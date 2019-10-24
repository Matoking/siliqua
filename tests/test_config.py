import os

import pytest
from siliqua.config import Config, create_config_files, get_config
from toml.decoder import TomlDecodeError


def test_config_invalid_path():
    # Try loading config from an invalid path
    with pytest.raises(FileNotFoundError):
        Config(path="/invalid/path")


def test_config_invalid_toml(tmp_path):
    # Try loading config file with invalid TOML content
    config_path = tmp_path / "config.toml"

    with open(config_path, "w") as f:
        f.write("invalid == blah")

    with pytest.raises(TomlDecodeError):
        Config(path=config_path)


def test_get_config_defaults(tmp_path):
    # Try loading an empty config file and ensure the defaults are included
    config_path = tmp_path / "config.toml"

    with open(config_path, "w") as f:
        f.write(
            "[main]\n"
            "default_ui_plugin='something'"
        )

    config = get_config(path=config_path)

    assert config.get("main.default_ui_plugin") == "something"
    assert config["main"]["default_ui_plugin"] == "something"
    assert config["main"]["default_work_plugin"] == "local"
    assert config["work"]["precompute_work"] is True
    assert config["work"]["local"]["threads"] == -1


def test_cli_config_priority(tmp_path):
    # Create a config file with CLI and config values used interchangeably
    config_path = tmp_path / "config.toml"

    with open(config_path, "w") as f:
        f.write(
            "[main]\n"
            "test_one='a'\n"
            "test_two='b'\n"
        )

    config = get_config(path=config_path)

    config.set("main.test_one", "aa", update_config=True, update_cli=False)
    config.set("main.test_two", "bb", update_config=False, update_cli=True)

    assert config.get("main.test_one") == "aa"
    assert config.get("main.test_two") == "bb"

    # Save and reload the configuration file.
    # CLI parameters should be discarded.
    config.save()
    config = get_config(path=config_path)

    assert config.get("main.test_one") == "aa"
    assert config.get("main.test_two") == "b"


def test_create_config_files(test_home):
    create_config_files()

    config_path = test_home / ".config" / "Siliqua" / "config.toml"
    example_config_path = (
        test_home / ".config" / "Siliqua" / "config.toml.example"
    )

    assert os.path.exists(config_path)
    assert os.path.exists(example_config_path)

    # config.toml will not get overwritten, but config.toml.example will
    # get overwritten
    with open(config_path, "w") as f:
        f.write("OVERWRITTEN")

    with open(example_config_path, "w") as f:
        f.write("OVERWRITTEN")

    create_config_files()

    with open(config_path, "r") as f:
        assert "OVERWRITTEN" in f.read()

    with open(example_config_path, "r") as f:
        assert "OVERWRITTEN" not in f.read()
