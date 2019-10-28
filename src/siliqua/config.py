import os
import toml

from appdirs import AppDirs

__all__ = (
    "get_appdirs", "get_default_config_dir", "get_default_config_path",
    "get_config", "create_config_files"
)


def get_appdirs():
    dirs = AppDirs("Siliqua", "Matoking")

    return dirs


def get_default_config_dir():
    """
    Get the default configuration directory for the application

    :returns: Configuration path
    :rtype: str
    """
    return get_appdirs().user_config_dir


def get_default_config_path():
    """
    Get the path to the default configuration file

    :returns: Configuration file path
    :rtype: str
    """
    return os.path.join(
        get_appdirs().user_config_dir,
        "config.toml"
    )


DEFAULT_CONFIG = """
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
precompute_multiplier = 1.25

    [work.local]
    # -1 = use half of physical CPU cores (default)
    threads = -1

[network]

    [network.nano_node]
    # RECOMMENDED plugin
    # 'nano_node' requires a NANO node with a version of 19 or higher

    # rpc_url is REQUIRED
    # rpc_url = "http://localhost:7076"

    # ws_url is optional, but allows new transactions to be received in
    # real-time
    # ws_url = "http://localhost:7078"

    concurrent_requests = 100

    [network.nanovault]
    # 'nanovault' uses NanoVault.io-compatible servers and is
    # the easiest network plugin to set up.
    # See https://nanovault.io for details
    #
    # The plugin is unable to track network difficulty and may
    # result in transactions getting delayed when the network is under
    # high activity

    # rpc_url (aka API Server) is REQUIRED
    # rpc_url = ""

    # ws_url (aka Updates Server) is optional but recommended
    # ws_url = ""
"""[1:]  # Strip the first newline


class Config:
    """
    Config object that supports multi-level configuration fields
    and values from two different sources: configuration file and CLI
    parameters.

    If different values are provided in the configuration file and as
    a CLI parameter, the CLI parameter takes priority.
    """
    def __init__(self, path, defaults=None):
        self.cli_params = {}
        if not defaults:
            self.config = {}
        else:
            self.config = defaults.copy()

        with open(path, "r") as f:
            self._merge(toml.load(f))

        self.path = path

    def save(self):
        """
        Save the configuration to a file.

        Only values that belong to the configuration file are saved.
        """
        with open(self.path, "w") as f:
            f.write(toml.dumps(self.config))

    def get(self, key, default=None):
        """
        Get the configuration field's value

        :param str key: Key name. Different levels are separated with a dot.
                        Eg. "network.nano_node.ws_url"
        :param str val: Value
        :param default: Default value in case the field does not exist

        :return: Value if found, default value otherwise
        """
        keys = key.split(".")

        cli_d = self.cli_params
        conf_d = self.config
        for i, key in enumerate(keys):
            is_last = (i+1) == len(keys)

            if is_last:
                try:
                    return cli_d[key]
                except KeyError:
                    return conf_d.get(key, default)
            else:
                cli_d = cli_d.get(key, {})
                conf_d = conf_d.get(key, {})

    def set(self, key, val, update_config=True, update_cli=False):
        """
        Set the configuration field's value

        :param str key: Key name. Different levels are separated with a dot.
                        Eg. "network.nano_node.ws_url"
        :param str val: Value
        :param bool update_config: Whether the value belongs to the
                                   configuration file
        :param bool pdate_cli: Whether the value is provided from a CLI
                               parameter
        """
        keys = key.split(".")

        cli_d = self.cli_params
        conf_d = self.config
        for i, key in enumerate(keys):
            is_last = (i+1) == len(keys)

            if is_last:
                if update_config:
                    conf_d[key] = val
                if update_cli:
                    cli_d[key] = val
            else:
                if key not in cli_d:
                    cli_d[key] = {}
                cli_d = cli_d[key]

                if key not in conf_d:
                    conf_d[key] = {}
                conf_d = conf_d[key]

    def _merge(self, src, dest=None):
        """
        Merge a dict into the current configuration. This is used
        to update the config with default values.
        """
        if dest is None:
            dest = self.config

        for k, v in src.items():
            if isinstance(v, dict):
                item = dest.setdefault(k, {})
                self._merge(src=v, dest=item)
            else:
                dest[k] = v

    def __getitem__(self, key):
        return self.config[key]


def create_config_files():
    """
    Create a configuration directory and add the default files inside it
    """
    config_dir_path = get_default_config_dir()
    config_path = get_default_config_path()
    config_default_file_path = "{}.example".format(config_path)

    try:
        os.makedirs(config_dir_path)
    except FileExistsError:
        pass

    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            f.write(DEFAULT_CONFIG)

    with open(config_default_file_path, "w") as f:
        f.write(DEFAULT_CONFIG)


def get_config(path=None):
    """
    Load configuration from the given path

    :path str path: Path to the configuration file. Defaults to the
                    user-specific default location.
    """
    if not path:
        path = get_default_config_path()

    config = Config(path, defaults=toml.loads(DEFAULT_CONFIG))

    return config
