import asyncio
import concurrent
import copy
import importlib
import json
import random
import socket
import sys
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from itertools import cycle
from multiprocessing import Event as ProcessEvent
from multiprocessing import Manager, Process
from multiprocessing import RLock as ProcessRLock
from socketserver import ThreadingMixIn
from threading import Event as ThreadEvent
from threading import RLock, Thread, current_thread

from aiohttp import web

import pytest
from nanolib import Block as RawBlock
from nanolib import derive_work_difficulty, derive_work_multiplier
from siliqua.network.nano_node import NetworkPlugin, logger
from siliqua.wallet import Wallet
from siliqua.wallet.accounts import Account, Block
from tests.util import (HTTPReplay, PartialMatch, async_hook, find_free_port,
                        hook, to_hex)

TEST_DIFFICULTY = to_hex(9459044173002835, 16)


def wallet_from_str(s):
    """
    Convenience function to load a Wallet instance from a JSON-encoded string.
    This is more performant for transferring the wallet to the mocked
    HTTP server.
    """
    if s is None:
        return None

    return Wallet.from_dict(json.loads(s))


def wallet_to_str(wallet):
    """
    Convenience function to convert a Wallet instance to a JSON-encoded string.
    This is more performant for transferring the wallet to the mocked
    HTTP server.
    """
    if wallet is None:
        return None

    return json.dumps(wallet.to_dict(wallet))


class PartialMatch:
    def __init__(self, substr):
        self.substr = substr


class HTTPReplay:
    def __init__(self, req, resp, stage=0, block_to_confirm=None):
        self.req = req
        self.resp = resp
        self.stage = stage
        self.block_to_confirm = block_to_confirm

        self.resp_iter = cycle(self.resp)

    def match(self, request):
        if self.req.keys() != request.keys():
            return False

        for key, val in self.req.items():
            if isinstance(val, PartialMatch):
                if val.substr not in request[key]:
                    return False
            elif request[key] != val:
                return False

        return True

    def get(self):
        """
        Get the next response
        """
        if isinstance(self.resp, dict):
            # If the response is a dict, return it
            return self.resp
        elif isinstance(self.resp, list):
            # If the response is a list, iterate the list in a loop
            # to return the next response
            return next(self.resp_iter)

class WebSocketReplay:
    def __init__(self, topic, options, response):
        self.topic = topic
        self.options = options
        self.response = response


