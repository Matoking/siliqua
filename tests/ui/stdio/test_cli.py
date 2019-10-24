import json

from siliqua.server import WalletServer


def test_wallet_required(stdio):
    result = stdio(["list-accounts"], success=False)

    assert result["data"]["error"] == "wallet_required"


def test_wallet_incorrect_passphrase(stdio, wallet_path, wallet_loader):
    stdio(
        [
            "create-wallet", str(wallet_path), "--encrypt-secrets",
            "--encrypt-wallet"
        ],
        env={"PASSPHRASE": "test_password"}
    )

    result = stdio(
        ["--wallet", str(wallet_path), "list-accounts"],
        env={"PASSPHRASE": "wrong_password"},
        success=False
    )

    assert result["data"]["error"] == "incorrect_passphrase"


def test_wallet_missing_passphrase(stdio, wallet_path):
    stdio(
        [
            "create-wallet", str(wallet_path), "--encrypt-secrets",
            "--encrypt-wallet"
        ],
        env={"PASSPHRASE": "test_password"}
    )

    result = stdio(
        ["--wallet", str(wallet_path), "list-accounts"],
        success=False
    )

    assert result["data"]["error"] == "wallet_encrypted"


def test_wallet_file_locked(stdio, config, wallet_path, wallet_factory):
    wallet = wallet_factory()
    wallet.save(wallet_path)

    server = WalletServer(config=config, work=None, network=None, wallet=None)
    server.load_wallet(wallet_path)

    # Launch a command while the wallet is locked
    result = stdio([
        "--wallet", wallet_path, "list-accounts"
    ], success=False)

    assert result["data"]["error"] == "wallet_locked"

    server.close_wallet()

    # Wallet is unlocked again and the command can be executed
    stdio(["--wallet", wallet_path, "list-accounts"])


def test_wallet_file_invalid(stdio, wallet_path):
    with open(wallet_path, "w") as f:
        f.write("invalid wallet")

    result = stdio([
        "--wallet", wallet_path, "list-accounts"
    ], success=False)

    assert result["data"]["error"] == "wallet_invalid"


def test_wallet_file_version_migration_needed(
        stdio, wallet_factory, wallet_path):
    wallet = wallet_factory()
    wallet.save(wallet_path)

    with open(wallet_path, "r") as f:
        data = json.load(f)

    data["properties"]["version"] = 0

    with open(wallet_path, "w") as f:
        json.dump(data, f)

    result = stdio([
        "--wallet", wallet_path, "list-accounts"
    ], success=False)

    assert result["data"]["error"] == "wallet_migration_required"
    assert "Current version: 0" in result["message"]


def test_wallet_file_version_unsupported(stdio, wallet_factory, wallet_path):
    wallet = wallet_factory()
    wallet.save(wallet_path)

    with open(wallet_path, "r") as f:
        data = json.load(f)

    data["properties"]["version"] = 10000

    with open(wallet_path, "w") as f:
        json.dump(data, f)

    result = stdio([
        "--wallet", wallet_path, "list-accounts"
    ], success=False)

    assert result["data"]["error"] == "unsupported_wallet_version"
    assert "newer version 10000" in result["message"]


def test_config_invalid_work_configuration(
        stdio, wallet_path, wallet_factory, tmp_path):
    wallet = wallet_factory(balance=10000, confirmed=True)
    wallet.save(wallet_path)

    CONFIG = """
    [main]
    default_ui_plugin = "stdio"
    default_work_plugin = "local"
    default_network_plugin = "nano_node"
    denomination = "nano"

    [wallet]
    # Default is 0.0001 NANO
    minimum_pocketable_amount = "100000000000000000000000000"

    [work]
    precompute_work = true

        [work.local]
        threads = -100

    [network]

        [network.nano_node]
        concurrent_requests = 100
        url = "http://127.0.0.1:7076"
    """
    config_path = tmp_path / "config.toml"

    with open(config_path, "w") as f:
        f.write(CONFIG)

    result = stdio([
        "--wallet", str(wallet_path), "--config", str(config_path),
        "list-accounts"
    ], success=False)

    assert result["data"]["error"] == "work_configuration_error"


def test_config_invalid_network_configuration(
        stdio, wallet_path, wallet_factory, tmp_path):
    wallet = wallet_factory(balance=10000, confirmed=True)
    wallet.save(wallet_path)

    CONFIG = """
    [main]
    default_ui_plugin = "stdio"
    default_work_plugin = "local"
    default_network_plugin = "nano_node"
    denomination = "nano"

    [wallet]
    # Default is 0.0001 NANO
    minimum_pocketable_amount = "100000000000000000000000000"

    [work]
    precompute_work = true

        [work.local]
        threads = -1

    [network]

        [network.nano_node]
        concurrent_requests = 100
    """
    config_path = tmp_path / "config.toml"

    with open(config_path, "w") as f:
        f.write(CONFIG)

    result = stdio([
        "--wallet", str(wallet_path), "--config", str(config_path),
        "list-accounts"
    ], success=False)

    assert result["data"]["error"] == "network_configuration_error"


def test_network_inaccessible(stdio, wallet_factory, wallet_path):
    wallet = wallet_factory(balance=0)
    wallet.save(wallet_path)

    # Mock node is not active, so trying to run a command
    # that requires network should fail
    result = stdio([
        "--wallet", wallet_path, "sync"
    ], success=False)

    assert result["data"]["error"] == "network_connection_failure"


def test_network_unsupported_protocol_version(
        mock_node, stdio, wallet_factory, wallet_path):
    wallet = wallet_factory(balance=0)
    wallet.save(wallet_path)

    mock_node.add_replay_datasets([
        "active_difficulty", "old_version"
    ]).start()

    result = stdio(["--wallet", wallet_path, "sync"], success=False)

    assert result["data"]["error"] == "unsupported_protocol_version"
    assert "only supports protocol version 16" in result["message"]
    assert "protocol version 17 is required" in result["message"]


def test_option_group(
        stdio, zero_balance_wallet, wallet_path, mock_stdin):
    """
    Test option groups. If value for at least one option in the group is given,
    user won't be prompted for the other fields
    """
    wallet = zero_balance_wallet
    wallet.save(wallet_path)

    # Mock an interactive session.
    # In this scenario, private key will be prompted by the application
    # since no other options are provided
    mock_stdin("1"*64)
    result = stdio(["--wallet", wallet_path, "add-account"])

    assert result["data"]["account_id"] == \
        "xrb_3d78japo7ziqqcsptk47eonzwzwjyaydcywq5ebzowjpxgyehynnjc9pd5zj"
