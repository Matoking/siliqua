import decimal
import os
import click
import sys

from nanolib import (
    NanoDenomination, convert, is_account_id_valid, validate_public_key,
    validate_private_key, validate_block_hash
)
from . import logger


class GroupClickOption(click.Option):
    """
    Subclass of click.Option that allows options to be grouped
    with the :attr:`group_name` attribute.

    This means that if at least one option in the same group already
    has a value, no prompts are created for other options in the group.
    """
    def __init__(self, *args, **kwargs):
        self.group_name = kwargs.pop("group_name", None)

        super().__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        value, args = super().handle_parse_result(ctx, opts, args)

        if self.group_name is not None and value not in (None, ""):
            ctx.meta["siliqua.group_{}".format(self.group_name)] = True

        return value, args

    def prompt_for_value(self, ctx):
        group_populated = (
            self.group_name and
            ctx.meta.get("siliqua.group_{}".format(self.group_name))
        )

        result = None
        if not group_populated:
            # Only prompt from user if user hasn't provided a value for
            # any of the other options in the same group
            result = super().prompt_for_value(ctx)

        return result


class BaseParam:
    """
    Base class for different parameter types
    """
    def __init__(self, **kwargs):
        self.name = None

    def parse(self, val):
        """
        Parse the received value. If the value is invalid ValueError
        should be raised with a human-readable error message.

        :param str val: Value to parse

        :return: Parsed value
        """
        raise NotImplementedError

    def get_click_kwargs(self):
        """
        Get a dict of kwargs to pass to the underlying :class:`click.Option`
        class

        :return: Dict of keyword arguments
        :rtype: dict
        """
        return {}

    def to_cli_parameter(self):
        """
        Convert parameter to a :class:`click.Argument`

        :return: Click argument
        :rtype: :class:`click.Argument`
        """
        kwargs = {
            "required": True,
            "param_decls": [self.name],
            "callback": self.click_callback,
            "type": str
        }

        kwargs.update(self.get_click_kwargs())

        return click.Argument(**kwargs)

    def click_callback(self, ctx, param, value):
        """
        Function called by Click to parse the value
        """
        try:
            return self.parse(value)
        except ValueError as e:
            raise click.BadParameter(e)


class BaseOption(BaseParam):
    """
    Base class for different option types
    """
    def __init__(self, **kwargs):
        super(BaseOption, self).__init__(**kwargs)

        self.help_text = kwargs.get("help_text", None)
        self.group_name = kwargs.get("group_name", None)

    def to_cli_parameter(self):
        kwargs = {
            "required": False,
            "param_decls": ["--{}".format(self.name.replace("_", "-"))],
            "callback": self.click_callback,
            "group_name": self.group_name,
            "type": str
        }

        kwargs.update(self.get_click_kwargs())

        return GroupClickOption(**kwargs)


class RepeatParams(BaseParam):
    """
    Parameter that can be repeated indefinitely.

    The underlying parameter can consist of a single parameter, or multiple
    parameters.
    """
    def __init__(self, names, types, **kwargs):
        super(RepeatParams, self).__init__(**kwargs)

        self.names = names
        self.types = types

    def parse(self, val):
        values = val.split(",")

        if len(values) != len(self.names):
            raise ValueError(
                "expected a ({}) sequence, "
                "got a wrong amount of parameters".format(
                    ", ".join(self.names)
                )
            )

        param = {}

        for name, param_cls, value in zip(self.names, self.types, values):
            try:
                value = param_cls().parse(value)
            except ValueError as exc:
                raise ValueError("invalid '{}': {}".format(name, str(exc)))
            param[name] = value

        return param

    def get_click_kwargs(self):
        return {"nargs": -1}

    def click_callback(self, ctx, param, value):
        # click returns a list of tuples, so parse value as a list
        # instead of a single value
        try:
            return [self.parse(val) for val in value]
        except ValueError as e:
            raise click.BadParameter(e)


class FilePathParam(BaseParam):
    """
    Parameter for a file path
    """
    def __init__(self, **kwargs):
        """
        :param bool exists: Whether the file must exist
        """
        super(FilePathParam, self).__init__(**kwargs)

        self.exists = kwargs.get("exists", True)

    def parse(self, val):
        val = os.path.abspath(val)

        if self.exists and not os.path.exists(val):
            raise ValueError("does not exist")

        if os.path.isdir(val):
            raise ValueError("is a directory, not a file")

        return val

    def get_click_kwargs(self):
        return {
            "type": click.Path(
                file_okay=True, dir_okay=False, exists=self.exists
            )
        }


