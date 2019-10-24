import binascii
import uuid
from collections import UserDict
from functools import cmp_to_key, wraps

from nanolib import Block as RawBlock
from nanolib import nbase32_to_bytes, get_account_id

__all__ = (
    "RawBlock", "BlockProxy", "Callbacks", "CallbackSlot", "AccountIDDict"
)


class BlockProxy(object):
    """
    Allow an object containing 'block' Block instance to access underlying
    RawBlock fields directly.

    Eg.
    instead of `block.block.account`, you can access `block.account`
    """
    # Writable fields
    block_type = property(
        lambda x: x.block.block_type,
        lambda x, v: x.block.set_block_type(v))
    account = property(
        lambda x: x.block.account,
        lambda x, v: x.block.set_account(v))
    source = property(
        lambda x: x.block.source,
        lambda x, v: x.block.set_source(v))
    previous = property(
        lambda x: x.block.previous,
        lambda x, v: x.block.set_previous(v))
    destination = property(
        lambda x: x.block.destination,
        lambda x, v: x.block.set_destination(v))
    representative = property(
        lambda x: x.block.representative,
        lambda x, v: x.block.set_representative(v))
    balance = property(
        lambda x: x.block.balance,
        lambda x, v: x.block.set_balance(v))
    link = property(
        lambda x: x.block.link,
        lambda x, v: x.block.set_link(v))
    link_as_account = property(
        lambda x: x.block.link_as_account,
        lambda x, v: x.block.set_link_as_account(v))
    signature = property(
        lambda x: x.block.signature,
        lambda x, v: x.block.set_signature(v))
    work = property(
        lambda x: x.block.work,
        lambda x, v: x.block.set_work(v))
    difficulty = property(
        lambda x: x.block.difficulty,
        lambda x, v: x.block.set_difficulty(v))

    # Read-only fields
    tx_type = property(lambda x: x.block.tx_type)
    block_hash = property(lambda x: x.block.block_hash)
    work_block_hash = property(lambda x: x.block.work_block_hash)
    complete = property(lambda x: x.block.complete)
    has_valid_work = property(lambda x: x.block.has_valid_work)
    has_valid_signature = property(lambda x: x.block.has_valid_signature)
    work_value = property(lambda x: x.block.work_value)

    # Methods
    verify_work = property(lambda x: x.block.verify_work)
    verify_signature = property(lambda x: x.block.verify_signature)
    sign = property(lambda x: x.block.sign)
    solve_work = property(lambda x: x.block.solve_work)
    json = property(lambda x: x.block.json)

    # 'account' alias
    account_id = property(
        lambda x: x.block.account,
        lambda x, v: x.block.set_account(v))


class CallbackSlot:
    """
    Callback container with an identifier and arbitrary amount of
    callback functions
    """
    def __init__(self, name):
        """
        :param str name: Name for the action triggering a callback
        """
        self.name = name

        self.funcs = []

    def add(self, func, func_id=None):
        """
        Add a callback function. If `func_id` is not provided, an
        identifier for the callback function is created automatically

        :param func: Callback function to add
        :param str func_id: Unique identifier for the callback identifier
                            to remove the callback function later
        """
        if not func_id:
            func_id = uuid.uuid4().hex

        self.funcs.append((func_id, func))

        return func_id

    def remove(self, func_id):
        """
        Remove a callback function using its identifier.

        :param str func_id: Unique identifier for a callback function
        """
        func_id_to_remove = func_id

        self.funcs = [
            (func_id, func) for func_id, func in self.funcs
            if func_id_to_remove != func_id
        ]

    def invoke(self, *args, **kwargs):
        """
        Run all callback functions with the given arguments
        """
        for _, func in self.funcs:
            func(*args, **kwargs)


class Callbacks:
    """
    Collection of CallbackSlot instances

    Allows a collection of callbacks to be more easily passed to
    methods that execute callbacks
    """
    def __init__(self, names):
        """
        :param list names: List of action names
        """
        for name in names:
            setattr(self, name, CallbackSlot(name))


def account_id_to_bytes(account_id):
    """
    Convert an account ID to bytes, ignoring the checksum and the prefix.
    Used for data structures that accept account IDs.

    :param str account_id: Account ID

    :return: Account ID as bytes
    :rtype: bytes
    """
    has_valid_prefix = (
        account_id.startswith("xrb_") or account_id.startswith("nano_")
    )

    if not has_valid_prefix:
        raise ValueError("Account ID has invalid prefix")

    # Get the public key portion of the account ID and decode it into
    # raw bytes
    return nbase32_to_bytes(account_id[-60:-8])


def account_ids_equal(account_id_a, account_id_b):
    """
    Compare two account IDs while discarding the account prefix

    :return: Whether the account IDs are equal
    :rtype: bool
    """
    return account_id_a[-60:-8] == account_id_b[-60:-8]


def normalize_account_id(account_id):
    """
    Normalize account ID to make it possible to use normal string
    comparisons between different account IDs

    :return: Normalized account ID
    :rtype: str
    """
    return account_id.replace("nano_", "xrb_")


class AccountIDDict(UserDict):
    """
    A dictionary that accepts NANO account IDs and uses the public key as
    the underlying key.

    The account prefix is ignored, meaning that the same public key represented
    with different account prefixes are considered identical.
    The account checksum (last 8 chars) is also ignored to improve performance.
    """
    def __getitem__(self, key):
        key = account_id_to_bytes(key)
        return self.data[key]

    def __setitem__(self, key, val):
        key = account_id_to_bytes(key)
        self.data[key] = val

    def __delitem__(self, key):
        key = account_id_to_bytes(key)
        del self.data[key]

    def __contains__(self, key):
        key = account_id_to_bytes(key)
        return key in self.data

    def items(self):
        return [
            (
                get_account_id(
                    public_key=binascii.hexlify(key).decode(),
                    prefix="xrb_"
                ),
                value
            ) for key, value in self.data.items()
        ]

    def values(self):
        return self.data.values()

    def keys(self):
        return [
            get_account_id(
                public_key=binascii.hexlify(key).decode(),
                prefix="xrb_"
            ) for key in self.data.keys()
        ]

    def to_dict(self):
        return {
            get_account_id(
                public_key=binascii.hexlify(key).decode(),
                prefix="xrb_"
            ): value
            for key, value in self.data.items()
        }

