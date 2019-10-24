import asyncio
import time
import traceback

import aiohttp

from nanolib.blocks import ZERO_BLOCK_HASH
from nanolib.exceptions import InvalidBlock, InvalidSignature
from nanolib.work import validate_difficulty
from siliqua.network import BlockSyncResult
from siliqua.network.nano_node.base import (NetworkProcessorBase,
                                            get_block_from_json,
                                            get_link_block_hash,
                                            get_raw_block_from_json)
from siliqua.util import normalize_account_id
from siliqua.wallet.accounts import LinkBlock, Timestamp, TimestampSource

from . import logger


class WebSocketProcessor(NetworkProcessorBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.websocket_url = self.config.get("network.nano_node.ws_url")

        self.difficulty_subscribed = False
        self.account_subscribed = False

        self.subscribed_account_ids = set()

    async def loop(self):
        """
        The main event loop that continues endlessly until the shutdown
        flag is activated
        """
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.NETWORK_TIMEOUT_SECONDS)
        )
        while True:
            try:
                self.ws_conn = await self.session.ws_connect(
                    self.websocket_url
                )
                break
            except aiohttp.client_exceptions.ClientConnectorError:
                if self.shutdown_flag.is_set():
                    await self.session.close()
                    return
                else:
                    await asyncio.sleep(self.NETWORK_ERROR_WAIT_SECONDS)

        logger.info("Starting WebSocket update loop")

        failed = False
        error = None

        while not self.shutdown_flag.is_set():
            try:
                # Update the subscription options (which account IDs are we
                # following?)
                await self.update_listen_subscription()
                await self.listen_for_msg()
            except (InvalidBlock, InvalidSignature) as exc:
                # Abort if invalid blocks are returned
                failed = True
                error = exc
                self.shutdown_flag.set()
                break
            except Exception as exc:
                logger.error(
                    "Unexpected error during WS network update: %s",
                    traceback.format_exc()
                )
                await asyncio.sleep(self.NETWORK_ERROR_WAIT_SECONDS)
                continue

        logger.info("Stopping WebSocket update loop")

        await self.ws_conn.close()
        await self.session.close()

        if failed:
            logger.error(
                "Network server aborted due to a fatal error in WebSocket "
                "processor: %s", error
            )
            self.connection_status.abort(error)

    async def listen_for_msg(self):
        try:
            response = await self.ws_conn.receive_json(timeout=0.1)
        except asyncio.TimeoutError:
            return

        topic = response["topic"]
        msg = response["message"]

        if topic == "confirmation":
            await self.process_block_message(response)
        elif topic == "active_difficulty":
            self.work_difficulty = validate_difficulty(
                msg["network_minimum"]
            )

    async def process_block_message(self, response):
        """
        Process a block and insert it into the account and/or pocketable
        queue
        """
        msg = response["message"]
        account_id = normalize_account_id(msg["account"])

        block_data = msg["block"]
        subtype = msg["block"]["subtype"]

        if account_id in self.account_sync_statuses:
            await self.process_account_block_message(
                block_data=block_data,
                account_id=account_id,
                subtype=subtype
            )

        amount = int(msg.get("amount", 0))

        if amount != 0:
            raw_block = get_raw_block_from_json(block_data)
            if raw_block.tx_type not in ("send", "receive", "send/receive"):
                return

            link_block = LinkBlock(
                block=raw_block,
                amount=amount
            )
            if link_block.recipient in self.account_sync_statuses:
                await self.process_pocketable_block_message(
                    block_data=block_data,
                    amount=int(msg["amount"])
                )

    async def process_account_block_message(
            self, block_data, account_id, subtype):
        sync_status = self.account_sync_statuses[account_id]
        block = get_block_from_json(block_data)

        block_previous = (
            None if block.previous == ZERO_BLOCK_HASH else block.previous
        )

        if block_previous != sync_status.network_head:
            # We didn't receive a successor, which means the WebSocket
            # connection missed a block or we haven't finished the sync
            # for this account.
            logger.warning(
                "WebSocket received block %s for account %s, which isn't a "
                "successor to the local head %s. Polling to receive current "
                "network head.",
                block.block_hash, account_id, sync_status.network_head
            )
            self.account_ids_to_poll.add(account_id)
            return False

        link_block_hash = get_link_block_hash(block, subtype)

        if link_block_hash:
            link_blocks = await self.get_link_blocks([link_block_hash])
            link_block = link_blocks[0]
            block.link_block = link_block

        block.timestamp = Timestamp(
            date=int(time.time()),
            source=TimestampSource.BROADCAST
        )

        self.processed_block_queue.put(
            BlockSyncResult(block=block, confirmed=True)
        )

        sync_status.network_head = block.block_hash
        sync_status.sync_complete = False

        return True

    async def process_pocketable_block_message(self, block_data, amount):
        raw_block = get_raw_block_from_json(block_data)
        link_block = LinkBlock(
            block=raw_block,
            amount=amount
        )

        try:
            recipient = link_block.recipient
        except ValueError:
            logger.warning(
                "Received block %s wasn't pocketable",
                link_block.block_hash
            )
            return

        if recipient not in self.account_sync_statuses:
            logger.warning(
                "Received pocketable block %s didn't belong to any of "
                "the accounts in the wallet",
                link_block.block_hash
            )
            return

        link_block.timestamp = Timestamp(
            date=int(time.time()),
            source=TimestampSource.BROADCAST
        )

        self.pocketable_block_queue.put(link_block)

    async def update_listen_subscription(self):
        if not self.difficulty_subscribed:
            await self.ws_conn.send_json({
                "action": "subscribe",
                "topic": "active_difficulty"
            })
            self.difficulty_subscribed = True

        # Check which accounts we are supposed to listen for
        account_ids = set(list(self.account_sync_statuses.keys()))

        if account_ids == self.subscribed_account_ids:
            return

        if self.subscribed_account_ids:
            # Cancel the current subscription if one exists
            await self.ws_conn.send_json({
                "action": "unsubscribe",
                "topic": "confirmation"
            })

        await self.ws_conn.send_json({
            "action": "subscribe",
            "topic": "confirmation",
            "options": {
                "confirmation_type": "all",
                # The list of accounts is only sorted to make testing easier
                "accounts": sorted(list(account_ids))
            }
        })

        self.subscribed_account_ids = account_ids
