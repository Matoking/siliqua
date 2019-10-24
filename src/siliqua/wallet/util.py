import base64
import binascii
import time
from collections import UserDict
from datetime import datetime
from enum import Enum
from functools import wraps

from nanolib import (
    InvalidSeed, nbase32_to_bytes, bytes_to_nbase32, get_account_id
)

from .secret import Secret

__all__ = (
    "WalletSerializable", "Timestamp", "TimestampSource",
    "wallet_parameter", "get_current_timestamp",
    "HexDict"
)


def _serialize_value(val, settings, secret_key=None):
    prop_type = settings["type"]

    if val is None:
        return None
    elif isinstance(val, WalletSerializable):
        return val.to_dict(secret_key=secret_key)
    elif isinstance(val, Secret):
        return val.json()
    elif isinstance(val, Enum):
        return val.value
    elif prop_type is bytes:
        val = str(base64.b64encode(val), "utf-8")

    return val


def _deserialize_value(val, settings, secret_key=None):
    prop_type = settings["type"]

    if val is None:
        return None
    elif issubclass(prop_type, WalletSerializable):
        return prop_type.from_dict(d=val, secret_key=secret_key)
    elif isinstance(val, dict) and "_enc" in val.keys():
        return Secret(enc_payload=val)
    elif prop_type is bytes:
        val = base64.b64decode(val)

    return prop_type(val)


class WalletSerializable(object):
    """
    WalletSerializable allows deserialization/serialization of an object
    with encryption for selected fields
    """
    SERIALIZE_PROPS = {}

    def to_dict(self, secret_key=None):
        """
        """
        result = {}
        for name, settings in self.SERIALIZE_PROPS.items():
            is_required = settings.get("required", False)
            is_list = settings.get("list", False)
            serialize = settings.get("serialize", None)
            val = getattr(self, name)

            if serialize:
                # If a custom serialization function was provided, use it first
                val = serialize(val)

            if is_list:
                val = [
                    _serialize_value(
                        v, secret_key=secret_key,
                        settings=self.SERIALIZE_PROPS[name]
                    ) for v in val
                ]
            else:
                val = _serialize_value(
                    val, secret_key=secret_key,
                    settings=self.SERIALIZE_PROPS[name]
                )

            if val is not None:
                result[name] = val
            elif val is None and is_required:
                raise ValueError(
                    "Field {} is required but no value was provided!".format(
                        name
                    )
                )

        return result

    @classmethod
    def from_dict(cls, d=None, secret_key=None):
        """
        Deserialize the original object from a dict
        """
        kwargs = {}

        # Construct kwargs from a serialized dict
        for name, settings in cls.SERIALIZE_PROPS.items():
            is_list = settings.get("list", False)
            val = d.get(name, None)

            if is_list:
                if val is None:
                    val = []

                list_settings = cls.SERIALIZE_PROPS[name]

                kwargs[name] = [
                    _deserialize_value(
                        v, secret_key=secret_key,
                        settings=list_settings
                    ) for v in val
                ]
            else:
                kwargs[name] = _deserialize_value(
                    val, secret_key=secret_key,
                    settings=cls.SERIALIZE_PROPS[name])

        obj = cls(**kwargs)
        return obj

    def encrypt_secrets(self, secret_key):
        """
        Encrypt all properties recursively

        :param str secret_key: Secret key
        """
        for name, settings in self.SERIALIZE_PROPS.items():
            prop_type = settings["type"]

            is_list = settings.get("list", False)
            is_serializable = issubclass(prop_type, WalletSerializable)

            if is_list and is_serializable:
                for val in getattr(self, name):
                    val.encrypt_secrets(secret_key=secret_key)
            elif is_serializable:
                val = getattr(self, name)
                if val is not None:
                    val.encrypt_secrets(secret_key=secret_key)

            if not settings.get("secret", False):
                continue

            val = self.get_secret(name=name, secret_key=secret_key)

            if val is not None:
                self.set_secret(name=name, val=val, secret_key=secret_key)
            else:
                setattr(self, name, None)

    def decrypt_secrets(self, secret_key):
        """
        Decrypt and remove encryption recursively from all secret properties

        :param str secret_key: Secret key
        """
        for name, settings in self.SERIALIZE_PROPS.items():
            prop_type = settings["type"]

            is_list = settings.get("list", False)
            is_serializable = issubclass(prop_type, WalletSerializable)

            if is_list and is_serializable:
                for val in getattr(self, name):
                    val.decrypt_secrets(secret_key=secret_key)
            elif is_serializable:
                getattr(self, name).decrypt_secrets(
                    secret_key=secret_key
                )

            if not settings.get("secret", False):
                continue

            val = self.get_secret(name=name, secret_key=secret_key)
            setattr(self, name, val)

    def get_secret(self, name, secret_key=None):
        """
        Get the value of a property that is possibly encrypted
        """
        is_secret = self.SERIALIZE_PROPS[name].get("secret", False)
        val = getattr(self, name)

        if is_secret:
            if isinstance(val, Secret):
                if not secret_key:
                    raise ValueError(
                        "Secret key is required to decrypt this value")
                return val.get(secret_key=secret_key)

            return val

        if isinstance(val, Secret):
            raise ValueError(
                "A non-secret field {} has the type of Secret".format(name)
            )

        return val

    def set_secret(self, name, val, secret_key=None):
        """
        Set the value of a property that is possibly encrypted

        :param str name: Name of the field
        :param val: Value for the field
        :param str secret_key: Optional secret key for encrypting secret fields
        """
        old_val = getattr(self, name)
        is_secret = self.SERIALIZE_PROPS[name].get("secret", False)

        if is_secret:
            if isinstance(old_val, Secret) and secret_key:
                # Current value is encrypted so reuse the container
                old_val.set(val, secret_key=secret_key)
            elif not isinstance(old_val, Secret) and secret_key:
                # Create the encrypted container
                secret = Secret(val=val, secret_key=secret_key)
                setattr(self, name, secret)
            else:
                # No secret key provided, so don't actually encrypt this
                setattr(self, name, val)
        else:
            if not secret_key:
                setattr(self, name, val)
            else:
                raise ValueError(
                    "Tried to encrypt field '{}' that is not secret".format(
                        name
                    )
                )


