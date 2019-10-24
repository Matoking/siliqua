import asyncio
import time
import traceback
from queue import Empty

import aiohttp
import pkg_resources

from nanolib.exceptions import InvalidBlock, InvalidSignature
from nanolib.work import validate_difficulty
from siliqua.network import BlockProcessError, BlockSyncResult
from siliqua.network.exceptions import UnsupportedProtocolVersion
from siliqua.network.nano_node.base import (NetworkProcessorBase,
                                            get_block_from_json,
                                            get_link_block_from_json,
                                            get_link_block_hash)
from siliqua.util import normalize_account_id

from . import logger

SILIQUA_VERSION = pkg_resources.get_distribution("siliqua").version


class RPCProcessor(NetworkProcessorBase):
    # If WebSocket connection is in use, only poll for updates every 2 minutes
    POLL_INTERVAL_SECONDS = 120

    # If WebSocket connection is unavailable, poll every 5 seconds.
    # TODO: Maybe make this interval configurable?
    FAST_POLL_INTERVAL_SECONDS = 5

    # Poll for confirmation every 1 second
    CONFIRMATION_POLL_INTERVAL_SECONDS = 1

    # Wait 5 minutes at most for confirmation before giving up
    CONFIRMATION_TIMEOUT_SECONDS = 300

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.pocket_timestamp = None

    @property
    def poll_interval(self):
        """
        Return HTTP poll interval depending on whether a WebSocket
        connection is active
        """
        if self.network_plugin.websocket_processor:
            return self.POLL_INTERVAL_SECONDS

        return self.FAST_POLL_INTERVAL_SECONDS

    async def loop(self):
        """
        The main event loop that continues endlessly until the shutdown
        flag is activated
        """
        # Create a session
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Siliqua/{} (Matoking@Github)".format(
                    SILIQUA_VERSION
                )
            },
            timeout=aiohttp.ClientTimeout(total=self.NETWORK_TIMEOUT_SECONDS)
        )

        logger.info("Starting RPC update loop")

        failed = False
        error = None

        while not self.shutdown_flag.is_set():
            try:
                await self.check_node_version()

                await self.update_active_difficulty()
                await self.update_broadcast_blocks()
                await self.update_new_blocks()
                await self.update_pocketable_blocks()

                # Check if all accounts are synced
                self.connection_status.sync_complete = not any([
                    not status.sync_complete for status
                    in self.account_sync_statuses.values()
                ])
                self.connection_status.completed_rounds += 1
            except (aiohttp.ClientError, asyncio.TimeoutError):
                # In case of an error, sleep for a bit and then try
                # again. This could happen if the node is just starting up
                await asyncio.sleep(self.NETWORK_ERROR_WAIT_SECONDS)
                continue
            except (InvalidBlock, InvalidSignature,
                    UnsupportedProtocolVersion) as exc:
                # If invalid blocks are returned, abort and shutdown the
                # network plugin
                failed = True
                error = exc
                self.shutdown_flag.set()
                break
            except Exception as exc:
                logger.error(
                    "Unexpected error during RPC network update: %s %s",
                    str(exc), traceback.format_exc()
                )
                await asyncio.sleep(self.NETWORK_ERROR_WAIT_SECONDS)
                continue

            # Sleep for a small moment between updates
            await asyncio.sleep(self.NETWORK_LOOP_WAIT_SECONDS)

        logger.info("Stopping RPC update loop")

        # Close the session on shutdown
        await self.session.close()

        if failed:
            logger.error(
                "Network server aborted due to a fatal error in RPC "
                "processor: %s", error
            )
            self.connection_status.abort(error)

    async def check_node_version(self):
        """
        Check the node version in use and return True if the node version
        is recent enough
        """
        protocol_version = self.connection_status.meta.get(
            "protocol_version", None
        )

        if protocol_version:
            return True

        result = await self.do_json_post(
            self.rpc_url,
            params={
                "action": "version"
            }
        )

        protocol_version = int(result["protocol_version"])

        # Cache the version so that later calls don't cause RPC requests
        self.connection_status.meta["protocol_version"] = protocol_version

        if protocol_version < self.REQUIRED_PROTOCOL_VERSION:
            raise UnsupportedProtocolVersion(
                required_version=self.REQUIRED_PROTOCOL_VERSION,
                current_version=protocol_version
            )

    async def update_active_difficulty(self):
        """
        Check the active difficulty on the network and update accordingly
        """
        result = await self.do_json_post(
            self.rpc_url,
            params={
                "action": "active_difficulty"
            }
        )

        difficulty = validate_difficulty(result["network_minimum"])

        self.work_difficulty = difficulty

    async def broadcast_block(self, block):
        """
        Broadcast a single block and wait until it is complete
        """
        params = {
            "action": "process",
            "block": block.json()
        }
        if self.connection_status.meta["protocol_version"] >= 18:
            # NANO 20.0+ nodes automatically perform PoW regeneration.
            # Disable that since we handle PoW instead.
            params["watch_work"] = False

        block_hash = block.block_hash
        response = await self.do_json_post(
            self.rpc_url,
            params=params
        )
        sync_result = None

        if "hash" not in response:
            # Block was rejected
            sync_result = BlockSyncResult(
                block=block, rejected=True, error=response["error"]
            )
        else:
            poll_start = time.time()
            while True:
                response = await self.do_json_post(
                    self.rpc_url,
                    params={
                        "action": "blocks_info",
                        "hashes": [block_hash]
                    }
                )

                try:
                    confirmed = \
                        response["blocks"][block_hash]["confirmed"] == "true"
                except KeyError:
                    # Block disappeared entirely. Since we don't know
                    # why the node dropped it, set error to 'unknown'
                    sync_result = BlockSyncResult(
                        block=block, rejected=True, error="unknown"
                    )
                    break

                if confirmed:
                    sync_result = BlockSyncResult(block=block, confirmed=True)
                    break

                if poll_start + self.CONFIRMATION_TIMEOUT_SECONDS < time.time():
                    # Give up after several minutes of waiting.
                    sync_result = BlockSyncResult(
                        block=block, rejected=True, error="timeout"
                    )
                    break

                # Wait one second and poll for confirmation again
                await asyncio.sleep(self.CONFIRMATION_POLL_INTERVAL_SECONDS)

        if sync_result.rejected:
            if sync_result.error == \
                    BlockProcessError.BLOCK_ALREADY_PROCESSED:
                # We tried sending the block again.
                # This can happen due to a race condition between the network
                # and wallet threads, but can be safely ignored.
                logger.info(
                    "Ignoring error for block %s that was transmitted again",
                    block_hash
                )
                return

            logger.warning(
                "Rejected block %s. Reason: %s",
                block_hash, sync_result.error.value
            )

            if sync_result.error == \
                    BlockProcessError.INSUFFICIENT_WORK:
                # If block is rejected for having insufficient work,
                # update active difficulty so that next work units
                # have correct difficulty threshold
                await self.update_active_difficulty()

            self.processed_block_queue.put(sync_result)
            # Clear the queue if a block is rejected
            # TODO: A more granular approach could be taken here:
            # only drop blocks that are dependent on the rejected block
            # instead of dropping everything.
            with self.broadcast_queue_lock:
                self.broadcast_block_queue.queue.clear()
        else:
            logger.info("Confirmed block %s", block_hash)
            self.processed_block_queue.put(sync_result)
            # Remove the just-confirmed block from the broadcast queue
            # to prevent unnecessary duplicate transmissions
            self.broadcast_block_queue.remove(sync_result.block)

    async def update_broadcast_blocks(self):
        """
        Broadcast blocks in the queue one-by-one until the queue
        is exhausted
        """
        while True:
            try:
                # TODO: Instead of processing every block one-by-one,
                # order blocks into independent subqueues which can be
                # processed in parallel
                block = self.broadcast_block_queue.get_nowait()
                await self.broadcast_block(block)
            except Empty:
                break

    async def update_account_blocks(self, account_id):
        """
        Update an account's block in two requests:
        first request to check account's (unconfirmed) blockchain
        second request to retrieve related link blocks and check blocks'
        confirmation status
        """
        sync_status = self.account_sync_statuses[account_id]
        network_head = sync_status.network_head

        # Start by retrieving account history
        params = {
            "action": "account_history",
            "account": account_id,
            # siliqua stores the entire history of an account,
            # so start from the first block
            "reverse": True,
            "raw": True,
            # 500 blocks at a time.
            # Requesting 1000 blocks results in a request that's too big
            # for some web servers to handle
            "count": 500,
        }

        if network_head:
            params["head"] = network_head

        response = await self.do_json_post(self.rpc_url, params=params)

        if "error" in response and response["error"] == "Account not found":
            history = []
        else:
            history = response["history"]

        if history and history[0]["hash"] == network_head:
            # We can skip retrieving the first block if we already have it
            history = history[1:]

        if not history:
            sync_status.sync_complete = True
            self.account_ids_to_poll.discard(account_id)
            return

        sync_status.sync_complete = False
        self.connection_status.sync_complete = False

        # Determine which blocks and link blocks we need to get
        block_hashes_to_get = []
        block_hash2link_block_hash = {}
        blocks = []

        for entry in history:
            # Account ID may be unrelated due to a quirk in 'account_history'
            # RPC call
            entry["account"] = account_id

            block = get_block_from_json(entry)
            subtype = entry.get("subtype", None)

            block_hash = block.block_hash
            block_hashes_to_get.append(block_hash)

            link_block_hash = get_link_block_hash(block, subtype)

            if link_block_hash:
                block_hashes_to_get.append(link_block_hash)
                block_hash2link_block_hash[block_hash] = link_block_hash

            blocks.append(block)

        response = await self.do_json_post(
            self.rpc_url,
            params={
                "action": "blocks_info",
                "hashes": block_hashes_to_get
            }
        )

        sync_status.update_timestamp()

        for block in blocks:
            block_hash = block.block_hash
            entry = response["blocks"][block_hash]
            confirmed = entry["confirmed"] == "true"

            if not confirmed:
                return

            link_block_hash = block_hash2link_block_hash.get(block_hash, None)

            if link_block_hash:
                link_entry = response["blocks"][link_block_hash]
                link_block = get_link_block_from_json(link_entry)

                block.link_block = link_block

            self.processed_block_queue.put(
                BlockSyncResult(block=block, confirmed=True)
            )

            sync_status.network_head = block_hash

    async def update_new_blocks(self):
        """
        Check the network for any new blocks to add to the queue
        """
        account_reqs = []

        for account_id, sync_status in self.account_sync_statuses.items():
            update_account = (
                not sync_status.sync_complete
                or account_id in self.account_ids_to_poll
                or sync_status.seconds_since_timestamp > self.poll_interval
            )
            if update_account:
                account_reqs.append(self.update_account_blocks(account_id))

        await asyncio.gather(*account_reqs)

        return True

    async def update_pocketable_blocks(self):
        update_pocketable_blocks = (
            not self.pocket_timestamp
            or self.pocket_timestamp + self.poll_interval < time.time()
        )

        if not update_pocketable_blocks:
            return

        account_ids_to_sync = [
            sync_status.account_id for sync_status
            in self.account_sync_statuses.values()
            if sync_status.sync_complete
        ]

        if not account_ids_to_sync:
            return

        response = await self.do_json_post(
            self.rpc_url,
            params={
                "action": "accounts_pending",
                "accounts": account_ids_to_sync,
                "threshold": self.minimum_pocketable_amount,
                "source": True
            }
        )

        account_block_hashes = []

        for blocks in response["blocks"].values():
            if blocks == "":
                # Instead of an empty dict, an empty string is used in the
                # API
                continue

            for block_hash in blocks.keys():
                account_block_hashes.append(block_hash)

        link_blocks = await self.get_link_blocks(account_block_hashes)

        for link_block in link_blocks:
            self.pocketable_block_queue.put(link_block)