class StrParam(BaseParam):
    """
    String parameter
    """
    def parse(self, val):
        if isinstance(val, bytes):
            raise ValueError("is not a string")

        return str(val)


class StrOption(BaseOption):
    """
    String option
    """
    def parse(self, val):
        if val is None:
            return None

        if isinstance(val, bytes):
            raise ValueError("is not a string")

        return str(val)


class SecureStrOption(BaseOption):
    """
    Secure string option.

    Secure strings can be passed using environment variables or
    prompted directly from the user in an interactive session
    """
    def __init__(self, **kwargs):
        super(SecureStrOption, self).__init__(**kwargs)

        self.required = kwargs.get("required", False)

    def parse(self, val):
        return val

    def to_cli_parameter(self):
        # Are we in a tty-like device (eg. can the user input anything, or
        # we being piped?)
        # In the latter case, don't try to prompt the user for anything
        is_atty = sys.stdout.isatty()

        if self.required:
            return GroupClickOption(
                required=True,
                param_decls=[
                    "--{}".format(self.name.replace("_", "-")), self.name
                ],
                group_name=self.group_name,
                show_envvar=True,
                envvar=self.name.upper(),
                callback=self.click_callback,
                prompt=is_atty,
                hide_input=True
            )

        return GroupClickOption(
            param_decls=[
                "--{}".format(self.name.replace("_", "-")),
                self.name
            ],
            group_name=self.group_name,
            required=False,
            default="",
            callback=self.click_callback,
            show_envvar=True,
            envvar=self.name.upper(),
            prompt=is_atty,
            hide_input=True
        )

    def get_click_kwargs(self):
        return {
            "default": None,
            "envvar": self.name.upper(),
        }


class PassphraseOption(SecureStrOption):
    """
    Passphrase option.

    Is essentially the same as :class:`SecureStrOption` except that
    in an interactive session the passphrase prompt is postponed
    until needed.
    """
    def __init__(self, **kwargs):
        super(PassphraseOption, self).__init__(**kwargs)

    def to_cli_parameter(self):
        # When the user is using a wallet through a terminal, don't prompt
        # for the wallet passphrase using a Click parameter.
        # Instead, passphrase prompt will be postponed until the wallet
        # is actually unlocked
        is_atty = sys.stdout.isatty()

        if is_atty:
            return GroupClickOption(
                param_decls=[
                    "--{}".format(self.name.replace("_", "-")),
                    self.name
                ],
                group_name=self.group_name,
                required=False,
                default="",
                callback=self.click_callback,
                show_envvar=True,
                envvar=self.name.upper(),
                prompt=False
            )

        return GroupClickOption(
            param_decls=[
                "--{}".format(self.name.replace("_", "-")),
                self.name
            ],
            group_name=self.group_name,
            required=False,
            default="",
            callback=self.click_callback,
            show_envvar=True,
            envvar=self.name.upper(),
            prompt=is_atty,
            hide_input=True
        )


class BoolParam(BaseParam):
    """
    Bool parameter. Accepts different string aliases.
    """
    def parse(self, val):
        VALUES = {
            "on": True,
            "1": True,
            "yes": True,
            "true": True,

            "off": False,
            "0": False,
            "no": False,
            "false": False
        }

        if val in (True, False):
            return val
        else:
            try:
                return VALUES[val]
            except KeyError:
                raise ValueError("is not a valid truth value")


class BoolOption(BaseOption):
    """
    Bool option that uses two flag parameters.
    """
    def __init__(self, **kwargs):
        super(BoolOption, self).__init__(**kwargs)

        self.default = kwargs.get("default", None)

        if self.default not in (True, False, None):
            raise ValueError("Default must be True or False")

    def parse(self, val):
        if val is None:
            if self.default is not None:
                return self.default
            else:
                raise ValueError("is required")

        if val not in (True, False):
            raise ValueError("is not a flag")

        return val

    def to_cli_parameter(self):
        kwargs = {
            "required": True,
            "param_decls": [
                "--{name}/--no-{name}".format(name=self.name.replace("_", "-"))
            ],
            "group_name": self.group_name
        }

        if self.default is not None:
            kwargs["required"] = False
            kwargs["default"] = self.default

        return GroupClickOption(**kwargs)


class IntParam(BaseParam):
    """
    Integer parameter. Floats are not accepted.
    """
    def parse(self, val):
        is_str = isinstance(val, str)
        if is_str:
            if val.isdigit():
                return int(val)
            else:
                raise ValueError("is not an integer")

        if not isinstance(val, int) or val is None:
            raise ValueError("is not an integer")

        return int(val)