# Defined here for Python 3.6 compatibility
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class MockWebSocketNode:
    def __init__(self, port, mock_node):
        self.port = port
        self.mock_node = mock_node

        self.thread = None
        self.shutdown_flag = None
        self.lock = RLock()

        self.broadcast_blocks = mock_node.shared.broadcast_blocks
        self.subscriptions = {}

        self.ws_responses = defaultdict(list)

        self.work_difficulty = TEST_DIFFICULTY

    wallet = property(
        lambda self: self.mock_node.shared.wallet
    )

    def start(self):
        self.shutdown_flag = ThreadEvent()

        self.thread = Thread(
            target=run_test_ws_node,
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

    def add_replay_datasets(self, datasets):
        for dataset_name in datasets:
            req_responses = load_ws_replay_dataset(dataset_name)

            for response in req_responses:
                self.ws_responses[response.topic].append(response)

        return self

    async def handle_subscription(self, response):
        action = response["action"]
        topic = response["topic"]

        if action == "subscribe":
            self.subscriptions[topic] = response.get("options", {})
            logger.info(
                "[MOCK] Subscribed %s %s", topic, self.subscriptions[topic]
            )
        elif action == "unsubscribe":
            try:
                del self.subscriptions[topic]
                logger.info(
                    "[MOCK] Unsubscribed from topic '%s'",
                    topic
                )
            except KeyError:
                logger.info(
                    "[MOCK] Tried to unsubscribe from topic '%s' "
                    "which is not active", topic
                )

    async def broadcast_replay_responses(self, ws):
        for topic, options in self.subscriptions.items():
            for response in self.ws_responses[topic]:
                if response.options == options:
                    await ws.send_json(response.response)
                    self.ws_responses[topic].remove(response)

    async def broadcast_mock_responses(self, ws):
        wallet = wallet_from_str(self.wallet)

        if "confirmation" in self.subscriptions:
            options = self.subscriptions["confirmation"].get("options", {})

            accounts = options.get("accounts", [])

            for account_id in accounts:
                try:
                    account = wallet.account_map[account_id]
                except KeyError:
                    continue

                if not account.blocks:
                    continue

                block = account.blocks[0]

                while block:
                    if not block.confirmed:
                        break
                    block_hash = block.block_hash

                    # Has this been broadcast yet?
                    if block_hash in self.broadcast_blocks:
                        block = block.next
                        continue

                    block_data = block.to_dict()
                    if block.link_block:
                        subtype = "receive"
                    elif block.tx_type == "change":
                        subtype = "change"
                    else:
                        subtype = "send"
                    block_data["subtype"] = subtype

                    await ws.send_json({
                        "topic": "confirmation",
                        "time": str(time.time() * 1000),
                        "message": {
                            "account": block.account,
                            "amount": str(block.amount),
                            "hash": block_hash,
                            "confirmation_type": "active_quorum",
                            "block": block_data
                        }
                    })

                    self.broadcast_blocks.add(block_hash)

                    block = block.next

        if "active_difficulty" in self.subscriptions:
            await ws.send_json({
                "topic": "active_difficulty",
                "time": str(time.time()),
                "message": {
                    "network_minimum": self.work_difficulty,
                    "network_current": self.work_difficulty,
                    "multiplier": derive_work_multiplier(
                        difficulty=self.work_difficulty,
                        base_difficulty=TEST_DIFFICULTY
                    )
                }
            })


async def mock_ws_handler(request):
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
            if ws_mock_node.wallet:
                await ws_mock_node.broadcast_mock_responses(ws)
        except Exception:
            import traceback
            print(traceback.format_exc())

    raise web.GracefulExit()


def run_test_ws_node(shutdown_flag, ws_mock_node):
    app = web.Application()

    app.add_routes([
        web.get("/", mock_ws_handler)
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


class TestRPCNodeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        result = None

        shared = self.server.shared

        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        post_data = json.loads(post_data)

        with self.server.lock:
            for mock_response in shared.req_responses:
                if mock_response.match(post_data):
                    # If the request parameters correspond, send the
                    # prepared mock response
                    result = mock_response.get()

            if not result and shared.wallet:
                result = self.server.mocker.create_mock_response(post_data)

        if not result:
            logger.info(
                "Didn't find request {}".format(post_data)
            )
            raise ValueError(
                "Didn't find a response for request {}".format(post_data)
            )

        self.send_response(200)

        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()

        self.wfile.write(bytes(json.dumps(result), "utf-8"))
        return


def run_test_rpc_node(shutdown_flag, lock, port, shared):
    test_server = ThreadingHTTPServer(
        ("localhost", port), TestRPCNodeHandler)
    test_server.shared = shared
    test_server.mocker = MockRPCResponseMocker(shared=shared)
    test_server.lock = lock
    test_server.timeout = 0.1

    while not shutdown_flag.is_set():
        test_server.handle_request()

    test_server.server_close()

    return True


def load_http_replay_dataset(name):
    mod = importlib.import_module(
        "tests.network.nano_node.data.http.{}".format(name)
    )
    return getattr(mod, "DATA")


def load_ws_replay_dataset(name):
    mod = importlib.import_module(
        "tests.network.nano_node.data.ws.{}".format(name)
    )
    return getattr(mod, "DATA")


def create_responses_from_wallet(wallet, mock_node):
    req_responses = []

    return req_responses


class MockRPCResponseMocker:
    def __init__(self, shared):
        self.shared = shared

    def create_mock_account_history(self, data):
        account_id = data["account"]

        wallet = wallet_from_str(self.shared.wallet)

        assert data["raw"]
        assert data["reverse"]
        assert data["count"] == 500

        head = data.get("head", None)

        result = {
            "account": account_id
        }

        try:
            account = wallet.account_map[account_id]
        except KeyError:
            logger.info(
                "[MOCK] Account {} not in mock wallet".format(account_id)
            )

        if not account.blocks:
            return {"error": "Account not found"}

        account_entries = ""

        found_head = False
        for i, block in enumerate(account.blocks):
            block_hash = block.block_hash

            if block_hash == head:
                found_head = True
            elif i == 0 and head is None:
                found_head = True

            if found_head and block.confirmed:
                arrival_time = self.shared.block_arrival_time.get(block.block_hash, 0)
                broadcast_complete = block_hash in self.shared.broadcast_blocks

                # Don't report the block just yet if it's delayed,
                # unless it's been broadcast by WebSocket
                if not broadcast_complete and \
                        time.time() < arrival_time + self.shared.broadcast_delay:
                    continue

                self.shared.broadcast_blocks.add(block_hash)

                if block.link_block:
                    subtype = "receive"
                elif block.tx_type == "send/receive":
                    subtype = "send"
                else:
                    subtype = block.tx_type

                if account_entries == "":
                    account_entries = []

                account_entries.append({
                    "account": account.account_id,
                    "amount": str(block.amount),
                    "balance": str(block.balance),
                    "hash": block.block_hash,
                    "link": block.link,
                    "local_timestamp": None,
                    "previous": block.previous,
                    "representative": block.representative,
                    "signature": block.signature,
                    "subtype": subtype,
                    "type": block.block_type,
                    "work": block.work
                })

        result["history"] = account_entries

        return result

    def create_mock_blocks_info(self, data):
        blocks = {}

        wallet = wallet_from_str(self.shared.wallet)

        for block_hash in data["hashes"]:
            found_block = None
            for account in wallet.accounts:
                if block_hash in account.block_map:
                    block = account.block_map[block_hash]

                    found_block = block
                    break

            for block in self.shared.pocketable_blocks:
                if block.block_hash != block_hash:
                    continue

                destination = (
                    block.destination
                    if block.block_type == "send"
                    else block.link_as_account
                )

                try:
                    account = wallet.account_map[destination]
                except KeyError:
                    logger.info(
                        "[MOCK] Account {} not in the mock wallet".format(
                            destination
                        )
                    )

                found_block = block

            if found_block:
                blocks[block_hash] = {
                    "amount": str(found_block.amount),
                    "balance": str(found_block.balance),
                    "contents": found_block.block.json(),
                    # We can fake this for now
                    "height": str(random.randint(2, 10)),
                    "confirmed": "true",
                    "local_timestamp": None
                }
            else:
                logger.info("[MOCK] Didn't find block {}".format(block_hash))

        return {
            "blocks": blocks
        }

    def create_mock_accounts_pending(self, data):
        accounts = data["accounts"]

        wallet = wallet_from_str(self.shared.wallet)

        assert data["threshold"] == "100000000000000000000000000"
        assert data["source"]

        blocks = {}

        for account_id in accounts:
            blocks[account_id] = ""

            for block in self.shared.pocketable_blocks:
                destination = (
                    block.destination
                    if block.block_type == "send"
                    else block.link_as_account
                )

                if destination != account_id:
                    continue

                try:
                    account = wallet.account_map[destination]
                except KeyError:
                    logger.info(
                        "[MOCK] Account {} to check pending blocks for "
                        "not in mock wallet".format(destination)
                    )
                    continue

                already_pocketed = False

                for account_block in account.blocks:
                    if not account_block.link_block:
                        continue

                    if account_block.link_block.block_hash != block.block_hash:
                        continue

                    if account_block.confirmed:
                        already_pocketed = True
                        break

                if already_pocketed:
                    # Block has already been pocketed
                    continue

                if blocks[account_id] == "":
                    blocks[account_id] = {}

                blocks[account_id][block.block_hash] = {
                    "amount": str(block.amount),
                    "source": block.source
                }

        return {
            "blocks": blocks
        }

    def create_mock_process(self, data):
        block_data = data["block"]
        wallet = wallet_from_str(self.shared.wallet)

        block = RawBlock.from_json(block_data)

        if not block.signature:
            logger.info(
                "[MOCK] Trying to process unsigned block {}".format(
                    block.block_hash
                )
            )
            return None

        if not block.work:
            logger.info(
                "[MOCK] Trying to process block with no work {}".format(
                    block.block_hash
                )
            )
            return None

        account = wallet.account_map[block.account]
        mock_block = account.block_map[block.block_hash]

        if mock_block.confirmed:
            logger.info(
                "[MOCK] Trying to process confirmed block {}".format(
                    block.block_hash
                )
            )
            return None

        logger.info(
            "[MOCK] Confirming block {}".format(block.block_hash)
        )

        if self.shared.broadcast_fail_counter is not None:
            if self.shared.broadcast_fail_counter == 0:
                return {
                    "error": "Gap source block"
                }
            else:
                self.shared.broadcast_fail_counter -= 1

        if self.shared.difficulty_raise_counter is not None:
            if self.shared.difficulty_raise_counter == 0:
                self.shared.difficulty_raise_counter = None

                self.shared.work_difficulty = derive_work_difficulty(
                    multiplier=1.15, base_difficulty=self.shared.work_difficulty
                )
                return {
                    "error": "Block work is less than threshold"
                }
            else:
                self.shared.difficulty_raise_counter -= 1

        mock_block.confirmed = True

        self.shared.block_arrival_time[block.block_hash] = time.time()
        self.shared.wallet = wallet_to_str(wallet)

        return {
            "hash": block.block_hash
        }

    def create_mock_active_difficulty(self, _):
        return {
            "network_minimum": self.shared.work_difficulty,
            "network_current": self.shared.work_difficulty,
            "multiplier": str(
                derive_work_multiplier(
                    difficulty=self.shared.work_difficulty,
                    base_difficulty=TEST_DIFFICULTY
                )
            )
        }

    def create_mock_version(self, _):
        return {
            "node_vendor": "Mock Nano 19.0",
            "protocol_version": "17",
            "rpc_version": "1",
            "store_version": "13"
        }

    def create_mock_response(self, data):
        action = data["action"]

        try:
            if action == "account_history":
                return self.create_mock_account_history(data)
            elif action == "blocks_info":
                return self.create_mock_blocks_info(data)
            elif action == "accounts_pending":
                return self.create_mock_accounts_pending(data)
            elif action == "process":
                return self.create_mock_process(data)
            elif action == "active_difficulty":
                return self.create_mock_active_difficulty(data)
            elif action == "version":
                return self.create_mock_version(data)
            else:
                logger.info("[MOCK] Got non-mockable action '{}'".format(action))
        except Exception as exc:
            logger.info("[MOCK] Mock function failed with {}".format(str(exc)))


class MockRPCNode:
    def __init__(self, port):
        self.port = port
        self.process = None
        self.shutdown_flag = None

        self.manager = Manager()
        self.lock = ProcessRLock()

        self.shared = self.manager.Namespace()

        self.shared.wallet = None

        self.shared.req_responses = []
        self.shared.req_datasets = []

        self.shared.block_arrival_time = {}
        self.shared.broadcast_blocks = set()

        self.shared.work_difficulty = TEST_DIFFICULTY

        self.shared.last_broadcast_block_hash = None
        self.shared.broadcast_fail_counter = None
        self.shared.difficulty_raise_counter = None
        self.shared.broadcast_delay = 0.0

        self.shared.pocketable_blocks = []

    def add_pocketable_blocks(self, blocks):
        self.shared.pocketable_blocks += blocks

    def fail_broadcast_after(self, block_count=0):
        """
        Cause block broadcasts to fail after a certain amount of blocks
        have been confirmed by the mocked node
        """
        self.shared.broadcast_fail_counter = block_count

    def raise_difficulty_after(self, block_count=0):
        """
        Cause block broadcasts to fail due to a difficulty increase
        after a certain amount of blocks have been confirmed by the mocked
        node
        """
        self.shared.difficulty_raise_counter = block_count

    def delay_confirmation(self, seconds):
        """
        Delay blocks from appearing in the mock node's history with
        the given delay.

        This is done to allow the WebSocket node to report of the block's
        existence first
        """
        self.shared.broadcast_delay = 0.0

    def update_wallet(self):
        """
        Create mock requests allowing the accounts in the wallet
        to be synchronized
        """
        if not self.shared.wallet:
            return

        self.shared.req_responses += create_responses_from_wallet(
            wallet=self.shared.wallet,
            mock_node=self)

        return self

    def synchronize_responses(self):
        with self.lock:
            self.clear() \
                .update_wallet()

    def add_replay_datasets(self, datasets):
        new_req_responses = []
        for dataset_name in datasets:
            new_req_responses += load_http_replay_dataset(dataset_name)

        self.shared.req_responses += new_req_responses

        return self

    def start(self):
        self.shutdown_flag = ProcessEvent()

        self.process = Process(
            target=run_test_rpc_node,
            kwargs={
                "shutdown_flag": self.shutdown_flag,
                "lock": self.lock,
                "port": self.port,
                "shared": self.shared,
            }
        )
        self.process.start()

        # Wait for a bit to let the process start up
        time.sleep(0.1)

    def stop(self):
        if self.shutdown_flag:
            self.shutdown_flag.set()
            self.process.join()

            self.shutdown_flag = None
            self.process = None

        return self

    def clear(self):
        self.shared.req_responses.clear()

        return self

    def reload(self):
        self.stop()
        self.start()

        return self

    def add_request(self, req_resp):
        self.shared.req_responses.append(req_resp)
        return self


@pytest.fixture(scope="function")
def low_difficulty(monkeypatch):
    monkeypatch.setattr(
        "siliqua.network.nano_node.base.NetworkProcessorBase.work_difficulty",
        TEST_DIFFICULTY
    )
    monkeypatch.setattr(
        "siliqua.network.nano_node.RPCProcessor.work_difficulty",
        TEST_DIFFICULTY
    )
    monkeypatch.setattr(
        "siliqua.network.nano_node.WebSocketProcessor.work_difficulty",
        TEST_DIFFICULTY
    )
    monkeypatch.setattr(
        "siliqua.network.BaseNetworkPlugin.work_difficulty",
        TEST_DIFFICULTY
    )
    monkeypatch.setattr(
        "nanolib.blocks.WORK_DIFFICULTY", TEST_DIFFICULTY)
    monkeypatch.setattr(
        "siliqua.wallet.wallet.WORK_DIFFICULTY", TEST_DIFFICULTY)


@pytest.fixture(scope="function")
def mock_node_factory():
    mock_nodes = []

    def create_test_node(datasets=None, port=9076):
        if not datasets:
            datasets = []

        mock_node = MockRPCNode(port=port)
        if datasets:
            mock_node.add_replay_datasets(datasets)

        mock_nodes.append(mock_node)

        return mock_node

    yield create_test_node

    for mock_node in mock_nodes:
        mock_node.stop()


@pytest.fixture(scope="function")
def mock_node(mock_node_factory, config):
    port = find_free_port()
    config.set("network.nano_node.rpc_url", "http://127.0.0.1:{}".format(port))
    config.save()

    return mock_node_factory(port=port)


@pytest.fixture(scope="function")
def mock_ws_node_factory(mock_node_factory):
    mock_ws_nodes = []

    def create_test_node(port=9078, mock_node=None):
        if not mock_node:
            mock_node = mock_node_factory()

        mock_ws_node = MockWebSocketNode(mock_node=mock_node, port=port)

        mock_ws_nodes.append(mock_ws_node)

        return mock_ws_node

    yield create_test_node

    for mock_ws_node in mock_ws_nodes:
        mock_ws_node.stop()


@pytest.fixture(scope="function")
def mock_ws_node(mock_ws_node_factory, mock_node, config):
    port = find_free_port()
    config.set("network.nano_node.ws_url", "http://127.0.0.1:{}".format(port))
    config.save()

    return mock_ws_node_factory(mock_node=mock_node, port=port)


def update_mock_responses_in_server(mock_node):
    def wrapper(*args, **kwargs):
        with mock_node.lock:
            mock_node.synchronize_responses()

    return wrapper


def update_mock_responses_in_wallet(mock_node):
    def wrapper(*args, **kwargs):
        with mock_node.lock:
            mock_node.synchronize_responses()

    return wrapper


def hook_server_wallet_to_mock_node(mock_node):
    def wrapper(*args, **kwargs):
        server = args[0]
        with mock_node.lock:
            logger.info(
                "Hooking wallet to the mocked node from '{}'".format(
                    wrapper._wrapped_method.__name__
                )
            )
            mock_node.shared.wallet = wallet_to_str(server.wallet)

    return wrapper


def hook_wallet_to_mock_node(mock_node):
    def wrapper(*args, **kwargs):
        wallet = args[0]
        with mock_node.lock:
            logger.info(
                "Hooking wallet to the mocked node from '{}'".format(
                    wrapper._wrapped_method.__name__
                )
            )
            mock_node.shared.wallet = wallet_to_str(wallet)

    return wrapper


def update_wallet_to_mock_node(mock_node):
    def wrapper(*args, **kwargs):
        wallet = args[0]
        with mock_node.lock:
            mock_wallet = wallet_from_str(mock_node.shared.wallet)

            if not mock_wallet:
                return

            logger.info(
                "Synchronizing mock wallet with the actual wallet "
                "from '{}'".format(wrapper._wrapped_method.__name__)
            )

            for account in wallet.account_map.values():
                account_id = account.account_id

                if account_id not in mock_wallet.account_map:
                    mock_wallet.add_account(
                        Account.from_dict(account.to_dict())
                    )

                mock_account = mock_wallet.account_map[account_id]

                for block in account.blocks:
                    if block.block_hash not in mock_account.block_map:
                        mock_account.add_block(
                            Block.from_dict(block.to_dict())
                        )

                    mock_block = mock_account.block_map[block.block_hash]

                    if not mock_block.confirmed:
                        mock_block.confirmed = block.confirmed

                    if not mock_block.work:
                        mock_block.work = block.work
                        mock_block.difficulty = block.difficulty

                    if not mock_block.signature:
                        mock_block.signature = block.signature

                mock_account.confirmed_head = None
                mock_account.update_confirmed_head()
                mock_account.precomputed_work = copy.deepcopy(
                    account.precomputed_work
                )

            mock_node.shared.wallet = wallet_to_str(wallet)
            mock_node.synchronize_responses()

    return wrapper


@pytest.fixture(scope="function")
def wallet_mock_node(monkeypatch, mock_node, low_difficulty):
    from siliqua.server import WalletServer
    from siliqua.wallet import Wallet
    monkeypatch.setattr(
        "siliqua.server.WalletServer.load_wallet",
        hook(
            after=hook_server_wallet_to_mock_node(mock_node),
            orig_func=WalletServer.load_wallet
        )
    )
    monkeypatch.setattr(
        "siliqua.server.WalletServer.wait_for_blocks",
        hook(
            before=hook_server_wallet_to_mock_node(mock_node),
            orig_func=WalletServer.wait_for_blocks
        )
    )
    monkeypatch.setattr(
        "siliqua.server.WalletServer.send_from",
        hook(
            after=hook_server_wallet_to_mock_node(mock_node),
            orig_func=WalletServer.send_from
        )
    )
    monkeypatch.setattr(
        "siliqua.wallet.Wallet.update_solved_blocks",
        hook(
            after=update_wallet_to_mock_node(mock_node),
            orig_func=Wallet.update_solved_blocks
        )
    )
    monkeypatch.setattr(
        "siliqua.wallet.Wallet.update_processed_blocks",
        hook(
            after=update_wallet_to_mock_node(mock_node),
            orig_func=Wallet.update_processed_blocks
        )
    )
    #monkeypatch.setattr(
    #    "siliqua.server.WalletServer.update",
    #    hook(
    #        update_mock_responses_in_server(mock_node),
    #        WalletServer.update
    #    )
    #)
    #monkeypatch.setattr(
    #    "siliqua.wallet.Wallet.update_processed_blocks",
    #    hook(
    #        update_mock_responses_in_wallet(mock_node),
    #        Wallet.update_processed_blocks
    #    )
    #)
    #monkeypatch.setattr(
    #    "siliqua.wallet.Wallet.update_solved_blocks",
    #    hook(
    #        update_mock_responses_in_wallet(mock_node),
    #        Wallet.update_solved_blocks
    #    )
    #)
    #monkeypatch.setattr(
    #    "siliqua.wallet.Wallet.sign_blocks",
    #    hook(
    #        update_mock_responses_in_wallet(mock_node),
    #        Wallet.sign_blocks
    #    )
    #)

    return mock_node


@pytest.fixture(scope="function")
def network_plugin_factory(config_factory):
    network_plugins = []

    def create_node_network_plugin(
            port=9076, ws_port=None, plugin_cls=None):
        if not plugin_cls:
            plugin_cls = NetworkPlugin

        config = config_factory()
        config.set(
            "main.default_network_plugin", plugin_cls.PLUGIN_NAME
        )
        config.set(
            "network.{}.rpc_url".format(plugin_cls.PLUGIN_NAME),
            "http://127.0.0.1:{}".format(port)
        )

        if ws_port:
            config.set(
                "network.{}.ws_url".format(plugin_cls.PLUGIN_NAME),
                "http://127.0.0.1:{}".format(ws_port)
            )

        config.set(
            "network.{}.sync_delay".format(plugin_cls.PLUGIN_NAME),
            0.1
        )

        network_plugin = plugin_cls(config=config)

        # Lower the work difficulty to make tests faster
        network_plugin.work_difficulty = TEST_DIFFICULTY
        network_plugin.start()

        network_plugins.append(network_plugin)

        return network_plugin

    yield create_node_network_plugin

    for network_plugin in network_plugins:
        if network_plugin.started:
            network_plugin.stop()


@pytest.fixture(scope="function")
def node_network_plugin(network_plugin_factory, mock_node):
    return network_plugin_factory(port=mock_node.port)


@pytest.fixture(scope="function")
def ws_node_network_plugin(
        network_plugin_factory, mock_node, mock_ws_node):
    return network_plugin_factory(
        port=mock_node.port, ws_port=mock_ws_node.port
    )

