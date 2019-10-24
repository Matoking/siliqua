import logging

import pytest


def test_cli_help(cli):
    # Print the main help message
    output = cli([
        "--ui", "stdio",
        "--network", "nano_node",
        "--work", "local",
        "--help"
    ]).out

    # Plugin-specific options should be available
    assert "--work-threads" in output
    assert "--network-rpc-url" in output

    assert "change-encryption" in output


def test_cli_command_help(cli):
    # Print a command-specific help message
    output = cli([
        "--ui", "stdio",
        "--network", "nano_node",
        "--work", "local",
        "change-encryption", "--help"
    ]).out

    assert "--new-passphrase" in output
    assert "Change encryption settings" in output


@pytest.mark.parametrize("plugin_type", [
    "ui", "network", "work"
])
def test_cli_incorrect_plugin(cli, plugin_type):
    # Try loading a non-existent plugin
    err = cli([
        "--{}".format(plugin_type), "fake",
        "--help"
    ]).err

    assert "Invalid value for \"--{}\"".format(plugin_type) in err


def test_cli_invalid_config(cli, tmp_path):
    # Create an invalid config file and try to load it
    config_path = tmp_path / "config.toml"

    with open(config_path, "w") as f:
        f.write("invalid == blah")

    err = cli(["--config", config_path]).err

    assert "configuration file is invalid" in err


def test_cli_verbosity(cli):
    # Set different levels of verbosity using the -v flag
    from siliqua import logger

    cli([""])
    assert logger.isEnabledFor(logging.CRITICAL)
    assert logger.isEnabledFor(logging.ERROR)
    assert not logger.isEnabledFor(logging.WARNING)

    cli(["-v"])
    assert logger.isEnabledFor(logging.WARNING)
    assert not logger.isEnabledFor(logging.INFO)

    cli(["-vv"])
    assert logger.isEnabledFor(logging.INFO)
    assert not logger.isEnabledFor(logging.DEBUG)

    cli(["-vvv"])
    assert logger.isEnabledFor(logging.DEBUG)


def test_cli_version(cli):
    output = cli(["--version"]).out

    assert "version" in output
    assert "local, nano_node, nanovault, stdio" in output
