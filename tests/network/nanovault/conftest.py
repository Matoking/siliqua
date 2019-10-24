import asyncio
import importlib
import time
from collections import defaultdict
from threading import Event as ThreadEvent
from threading import Thread

from aiohttp import web

import pytest
from siliqua.network.nanovault import NetworkPlugin
from siliqua.network.nanovault import logger
from tests.util import find_free_port


class WebSocketReplay:
    def __init__(self, accounts, response):
        self.accounts = accounts
        self.response = response


class MockNanoVaultWebSocketNode:
    def __init__(self, port, mock_node):
        self.port = port
        self.mock_node = mock_node

        self.thread = None
        self.shutdown_flag = None

        self.subscribed_accounts = set()

        self.ws_replays = []

    def start(self):
        self.shutdown_flag = ThreadEvent()

        self.thread = Thread(
            target=run_test_nanovault_ws_node,
            kwargs={
                "shutdown_flag": self.shutdown_flag,
                "ws_mock_node": self
            }
        )
        self.thread.start()

        # Wait for a bit to let the thread start up
        time.sleep(0.05)

    def stop(self):
        if self.shutdown_flag:
            self.shutdown_flag.set()
            self.thread.join()

            self.shutdown_flag = None
            self.thread = None

        return self

    def reload(self):
        self.stop()
        self.start()

        return self

    async def handle_subscription(self, response):
        action = response["event"]
        accounts = response["data"]

        if action == "subscribe":
            for account in accounts:
                self.subscribed_accounts.add(account)
            logger.info(
                "[MOCK] Subscribed to accounts %s", accounts
            )
        elif action == "unsubscribe":
            for account in accounts:
                self.subscribed_accounts.discard(account)
            logger.info(
                "[MOCK] Unsubscribed from accounts %s", accounts
            )


    def add_replay_datasets(self, datasets):
        for dataset_name in datasets:
            req_replays = load_nanovault_ws_replay_dataset(dataset_name)

            for replay in req_replays:
                self.ws_replays.append(replay)

        return self

    async def broadcast_replay_responses(self, ws):
        for replay in self.ws_replays:
            if set(replay.accounts).issubset(self.subscribed_accounts):
                await ws.send_json(replay.response)
                self.ws_replays.remove(replay)


async def mock_nanovault_ws_handler(request):
    shutdown_flag = request.app["shutdown_flag"]
    ws_mock_node = request.app["ws_mock_node"]

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    while not shutdown_flag.is_set():
        # Receive and handle subscriptions and unsubscriptions
        try:
            try:
                response = await ws.receive_json(timeout=0.1)
                await ws_mock_node.handle_subscription(response)
            except asyncio.TimeoutError:
                pass
            except TypeError:
                # TypeError might be raised if WSMsgType.CLOSED was received
                if ws.closed:
                    break
                else:
                    raise

            await ws_mock_node.broadcast_replay_responses(ws)
        except Exception:
            import traceback
            print(traceback.format_exc())

    raise web.GracefulExit()



def run_test_nanovault_ws_node(shutdown_flag, ws_mock_node):
    app = web.Application()

    app.add_routes([
        web.get("/", mock_nanovault_ws_handler)
    ])

    app["shutdown_flag"] = shutdown_flag
    app["ws_mock_node"] = ws_mock_node

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    web.run_app(
        app,
        host="127.0.0.1",
        port=ws_mock_node.port,
        print=None,
        handle_signals=False
    )


def load_nanovault_ws_replay_dataset(name):
    mod = importlib.import_module(
        "tests.network.nanovault.data.ws.{}".format(name)
    )
    return getattr(mod, "DATA")


@pytest.fixture(scope="function")
def mock_nanovault_node(mock_node_factory, config):
    port = find_free_port()
    config.set("main.default_network_plugin", "nanovault")
    config.set(
        "network.nanovault.rpc_url",
        "http://127.0.0.1:{}".format(port)
    )

    return mock_node_factory(port=port)


@pytest.fixture(scope="function")
def mock_nanovault_ws_node_factory(mock_node_factory):
    mock_ws_nodes = []

    def create_test_node(port=9078, mock_node=None):
        if not mock_node:
            mock_node = mock_node_factory()

        mock_ws_node = MockNanoVaultWebSocketNode(
            mock_node=mock_node, port=port
        )

        mock_ws_nodes.append(mock_ws_node)

        return mock_ws_node

    yield create_test_node

    for mock_ws_node in mock_ws_nodes:
        mock_ws_node.stop()


@pytest.fixture(scope="function")
def mock_nanovault_ws_node(
        mock_nanovault_ws_node_factory, mock_nanovault_node, config):
    port = find_free_port()
    config.set("network.nanovault.ws_url", "http://127.0.0.1:{}".format(port))
    config.save()

    return mock_nanovault_ws_node_factory(
        mock_node=mock_nanovault_node, port=port
    )


@pytest.fixture(scope="function")
def nanovault_network_plugin(network_plugin_factory, mock_nanovault_node):
    return network_plugin_factory(
        port=mock_nanovault_node.port, plugin_cls=NetworkPlugin
    )


@pytest.fixture(scope="function")
def nanovault_ws_node_network_plugin(
        network_plugin_factory, mock_nanovault_node, mock_nanovault_ws_node):
    return network_plugin_factory(
        port=mock_nanovault_node.port, ws_port=mock_nanovault_ws_node.port,
        plugin_cls=NetworkPlugin
    )
