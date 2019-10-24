import pkg_resources
import pkgutil
import os
import importlib

from .exceptions import ConfigurationError


__all__ = (
    "get_ui_plugins", "get_work_plugins", "get_network_plugins",
    "BasePlugin")


def get_plugins_with_name(pkg_name, mod_name):
    # Load separately installed plugins
    plugins = {
        entry_point.name: entry_point.load() for entry_point
        in pkg_resources.iter_entry_points("siliqua.plugins.{}".format(
            pkg_name
        ))
    }

    root_mod = importlib.import_module("siliqua.{}".format(pkg_name))

    # Load the plugins included with this package
    for pkg in pkgutil.walk_packages(root_mod.__path__):
        mod = importlib.import_module(
            "siliqua.{}.{}".format(pkg_name, pkg.name)
        )
        try:
            plugins[pkg.name] = getattr(mod, mod_name)
        except AttributeError:
            # If the module doesn't have a plugin, skip it
            continue

    return plugins


def get_ui_plugins():
    """
    Get all installed UI plugins
    """
    return get_plugins_with_name("ui", "WalletUi")


def get_work_plugins():
    """
    Get all installed work plugins
    """
    return get_plugins_with_name("work", "WorkPlugin")


def get_network_plugins():
    """
    Get all installed network plugins
    """
    return get_plugins_with_name("network", "NetworkPlugin")


class BasePlugin:
    """
    Base class used for plugins. Each plugin uses an
    :class:`siliqua.config.Config` instance to check if the configuration
    is complete to start the plugin.
    """
    PLUGIN_TYPE = None
    PLUGIN_NAME = None

    def __init__(self, **kwargs):
        if not kwargs.get("config", None):
            raise ValueError("Plugin requires a 'config' keyword argument")

        self.config = kwargs["config"]

    def _cli_param_callback(self, ctx, param, value):
        """
        Update the Config instance with CLI parameters
        """
        if value is None:
            # Value was not provided via CLI
            return

        # For example, if a "work" type plugin called "local" is active
        # and the `--work-threads` parameter is provided, update the
        # field "work.local.threads" with the configuration value
        field_name = "_".join(param.name.split("_")[1:])

        self.config.set(
            "{}.{}.{}".format(self.PLUGIN_TYPE, self.PLUGIN_NAME, field_name),
            value,
            update_config=False, update_cli=True)

    def get_cli_params(self):
        cli_params = self._get_cli_params()

        # Add a callback for each parameter to override the corresponding
        # configuration value
        for cli_param in cli_params:
            cli_param.help = "".join([
                "(Plugin: {}.{})\n".format(
                    self.PLUGIN_TYPE, self.PLUGIN_NAME
                ),
                cli_param.help
            ])
            cli_param.callback = self._cli_param_callback

        return cli_params

    def _get_cli_params(self):
        """
        Return a list of Click options and parameters also corresponding
        to the different configuration fields

        :returns: List of :class:`click.Parameter` and `click.Option` instances
        """
        raise NotImplementedError

    @property
    def is_config_valid(self):
        """
        Is the plugin-specific configuration valid. The plugin
        cannot be started if the configuration is invalid.

        .. note:: Implement :meth:`siliqua.plugins.BasePlugin.validate_config`
                  instead of overriding this property to validate configurations.

        :returns: Is configuration valid
        :rtype: bool
        """
        try:
            self.validate_config()
            return True
        except ConfigurationError:
            return False

    def validate_config(self):
        """
        Method that validates the plugin-specific configuration and
        raises :class:`siliqua.exceptions.ConfigurationError` for any
        incomplete or invalid configuration field
        """
        raise NotImplementedError