def wallet_parameter(setter):
    """
    Decorator to set error handling for setters for serializable fields
    in WalletSerializable instances
    """
    @wraps(setter)
    def wrapper(self, new):
        # Assume the setter follows the naming convention 'set_<param>'
        name = setter.__name__[4:]

        # Check if field is required
        is_required = self.SERIALIZE_PROPS[name].get("required", False)

        if is_required and new is None:
            raise ValueError("Field '{name}' is required".format(name=name))

        # Check if field is non-secret and Secret was provided
        is_secret = self.SERIALIZE_PROPS[name].get("secret", False)

        if not is_secret and isinstance(new, Secret):
            raise ValueError(
                "Non-secret field '{name}' can't be set to a secret".format(
                    name=name
                )
            )

        # Check if field is a subclass of WalletSerializable
        # and whether a value of the correct type was provided
        field_type = self.SERIALIZE_PROPS[name]["type"]
        is_list = self.SERIALIZE_PROPS[name].get("list", False)

        is_type_serializable = issubclass(field_type, WalletSerializable)

        if is_type_serializable and not is_list:
            if new is not None and not isinstance(new, field_type):
                raise ValueError(
                    "Field '{}' value has to be an {} instance".format(
                        name, field_type.__name__)
                )

        try:
            if is_secret:
                # For a possibly secret value, also include an additional
                # "is this a Secret" boolean
                setter(self, new, isinstance(new, Secret))
            else:
                setter(self, new)
        except ValueError as e:
            # pytest will change the caught exception into ExceptionInfo
            # in tests. Calling str isn't enough to copy the exception
            # message before that,
            # so make a proper copy of the message using 'format'
            message = "{}".format(str(e))
            raise type(e)(
                "Encountered exception while changing property "
                "'{name}': {message}".format(
                    name=name,
                    message=message)
            ) from e

    return wrapper


