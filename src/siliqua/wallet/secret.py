import base64
import binascii
import hashlib
import time
from enum import Enum
from functools import lru_cache

import msgpack
from cryptography.fernet import Fernet, InvalidToken

from .exceptions import InvalidEncryptionKey, ValueEncrypted

__all__ = (
    "Secret", "SecretAlgorithm", "KeyType", "calculate_key_iteration_count",
    "get_secret_key", "encrypt", "decrypt", "validate_encryption_key"
)


class SecretAlgorithm(Enum):
    """
    Algorithm used to encrypt a secret.

    Only Fernet is supported for now.
    """
    DEFAULT = "fernet"
    FERNET = "fernet"


class KeyType(Enum):
    """
    The type of key used for encryption.

    A different key is derived from the same passphrase: one for encrypting
    secrets and another for encrypting the wallet itself
    """
    WALLET = "wallet"
    SECRET = "secrets"


def calculate_key_iteration_count(seconds=1):
    """
    Calculate the amount of iterations that can be performed in the given
    timespan.

    This amount can be used to determine the amount of iterations
    used for key derivation.

    :return: Key iteration count
    :rtype: int
    """
    TEST_ITERATION_COUNT = 1000000
    start = time.time()

    hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=b"2"*32,
        salt=b"1"*16,
        iterations=TEST_ITERATION_COUNT
    )

    end = time.time()

    iteration_count = int((TEST_ITERATION_COUNT / (end - start)) * seconds)

    # Ensure the minimum iteration count is always at least 100,000 in case
    # an extremely low count was calculated
    return max(100000, iteration_count)


def get_secret_key(passphrase=None, key_type=None, iterations=500000):
    """
    Derive a secret key using a passphrase, key type and iteration
    count

    :param str passphrase: Passphrase
    :param key_type: Key type used to derive the secret key
    :type key_type: KeyType
    :param int iterations: Key iteration count. Higher values increase
                           security at the cost of more work required
                           to derive the secret key.

    :return: URL safe Base64 encoded secret key
    :rtype: str
    """
    secret_type = str(KeyType(key_type))

    # Use the key type ('wallet' or 'secrets') as a salt
    salt = b"".join([
        b"NUWALLET",
        secret_type.encode("utf-8")
    ])

    secret_key = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=passphrase.encode("utf-8"),
        salt=salt,
        iterations=iterations)

    # Fernet encryption algorithm takes an URL-safe BASE64 encoded string,
    # so convert the secret key to it
    return base64.urlsafe_b64encode(secret_key)


def encrypt(val, secret_key, algorithm):
    """
    Encrypt a value with a secret key and algorithm

    :param val: Value to encrypt. Multiple types (dict, str, bytes, list)
                are supported.
    :param str secret_key: URL safe Base64 encoded secret key
    :param algorithm: Algorithm used for encryption
    :type algorithm: SecretAlgorithm

    :return: Encrypted payload as a dict
    :rtype: dict
    """
    payload = {
        "_enc": True,
        "alg": SecretAlgorithm(algorithm).value,
    }

    if isinstance(val, dict):
        payload["type"] = "dict"
        payload["val"] = msgpack.packb(val, use_bin_type=True)
    elif isinstance(val, str):
        payload["type"] = "str"
        payload["val"] = val.encode("utf-8")
    elif isinstance(val, bytes):
        payload["type"] = "bytes"
        payload["val"] = val
    elif isinstance(val, list):
        payload["type"] = "list"
        payload["val"] = msgpack.packb(val, use_bin_type=True)
    else:
        raise TypeError(
            "Value of type {} can't be encrypted.".format(type(val))
        )

    algo = SecretAlgorithm(algorithm)

    if algo == SecretAlgorithm.FERNET:
        fernet = Fernet(secret_key)
        payload["val"] = fernet.encrypt(payload["val"]).decode("utf-8")

    return payload


def decrypt(payload, secret_key):
    """
    Decrypt a payload with a secret key

    :param val: Dict to decrypt
    :param str secret_key: URL safe Base64 encoded secret key

    :return: Decrypted value
    """
    # For now, just check that the algorithm is valid
    algo = SecretAlgorithm(payload["alg"])

    if algo == SecretAlgorithm.FERNET:
        try:
            fernet = Fernet(secret_key)
            val = fernet.decrypt(payload["val"].encode("utf-8"))
        except InvalidToken:
            raise InvalidEncryptionKey()

    if payload["type"] in ["dict", "list"]:
        val = msgpack.unpackb(val, raw=False)
    elif payload["type"] == "str":
        val = val.decode("utf-8")
    elif payload["type"] == "bytes":
        pass
    else:
        raise TypeError(
            "Value of type {} can't be decrypted.".format(type(val))
        )

    return val


class Secret(object):
    """
    An object containing a value that is always stored in an encrypted
    format.

    The secret can be serialized into and deserialized from JSON.
    """
    __slots__ = ("enc_payload", "algorithm")

    def __init__(
            self, enc_payload=None, val=None, secret_key=None,
            algorithm=SecretAlgorithm.FERNET):
        """
        :param dict enc_payload: Encrypted payload that can be transmitted
                                 as-is to recreate the Secret object
        :param val: Value to encrypt
        :param str secret_key: Secret key used to encrypt the secret
        :param algorithm: Algorithm used for encrypting the secret
        :type algorithm: siliqua.wallet.secret.SecretAlgorithm
        """
        self.algorithm = SecretAlgorithm(algorithm)

        if enc_payload and val is None and not secret_key:
            self.enc_payload = enc_payload
        elif val and secret_key and not enc_payload:
            self.enc_payload = encrypt(
                val=val, secret_key=secret_key, algorithm=self.algorithm)
        else:
            raise ValueError("Only 'encrypted' or ('val', 'key') is accepted")

    def set(self, val, secret_key):
        """
        Replace the encrypted value

        :param val: Value to encrypt
        :param str secret_key: Secret key
        """
        self.enc_payload = encrypt(
            val=val, secret_key=secret_key, algorithm=self.algorithm)

    def get(self, secret_key):
        """
        Decrypt and return a copy of the decrypted value

        :param str secret_key: Secret key

        :return: Decrypted value
        """
        return decrypt(payload=self.enc_payload, secret_key=secret_key)

    def json(self):
        """
        Return a dict of the encrypted payload which can be later
        deserialized

        :return: Encrypted payload
        :rtype: dict
        """
        return self.enc_payload


def validate_encryption_key(key):
    """
    Check that the given encryption key is formatted in a valid way

    :raises InvalidEncryptionKey: If the encryption key is invalid
    """
    try:
        result = base64.urlsafe_b64decode(key)
        if len(result) != 32:
            raise InvalidEncryptionKey
    except (SyntaxError, binascii.Error):
        raise InvalidEncryptionKey

    return True
