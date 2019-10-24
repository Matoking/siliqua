import asyncio
import time
import traceback

import aiohttp

from nanolib.exceptions import InvalidBlock, InvalidSignature
from siliqua.network.nano_node.base import get_raw_block_from_json
from siliqua.network.nano_node.ws import \
    WebSocketProcessor as NanoNodeWebSocketProcessor
from siliqua.util import normalize_account_id
from siliqua.wallet.accounts import LinkBlock

from . import logger


class WebSocketProcessor(NanoNodeWebSocketProcessor):
    """
    NanoVault uses its own WebSocket server
    """
    KEEPALIVE_INTERVAL_SECONDS = 60

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.websocket_url = self.config.get("network.nanovault.ws_url")

        self.account_subscribed = False

        self.subscribed_account_ids = set()

        self.keepalive_timestamp = time.time()

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
        broadcast_keepalive = (
            self.keepalive_timestamp + self.KEEPALIVE_INTERVAL_SECONDS
            < time.time()
        )
        if broadcast_keepalive:
            await self.ws_conn.send_json({"event": "keepalive"})
            self.keepalive_timestamp = time.time()

        try:
            response = await self.ws_conn.receive_json(timeout=0.1)
        except asyncio.TimeoutError:
            return

        msg = response["data"]
        block_data = msg["block"]
        account_id = normalize_account_id(block_data["account"])
        amount = int(msg["amount"])

        if amount != 0:
            raw_block = get_raw_block_from_json(block_data)
            if raw_block.tx_type in ("send", "receive", "send/receive"):
                link_block = LinkBlock(
                    block=raw_block,
                    amount=amount
                )
                if link_block.recipient in self.subscribed_account_ids:
                    await self.process_pocketable_block_message(
                        block_data=block_data, amount=amount
                    )

        if account_id in self.subscribed_account_ids:
            subtype = block_data["type"]
            if block_data["type"] == "state":
                if "is_send" in msg:
                    subtype = \
                        "send" if msg["is_send"] == "true" else "receive"

            await self.process_account_block_message(
                block_data=block_data,
                account_id=account_id,
                subtype=subtype
            )

    async def update_listen_subscription(self):
        # Check which accounts we are supposed to listen for
        account_ids = set(list(self.account_sync_statuses.keys()))

        if account_ids == self.subscribed_account_ids:
            return

        if self.subscribed_account_ids:
            # Cancel the current subscription if one exists
            await self.ws_conn.send_json({
                "event": "unsubscribe",
                "data": list(self.subscribed_account_ids)
            })

        await self.ws_conn.send_json({
            "event": "subscribe",
            "data": list(account_ids)
        })

        self.subscribed_account_ids = account_ids
