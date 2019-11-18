import io
import os
import random
from functools import lru_cache
from pathlib import Path

from click.testing import CliRunner

import pytest
from siliqua.cli import main as cli_main
from siliqua.config import DEFAULT_CONFIG, Config
from siliqua.logger import set_verbosity_level
from siliqua.plugins import get_ui_plugins, get_work_plugins
from siliqua.server import WalletServer

from .network.nanovault.conftest import *
from .network.nano_node.conftest import *
from .wallet.conftest import *
from .work.conftest import *

ENCRYPTED_FIXTURES = {
    "wallet_loader": "encrypted_wallet_loader",
    "wallet_factory": "encrypted_wallet_factory",
    "stdio": "encrypted_stdio"
}


def pytest_generate_tests(metafunc):
    test_markers = [
        marker.name for marker in metafunc.definition.own_markers
    ]
    test_class_markers = [
        marker.name for marker in metafunc.definition.parent.parent.own_markers
    ]
    if "add_encrypted_test" not in test_markers + test_class_markers:
        return

    # For 'add_encrypted_test' marker,
    # create two test scenarios for each test function:
    # one which uses an unencrypted wallet and another that uses
    # an encrypted wallet
    idlist = []
    argvalues = []

    fixture_names = [
        fixturename for fixturename in metafunc.fixturenames
        # Exclude 'request' since it can't be passed to pytest.mark.parametrize
        if fixturename != "request"
    ]
    default_fixture_names = [
        name for name in fixture_names if name != "is_encrypted_test"
    ]

    for is_encrypted in (False, True):
        idlist.append("encrypted" if is_encrypted else "unencrypted")

        arg_subvalues = []
        for fixture_name in fixture_names:
            if fixture_name == "is_encrypted_test":
                arg_subvalues.append(is_encrypted)
            else:
                arg_subvalues.append(fixture_name)

        argvalues.append(arg_subvalues)

    metafunc.parametrize(
        argnames=fixture_names, argvalues=argvalues,
        ids=("unencrypted", "encrypted"),
        indirect=default_fixture_names
    )


@lru_cache()
def fast_calculate_key_iteration_count(seconds):
    from siliqua.wallet.secret import calculate_key_iteration_count

    return calculate_key_iteration_count(seconds * 0.02)


@pytest.fixture(scope="function", autouse=True)
def enable_debug_log(scope="function", autouse=True):
    set_verbosity_level(3)


@pytest.fixture(scope="function")
def mock_stdin(monkeypatch):
    def mock_stdin_func(s):
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)
        monkeypatch.setattr("getpass.getpass", lambda _: s)

    return mock_stdin_func


@pytest.fixture(scope="function", autouse=True)
def fast_key_derivation(monkeypatch):
    """
    To speed up tests involving encryption, patch
    'calculate_key_iteration_count' to return key iteration counts
    that are 50x faster
    """
    monkeypatch.setattr(
        "siliqua.wallet.wallet.calculate_key_iteration_count",
        fast_calculate_key_iteration_count
    )
    monkeypatch.setattr(
        "siliqua.ui.stdio.commands.calculate_key_iteration_count",
        fast_calculate_key_iteration_count
    )
    monkeypatch.setattr(
        "siliqua.wallet.secret.calculate_key_iteration_count",
        lambda _: 2000
    )


@pytest.fixture(scope="function", autouse=True)
def fast_network_recovery(monkeypatch):
    """
    To speed up tests, allow the 'nano_node' plugin to recover 10x faster
    from timeouts and other non-fatal errors. This is necessary
    because the threaded HTTP server used for tests can cause some requests
    to drop out and delay the test unnecessarily otherwise.
    """
    monkeypatch.setattr(
        "siliqua.network.nano_node.base.NetworkProcessorBase."
        "NETWORK_ERROR_WAIT_SECONDS",
        0.5
    )
    monkeypatch.setattr(
        "siliqua.network.nano_node.base.NetworkProcessorBase."
        "NETWORK_TIMEOUT_SECONDS", 0.5
    )


@pytest.fixture(scope="function")
def cli(capsys):
    def invoke_command(args):
        try:
            cli_main(args)
        except SystemExit:
            pass

        return capsys.readouterr()

    return invoke_command


@pytest.fixture(scope="function")
def config_factory(tmp_path):
    def create_config():
        config_path = (
            tmp_path / "config{}.toml".format(random.randint(1, 2**32))
        )

        with open(config_path, "w") as f:
            f.write(DEFAULT_CONFIG)

        config = Config(path=config_path)
        return config

    return create_config


@pytest.fixture(scope="function")
def config(config_factory):
    return config_factory()


@pytest.fixture(scope="function")
def server_factory(config_factory, wallet_factory):
    def create_server(config=None, work=None, wallet=None):
        config = config or config_factory()

        if not work:
            work_name = config["main"]["default_work_plugin"]
            work = get_work_plugins()[work_name](config=config)

        wallet = wallet or wallet_factory()

        server = WalletServer(
            config=config or config_factory(),
            work=work,
            wallet=wallet
        )

        return server

    return create_server


@pytest.fixture(scope="function")
def server(server_factory):
    return server_factory()


@pytest.fixture(scope="function")
def test_home(tmp_path):
    test_home_path = tmp_path / "home"
    test_home_path.mkdir()

    old_home = os.environ.get("HOME", None)

    os.environ["HOME"] = str(test_home_path)
    yield test_home_path

    os.environ["HOME"] = old_home
