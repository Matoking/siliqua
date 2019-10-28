import asyncio
import traceback

import aiohttp

from nanolib.blocks import ZERO_BLOCK_HASH
from nanolib.exceptions import InvalidBlock, InvalidSignature
from nanolib.util import dec_to_hex
from nanolib.work import validate_difficulty
from siliqua.network import BlockSyncResult
from siliqua.util import RawBlock
from siliqua.wallet.accounts import (Block, LinkBlock, Timestamp,
                                     TimestampSource)

from . import logger


async def do_json_post(url, params, session):
    response = await session.post(
        url, json=params, headers={"Content-Type": "application/json"}
    )
    result = await response.json()

    return result


EXTRA_FIELDS = ("hash", "height", "opened")

BLOCK_PARAMS = (
    "type", "account", "previous", "destination", "representative",
    "balance", "source", "link", "link_as_account", "signature", "work"
)

def get_raw_block_from_json(block_data):
    if "contents" in block_data:
        # 'blocks_info' includes a JSON string
        return RawBlock.from_json(block_data["contents"])

    # 'account_history' uses a JSON array with some extra fields
    raw_block_data = {
        k: v for k, v in block_data.items()
        if k in BLOCK_PARAMS
    }
    # 'account_history' uses integers for all balances, even legacy blocks
    #
    # Since nanolib only accepts hex balances for legacy blocks,
    # convert it to hex
    if "balance" in raw_block_data and raw_block_data["type"] != "state":
        raw_block_data["balance"] = dec_to_hex(
            int(raw_block_data["balance"]), 16
        )

    return RawBlock.from_dict(raw_block_data)


def get_block_from_json(block_data):
    """
    Deserialize block data received from a node's JSON response to a
    Block instance.

    JSON response may include extra data such as a timestamp, so include
    those as well
    """
    raw_block = get_raw_block_from_json(block_data)

    local_timestamp = None
    if "local_timestamp" in block_data and block_data["local_timestamp"]:
        local_timestamp = int(block_data["local_timestamp"])

    block = Block(
        block=raw_block,
        confirmed=True
    )

    if local_timestamp:
        block.timestamp = Timestamp(
            date=local_timestamp,
            source=TimestampSource.NODE
        )

    return block


def get_link_block_hash(block, subtype):
    if block.block_type in ("receive", "open"):
        return block.source
    if block.block_type == "state" and subtype in ("receive", "open"):
        return block.link

    return None


def get_link_block_from_json(block_data):
    """
    Deserialize block data received from a node's JSON response to a
    LinkBlock instance.
    """
    raw_block = RawBlock.from_json(block_data["contents"])

    local_timestamp = None
    if "local_timestamp" in block_data and block_data["local_timestamp"]:
        local_timestamp = int(block_data["local_timestamp"])

    link_block = LinkBlock(
        block=raw_block,
        amount=int(block_data["amount"])
    )

    if local_timestamp:
        link_block.timestamp = Timestamp(
            date=local_timestamp,
            source=TimestampSource.NODE
        )

    return link_block


class NetworkProcessorBase:
    # Only Nano 19.0 and above is supported due to required RPC calls
    REQUIRED_PROTOCOL_VERSION = 17

    # Wait for 1 second in case of an error before continuing
    NETWORK_ERROR_WAIT_SECONDS = 1

    # Wait for 100 ms after a successful update loop
    NETWORK_LOOP_WAIT_SECONDS = 0.1

    # Wait 10 seconds for a request to complete at most
    NETWORK_TIMEOUT_SECONDS = 10

    def __init__(self, network_plugin):
        self.network_plugin = network_plugin

        self.processed_block_queue = network_plugin.processed_block_queue
        self.pocketable_block_queue = network_plugin.pocketable_block_queue
        self.broadcast_block_queue = network_plugin.broadcast_block_queue

        self.broadcast_queue_lock = network_plugin.broadcast_queue_lock

        self.account_sync_statuses = network_plugin.account_sync_statuses
        self.account_ids_to_poll = network_plugin.account_ids_to_poll

        self.connection_status = network_plugin.connection_status
        self.shutdown_flag = network_plugin.shutdown_flag

        self.config = network_plugin.config

        self.minimum_pocketable_amount = \
            self.config.get("wallet.minimum_pocketable_amount")

        # RPC URL is also required by WebSocket task to retrieve link blocks
        # which are not part of the WS messages
        self.rpc_url = self.config.get(
            "network.{}.rpc_url".format(self.network_plugin.PLUGIN_NAME)
        )
        self.session = None

    # Use an anonymous function to always keep a correct reference
    # to the underlying primitive
    work_difficulty = property(
        lambda self: self.network_plugin.work_difficulty,
        lambda self, value: setattr(
            self.network_plugin, "work_difficulty", value
        )
    )

    async def do_json_post(self, url, params):
        try:
            response = await do_json_post(
                url=url, params=params, session=self.session
            )
            self.connection_status.update(True)
            return response
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            self.connection_status.update(False)
            try:
                message = str(exc.message)
            except AttributeError:
                message = None
            import traceback
            logger.error(
                "HTTP POST to node %s, %s failed. Error %s",
                self.rpc_url, str(params), traceback.format_exc()
            )
            raise exc

    async def get_link_blocks(self, block_hashes):
        if not block_hashes:
            return []

        response = await self.do_json_post(
            self.rpc_url,
            params={
                "action": "blocks_info",
                "hashes": block_hashes
            }
        )

        # We don't need to preserve the order of the blocks here, so
        # iterate them directly from the dict
        link_blocks = [
            get_link_block_from_json(block)
            for block in response["blocks"].values()
        ]

        return link_blocks
