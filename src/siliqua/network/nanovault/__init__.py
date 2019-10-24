from .. import logger as root_logger  # isort:skip

logger = root_logger.getChild("nanovault")

import asyncio
from threading import Event, Thread
from urllib.parse import urlparse

import click

from nanolib.work import WORK_DIFFICULTY
from siliqua.exceptions import ConfigurationError
from siliqua.network.nano_node import NetworkPlugin as NanoNodeNetworkPlugin
from siliqua.network.nanovault.rpc import RPCProcessor
from siliqua.network.nanovault.ws import WebSocketProcessor


async def run_rpc_processor(network_plugin):
    logger.info("Starting JSON RPC network task...")
    rpc_processor = RPCProcessor(network_plugin)
    await rpc_processor.loop()


async def run_websocket_processor(network_plugin):
    network_plugin.websocket_processor = WebSocketProcessor(network_plugin)
    logger.info("Starting WebSocket network task...")
    await network_plugin.websocket_processor.loop()
    network_plugin.websocket_processor = None


def run_network_thread(network_plugin):
    """
    Start looping asynchronous RPC and WebSocket network tasks
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    tasks = [
        # RPC is always required
        run_rpc_processor(network_plugin)
    ]

    if network_plugin.config.get("network.nanovault.ws_url", None):
        # WebSocket is optional
        tasks.append(run_websocket_processor(network_plugin))
    else:
        logger.info(
            "WebSocket URL not provided, using HTTP polling instead. "
            "Block confirmations will be delayed."
        )

    loop.run_until_complete(asyncio.gather(*tasks))


class NetworkPlugin(NanoNodeNetworkPlugin):
    PLUGIN_NAME = "nanovault"

    def _get_cli_params(self):
        return [
            click.Option(
                ["--network-rpc-url"], type=str,
                help="URL to NanoVault compatible NANO node to use for the JSON RPC (required)"
            ),
            click.Option(
                ["--network-ws-url"], type=str,
                help=(
                    "URL to the NanoVault WebSocket server to use."
                    " WebSocket connection allows real-time synchronization. "
                    "(optional)"
                )
            )
 
        ]

    def _start(self):
        self.shutdown_flag = Event()
        self.thread = Thread(
            target=run_network_thread,
            kwargs={"network_plugin": self}
        )
        self.thread.start()

        logger.info("Started network thread")
