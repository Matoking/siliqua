from .. import logger as root_logger  # isort:skip

logger = root_logger.getChild("nano_node")

import asyncio
from threading import Event, Thread
from urllib.parse import urlparse

import click

from siliqua.exceptions import ConfigurationError
from siliqua.network import BaseNetworkPlugin
from siliqua.network.nano_node.rpc import RPCProcessor
from siliqua.network.nano_node.ws import WebSocketProcessor


async def run_rpc_processor(network_plugin):
    logger.info("Starting JSON RPC network task...")

    network_plugin.rpc_processor = RPCProcessor(network_plugin)
    await network_plugin.rpc_processor.loop()
    network_plugin.rpc_processor = None


async def run_websocket_processor(network_plugin):
    logger.info("Starting WebSocket network task...")

    network_plugin.websocket_processor = WebSocketProcessor(network_plugin)
    await network_plugin.websocket_processor.loop()
    network_plugin.websocket_processor = None


def run_network_thread(network_plugin):
    """
    Start looping RPC and WebSocket asynchronous network tasks
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    tasks = [
        # RPC is always required
        run_rpc_processor(network_plugin)
    ]

    if network_plugin.config.get("network.nano_node.ws_url", None):
        # WebSocket is optional
        tasks.append(run_websocket_processor(network_plugin))
    else:
        logger.info("WebSocket URL not provided, using HTTP polling instead.")

    loop.run_until_complete(asyncio.gather(*tasks))


class NetworkPlugin(BaseNetworkPlugin):
    PLUGIN_NAME = "nano_node"

    def __init__(self, *args, **kwargs):
        super(NetworkPlugin, self).__init__(*args, **kwargs)

        self.thread = None
        self.shutdown_flag = None

        self.rpc_processor = None
        self.websocket_processor = None

        # Account IDs to poll. This is only used when a WebSocket connection
        # missed the successing block, requiring the account history to be
        # polled over the JSON RPC to get the wallet in sync again faster.
        self.account_ids_to_poll = set()

    @property
    def started(self):
        return self.thread and self.thread.is_alive()

    def _get_cli_params(self):
        return [
            click.Option(
                ["--network-rpc-url"], type=str,
                help="URL to the NANO node to use for the JSON RPC (required)"
            ),
            click.Option(
                ["--network-ws-url"], type=str,
                help=(
                    "URL to the NANO node to use for the WebSocket connection."
                    " WebSocket connection allows real-time synchronization. "
                    "(optional)"
                )
            )
        ]

    def validate_config(self):
        plugin_name = self.PLUGIN_NAME

        rpc_url = self.config.get(
            "network.{}.rpc_url".format(plugin_name), None
        )
        if not rpc_url:
            raise ConfigurationError(
                "network.{}.rpc_url".format(plugin_name),
                "Parameter is required"
            )

        try:
            urlparse(rpc_url)
        except ValueError:
            raise ConfigurationError(
                "network.{}.rpc_url".format(plugin_name),
                "Provided URL is invalid"
            )

        ws_url = self.config.get(
            "network.{}.ws_url".format(plugin_name), None
        )
        if ws_url:
            try:
                urlparse(ws_url)
            except ValueError:
                raise ConfigurationError(
                    "network.{}.ws_url".format(plugin_name),
                    "Provided URL is invalid"
                )

    def _stop(self):
        self.shutdown_flag.set()
        self.thread.join()

        logger.info("Stopped network thread")

        self.thread = None
        self.shutdown_flag = None

        self.rpc_processor = None
        self.websocket_processor = None

    def _start(self):
        self.shutdown_flag = Event()
        self.thread = Thread(
            target=run_network_thread,
            kwargs={"network_plugin": self}
        )
        self.thread.start()

        logger.info("Started network thread")
