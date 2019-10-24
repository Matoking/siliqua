"""
User interface plugin to start the :class:`siliqua.server.WalletServer` instance
and allowing the user to interact with it.
"""
from siliqua import logger as root_logger  # isort:skip
logger = root_logger.getChild("gui")

import click

from siliqua.server import WalletServer


class BaseUI:
    """
    Base class for user interface plugins
    """
    def __init__(self, config):
        """
        :param config: Config instance
        :type config: siliqua.config.Config
        """
        self.config = config

    def get_cli(self):
        """
        Overridable method to return Click commands or a Click group
        """
        raise NotImplementedError

    def run(self, server, ctx, **kwargs):
        """
        Overridable method to start the GUI from server instance and a
        Click context containing command-line parameters
        """
        raise NotImplementedError

    def run_from_cli(self, ctx, **kwargs):
        ctx = click.get_current_context()

        server = WalletServer(
            config=ctx.obj["config"],
            work=ctx.obj.get("work", None),
            network=ctx.obj.get("network", None),
            wallet=ctx.obj.get("wallet", None)
        )

        return self.run(server=server, ctx=ctx, **kwargs)


# TODO: We could scan the directories for built-in GUI plugins, but for now
# just import them directly
from .stdio import *  # isort:skip
