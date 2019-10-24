import decimal
import inspect
import itertools
import json
import os
import sys
from collections import namedtuple
from contextlib import contextmanager
from functools import wraps
from getpass import getpass

import click

from nanolib import NanoDenomination, convert, is_account_id_valid
from nanolib.exceptions import InvalidSeed
from siliqua.exceptions import ConfigurationError, WalletFileLocked
from siliqua.network.exceptions import UnsupportedProtocolVersion
from siliqua.wallet import Wallet
from siliqua.wallet.exceptions import (AccountAlreadyExists,
                                       InsufficientBalance,
                                       InvalidEncryptionKey,
                                       TransactionAlreadyExists,
                                       UnsupportedWalletVersion,
                                       WalletFileInvalid, WalletLocked,
                                       WalletMigrationRequired)
from siliqua.wallet.secret import Secret

from . import logger
from .exceptions import StdioError
from .params import BaseParam

EXCEPTION_TO_ERROR = {
    AccountAlreadyExists: {
        "error": "account_already_exists",
        "message": "Account already exists in the wallet"
    },
    TransactionAlreadyExists: {
        "error": "transaction_already_exists",
        "message": "Another block with the same transaction ID already exists "
                   "in the wallet"
    },
    InvalidSeed: {
        "error": "invalid_seed",
        "message": "Seed is invalid"
    },
    InsufficientBalance: {
        "error": "insufficient_balance",
        "message": "Insufficient balance"
    },
    InvalidEncryptionKey: {
        "error": "incorrect_passphrase",
        "message": "Incorrect passphrase"
    }
}


class StdioResult:
    """
    Result created by running a command. Result can be successful or a failure.

    Result can be printed in JSON format
    """
    def __init__(self, data=None, error=None):
        if not data:
            data = {}

        self.data = data
        self.error = error

    def show(self):
        """
        Print the result to stdio in JSON format
        """
        status = "success" if not self.error else "error"

        result = {
            "status": status,
        }

        if self.data:
            result["data"] = self.data

        if self.error:
            if "data" not in result:
                result["data"] = {}

            result["data"]["error"] = self.error.code
            result["message"] = self.error.message

        print(json.dumps(result, indent=4, sort_keys=True))


def raise_common_error(exc):
    """
    Try raising an exception as a StdioError that can be printed in JSON
    format
    """
    if type(exc) in EXCEPTION_TO_ERROR.keys():
        raise StdioError(
            EXCEPTION_TO_ERROR[type(exc)]["error"],
            EXCEPTION_TO_ERROR[type(exc)]["message"]
        )

    raise exc


def to_cli_command(func, callback):
    """
    Convert a stdio command function into a Click command and return it
    """
    if "cli_command" not in vars(func):
        raise ValueError("Function is not a CLI method")

    # Add params
    cli_params = []
    for cli_param in func.cli_params:
        cli_params.append(cli_param.to_cli_parameter())

    cli_name = func.__name__.replace("_", "-")
    command = click.Command(
        name=cli_name,
        help=func.help_text,
        short_help=func.short_help_text,
        params=cli_params,
        callback=callback)

    return command


def parse_manual_params(func, kwargs):
    """
    Parse command parameters through a dict instead of the normal CLI
    interface.

    This is used when calling the commands outside the Click-based
    interface
    """
    parameters = func.cli_params

    parsed_kwargs = {}

    for param_type in parameters:
        val = kwargs.get(param_type.name, None)
        val = param_type.parse(val)

        parsed_kwargs[param_type.name] = val

    return parsed_kwargs


def get_cli_params(func):
    """
    Return a list of stdio command's parameters by iterating through
    its annotations
    """
    parameters = list(inspect.signature(func).parameters.values())
    cli_params = []

    for parameter in parameters:
        if parameter.name == "server":
            continue

        annotation = parameter.annotation

        if not isinstance(annotation, BaseParam):
            annotation = annotation()

        if isinstance(annotation, BaseParam):
            annotation.name = parameter.name
            cli_params.append(annotation)

    return cli_params