class FloatParam(BaseParam):
    """
    Float parameter. Integers are also accepted.
    """
    def parse(self, val):
        return float(val)


class FloatOption(BaseOption):
    """
    Float option. Integers are also accepted.
    """
    def parse(self, val):
        if val is not None:
            return float(val)
        else:
            return None

    def get_click_kwargs(self):
        return {
            "type": float
        }


class IntRangeOption(BaseOption):
    """
    Integer range option. Only integers in the given inclusive range are
    accepted.
    """
    def __init__(self, **kwargs):
        super(IntRangeOption, self).__init__(**kwargs)

        self.default = kwargs.get("default", None)
        self.minimum = kwargs.get("minimum", None)
        self.maximum = kwargs.get("maximum", None)

        if not (self.minimum is not None and self.maximum is not None):
            raise ValueError(
                "Range requires both 'minimum' and 'maximum' to be defined")

    def parse(self, val):
        if val is None:
            if self.default is not None:
                return self.default
            else:
                raise ValueError("is required")

        if not isinstance(val, int):
            raise ValueError("is not an integer")

        if self.minimum is not None:
            if val < self.minimum or val > self.maximum:
                raise ValueError(
                    "is not in range {}-{}".format(self.minimum, self.maximum)
                )

        return val

    def get_click_kwargs(self):
        minimum = self.minimum
        maximum = self.maximum

        kwargs = {
            "required": not bool(self.default is not None),
            "type": click.IntRange(minimum, maximum) if minimum else int
        }

        if self.default is not None:
            kwargs["default"] = self.default

        return kwargs


class AccountParam(BaseParam):
    """
    Account ID parameter
    """
    def parse(self, val):
        if not is_account_id_valid(val):
            raise ValueError("is not a valid account ID")

        return val


class AccountOption(BaseOption):
    """
    Account ID option
    """
    def parse(self, val):
        if val is None or val.strip() == "":
            val = None

        if val is not None and not is_account_id_valid(val):
            raise ValueError("is not a valid account ID")

        return val


class PublicKeyParam(BaseParam):
    """
    Public key parameter. Public key is accepted only in hexadecimal format.
    """
    def parse(self, val):
        try:
            validate_public_key(val)
            return val
        except ValueError:
            raise ValueError("is not a valid public key")


class PublicKeyOption(BaseOption):
    """
    Public key option. Public key is accepted only in hexadecimal format.
    """
    def parse(self, val):
        if val is None or val.strip() == "":
            return None

        try:
            validate_public_key(val)
            return val
        except ValueError:
            raise ValueError("is not a valid public key")


class PrivateKeyParam(BaseParam):
    """
    Private key parameter. Private key is accepted only in hexadecimal format.
    """
    def parse(self, val):
        try:
            validate_private_key(val)
            return val
        except ValueError:
            raise ValueError("is not a valid private key")


class PrivateKeyOption(SecureStrOption):
    """
    Private key option. Private key is accepted only in hexadecimal format.
    """
    def parse(self, val):
        if val is None or val.strip() == "":
            return None

        try:
            validate_private_key(val)
            return val
        except ValueError:
            raise ValueError("is not a valid private key")


class BlockHashParam(BaseParam):
    """
    Block hash parameter.
    """
    def parse(self, val):
        try:
            validate_block_hash(val)
            return val
        except ValueError:
            raise ValueError("is not a valid block hash")


class AmountParam(BaseParam):
    """
    Amount parameter.

    Amount is accepted as a single integer (denomination is assumed to be raw)
    or "<amount> <unit>" string where `amount` can be a decimal and `unit`
    is the NANO denomination.
    """
    def parse(self, val):
        ERROR_MESSAGE = (
            "value does not follow the format '<AMOUNT> <UNIT>' or "
            "'<AMOUNT IN RAW>'"
        )

        try:
            if val.isdigit():
                return int(val)
        except ValueError:
            pass

        try:
            amount, denom = val.split(" ")
        except ValueError:
            raise ValueError(ERROR_MESSAGE)

        try:
            amount = decimal.Decimal(amount)
        except decimal.InvalidOperation:
            raise ValueError("invalid amount")

        try:
            denom = NanoDenomination(denom)
        except ValueError:
            raise ValueError("invalid NANO denomination")

        val = convert(amount, source=denom, target=NanoDenomination.RAW)

        return int(val)
