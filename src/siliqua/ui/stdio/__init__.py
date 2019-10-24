from siliqua.ui import logger as root_logger  # isort:skip
logger = root_logger.getChild("stdio")

import json
import os
import sys
from functools import wraps

import click

from siliqua.server import WalletServer
from siliqua.ui import BaseUI
from siliqua.ui.stdio.commands import COMMANDS
from siliqua.ui.stdio.exceptions import StdioError
from siliqua.ui.stdio.util import to_cli_command


def wrap_command(cmd_func):
    """
    Wrapper used when a command is called using the CLI to ensure the
    correct function is called.

    Any exception/output is captured and printed as a JSON formatted string
    """
    def inner_function(ui):
        @wraps(ui)
        def wrapper(*args, **kwargs):
            kwargs["cmd_func"] = cmd_func

            try:
                result = ui.run_from_cli(*args, **kwargs)
                result.show()
                return
            except StdioError as exc:
                exc.show()
                sys.exit(-1)

        return wrapper

    return inner_function


class StdioUI(BaseUI):
    """
    User interface plugin that implements a command-line interface
    for wallet usage
    """
    def get_cli(self):
        """
        Get Click command for each individual stdio command
        """
        commands = []

        for command in COMMANDS:
            commands.append(
                to_cli_command(
                    command,
                    click.pass_context(wrap_command(command)(self))
                )
            )

        return click.Group(commands=commands)

    def run(self, server, ctx, cmd_func, **kwargs):
        """
        Run the given Click command which contains the underlying wrapped
        command
        """
        if cmd_func.wallet_required:
            kwargs["wallet_path"] = ctx.parent.params.get("wallet", None)
            kwargs["passphrase"] = ctx.params.get("passphrase", None)

        result = None
        try:
            result = cmd_func(server=server, **kwargs)
        finally:
            server.stop()

        return result