def cli_command(
        wallet_required=True,
        help_text=None,
        short_help_text=None,
        start_work=True,
        start_network=True):
    """
    Stdio command decorator that marks a function as a CLI command
    and allows configuring common behavior.

    :param bool wallet_required: Whether the command requires a wallet to be
                                 loaded when called
    :param str help_text: Long help text
    :param str short_help_text: Abbreviated help text
    :param bool start_work: Whether to start the work provider automatically
    :param bool start_network: Whether to start the network provider
                               automatically
    """
    def inner_function(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            server = kwargs.get("server", None)
            passphrase = kwargs.get("passphrase", None)

            # Convert empty string parameters to None
            kwargs = {
                k: None if v == "" else v for k, v in kwargs.items()
            }

            try:
                server.work.validate_config()
            except ConfigurationError as exc:
                raise StdioError(
                    "work_configuration_error",
                    "Work plugin has incomplete configuration: {}".format(
                        str(exc)
                    )
                )

            try:
                server.network.validate_config()
            except ConfigurationError as exc:
                raise StdioError(
                    "network_configuration_error",
                    "Network plugin has incomplete configuration: {}".format(
                        str(exc)
                    )
                )

            if wallet_required:
                if not kwargs["wallet_path"]:
                    raise StdioError(
                        "wallet_required",
                        "--wallet is required"
                    )

                try:
                    wallet_encrypted = Wallet.is_wallet_file_encrypted(
                        kwargs["wallet_path"]
                    )

                    if wallet_encrypted and sys.stdout.isatty():
                        print("Passphrase required to open encrypted wallet.")
                        passphrase = getpass("Passphrase: ")

                    server.load_wallet(
                        path=kwargs["wallet_path"],
                        passphrase=passphrase
                    )
                except InvalidEncryptionKey:
                    raise StdioError(
                        "incorrect_passphrase",
                        "Incorrect passphrase"
                    )
                except WalletLocked:
                    raise StdioError(
                        "wallet_encrypted",
                        "Wallet is encrypted but no passphrase was provided"
                    )
                except WalletFileLocked:
                    raise StdioError(
                        "wallet_locked",
                        "Wallet is locked and in use by another process"
                    )
                except WalletFileInvalid:
                    raise StdioError(
                        "wallet_invalid",
                        "Wallet file is invalid. It may be corrupted."
                    )
                except WalletMigrationRequired as exc:
                    raise StdioError(
                        "wallet_migration_required",
                        "Wallet file needs to be migrated before it can be "
                        "used. Current version: {}, "
                        "required version: {}".format(
                            exc.wallet_version, exc.required_version
                        )
                    )
                except UnsupportedWalletVersion as exc:
                    raise StdioError(
                        "unsupported_wallet_version",
                        "Wallet file with newer version {} was loaded but "
                        "only {} is supported. The wallet might have been "
                        "created with a newer version of this "
                        "application.".format(
                            exc.wallet_version, exc.required_version
                        )
                    )

                kwargs["server"] = server

                if start_work:
                    server.start_work()
                if start_network:
                    server.start_network()
                    try:
                        server.network.wait_for_connection(timeout=5)
                    except TimeoutError:
                        raise StdioError(
                            "network_connection_failure",
                            "Network plugin couldn't establish a connection."
                        )
                    except UnsupportedProtocolVersion as exc:
                        raise StdioError(
                            "unsupported_protocol_version",
                            "NANO node only supports protocol version "
                            f"{exc.current_version} while "
                            f"protocol version {exc.required_version} is "
                            "required"
                        )

                del kwargs["wallet_path"]

            try:
                return func(*args, **kwargs)
            except Exception as exc:
                # Raise a corresponding StdioError for a common error
                # if possible
                raise_common_error(exc)

        wrapper.cli_params = get_cli_params(wrapper)
        wrapper.cli_command = True
        wrapper.wallet_required = wallet_required
        wrapper.help_text = help_text
        wrapper.short_help_text = short_help_text
        wrapper.start_work = start_work
        wrapper.start_network = start_network

        return wrapper

    return inner_function


@contextmanager
def unlock_wallet(*args, **kwargs):
    """
    Context manager to temporarily unlock the wallet.

    Convenience function is also returned that allows secret fields to be
    read when the wallet is unlocked.
    """
    server = kwargs.get("server", None)
    passphrase = kwargs.get("passphrase", None)

    def peek(val):
        if isinstance(val, Secret):
            return val.get(secret_key=server.wallet.secret_key)

        return val

    if not passphrase and not server.wallet.secrets_unlocked:
        print("Passphrase required to access wallet secrets.")
        passphrase = getpass("Passphrase: ")

    try:
        server.wallet.unlock(passphrase)
        yield peek
    finally:
        # Ensure the wallet is locked afterwards no matter what if an exception
        # happens
        server.wallet.lock()


class PaginationResults:
    """
    Result object that can be iterated to get paginated results.

    :ivar results: List of results
    :ivar total_count: Total count of the original list before pagination
    """
    __slots__ = ("results", "total_count")

    def __init__(self, results, total_count):
        self.results = results
        self.total_count = int(total_count)

    def __iter__(self):
        yield from self.results


def paginate_list(entries, limit, offset, descending):
    """
    Paginate a list and return a PaginationResults object

    :param list entries: List of entries to paginate
    :param int limit: Maximum amount of entries to return
    :param int offset: Amount of entries to skip
    :param bool descending: Whether to return entries in descending or
                            ascending order

    :returns: Pagination results
    :rtype: PaginationResults
    """
    total_count = len(entries)

    if descending:
        end = total_count - offset
        start = end - limit
        if start < 0:
            start = 0
    else:
        start = offset
        end = offset + limit
        if end > total_count:
            end = total_count

    results = entries[start:end]

    if descending:
        results.reverse()

    return PaginationResults(
        results=results, total_count=total_count
    )


def truncate_ordered_dict(d, max_length=10):
    """
    Truncate an ordered dict starting from the oldest entries
    until it has the given maximum length

    :param d: OrderedDict instance
    :param int max_count: Maximum length of the dict
    """
    while len(d) > max_length:
        d.popitem(last=False)