class TimestampSource(Enum):
    """
    Timestamp source.

    Attaching a source to a timestamp means that the accuracy of the timestamp
    can be determined and possibly improved later (eg. by using a third party
    service)
    """
    # Timestamp reported by a node. Probably not accurate.
    NODE = "node"
    # Timestamp reported by a node when sending a broadcast notification.
    # Accurate.
    BROADCAST = "broadcast"
    # Timestamp generated by a wallet. Accurate.
    WALLET = "wallet"


class Timestamp(WalletSerializable):
    """
    Timestamp consisting of the actual date and the source of information.
    This allows timestamps to be updated to be more accurate later.
    """
    __slots__ = ("date", "source")

    SERIALIZE_PROPS = {
        "date": {
            "type": str, "required": True,
            "serialize": lambda x: str(int(x.timestamp()))
        },
        "source": {"type": TimestampSource, "required": True}
    }

    def __init__(self, date, source):
        self.date = datetime.fromtimestamp(int(date))
        self.source = TimestampSource(source)


def get_current_timestamp():
    """
    Get the current timestamp. The source is set as the wallet.
    """
    return Timestamp(
        date=time.time(),
        source=TimestampSource.WALLET)


class HexDict(UserDict):
    """
    A dictionary that accepts only hex-formatted key names.
    The key names are converted internally to bytes in order to save memory.
    """
    def __getitem__(self, key):
        key = binascii.unhexlify(key)
        return self.data[key]

    def __setitem__(self, key, val):
        key = binascii.unhexlify(key)
        self.data[key] = val

    def __delitem__(self, key):
        key = binascii.unhexlify(key)
        del self.data[key]

    def __contains__(self, key):
        key = binascii.unhexlify(key)
        return key in self.data

    def values(self):
        return self.data.values()

    def keys(self):
        return [
            str(binascii.hexlify(key), "utf-8").upper() for key
            in self.data.keys()
        ]


def _get_block_hashes_in_order(
        parent_block_hash, hash2parent, hash2successor):
    hash_list = [parent_block_hash]

    for block_hash in hash2parent[parent_block_hash]:
        hash_list += _get_block_hashes_in_order(
            block_hash, hash2parent, hash2successor
        )

    return hash_list


def sort_blocks_for_broadcast(blocks):
    """
    Sort and return a list of Blocks in correct order so they can be
    broadcast

    :param blocks: List of blocks
    :type blocks: List[siliqua.wallet.accounts.Block]

    :returns: Sorted list of blocks
    :rtype: list
    """
    block_map = HexDict()
    hash2successor = HexDict()
    hash2parent = HexDict()

    for block in blocks:
        block_hash = block.block_hash
        block_map[block_hash] = block
        hash2successor[block_hash] = []
        hash2parent[block_hash] = []

        if block.link_block:
            link_block_hash = block.link_block.block_hash
            hash2successor[link_block_hash] = []
            hash2parent[link_block_hash] = []

    for block in blocks:
        block_hash = block.block_hash
        previous = block.previous

        if previous and previous in block_map:
            hash2successor[previous].append(block_hash)
            hash2parent[block_hash].append(previous)

        if block.link_block:
            link_block_hash = block.link_block.block_hash

            if link_block_hash in block_map:
                hash2successor[link_block_hash].append(block_hash)
                hash2parent[block_hash].append(link_block_hash)

    frontiers = []

    # Get frontiers (blocks without any successors)
    for block_hash in hash2successor.keys():
        successors = hash2successor[block_hash]
        if not successors:
            frontiers.append(block_hash)

    block_hashes_in_order = []
    added_block_hashes = set()

    for frontier_hash in frontiers:
        block_hashes_to_frontier = _get_block_hashes_in_order(
            frontier_hash,
            hash2parent=hash2parent,
            hash2successor=hash2successor
        )
        block_hashes_to_frontier.reverse()

        for block_hash in block_hashes_to_frontier:
            if block_hash not in added_block_hashes \
                    and block_hash in block_map:
                block_hashes_in_order.append(block_hash)
                added_block_hashes.add(block_hash)

    return [block_map[block_hash] for block_hash in block_hashes_in_order]
