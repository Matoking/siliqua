import pytest
import base64
import datetime

from siliqua.wallet.exceptions import InvalidEncryptionKey
from siliqua.wallet.secret import (
    Secret, SecretAlgorithm, validate_encryption_key
)


SECRET_KEY_A = b'erIm8Vj4YjcfD5MF3wrfGdZ8Yt2ttk3GcqrI1H3LWkA='
SECRET_KEY_B = b'5nb5Hkpw0R4QcVwXvl-jf05l1nceoHWwrVHQTR851uo='


def test_secret_encryption():
    """
    Encrypt a value and try decrypting it with the correct and wrong key
    """
    secret = Secret(val="ultra secret", secret_key=SECRET_KEY_A)

    assert secret.get(secret_key=SECRET_KEY_A) == "ultra secret"

    with pytest.raises(InvalidEncryptionKey):
        secret.get(secret_key=SECRET_KEY_B)


@pytest.mark.parametrize("val", [
    "ultra secret",
    b"aabbccdd",
    ["a", "c", "ff"],
    {"a": 5, "b": 10},
])
def test_secret_types(val):
    """
    Encrypt different types of values and decrypt them,
    ensuring they're identical afterwards
    """
    secret = Secret(val=val, secret_key=SECRET_KEY_A)

    assert secret.get(secret_key=SECRET_KEY_A) == val


def test_secret_set():
    secret = Secret(val="ultra secret", secret_key=SECRET_KEY_A)

    assert secret.get(secret_key=SECRET_KEY_A) == "ultra secret"

    secret.set(val="ultra secret 2", secret_key=SECRET_KEY_A)

    assert secret.get(secret_key=SECRET_KEY_A) == "ultra secret 2"

    # Different secret key is allowed as well
    secret.set(val="ultra secret 3", secret_key=SECRET_KEY_B)

    assert secret.get(secret_key=SECRET_KEY_B) == "ultra secret 3"


@pytest.mark.parametrize("val,enc_type", [
    ("ultra secret", "str"),
    (b"bytevalue", "bytes"),
    (["a", "c", "ff"], "list"),
    ({"a": 5, "b": 100}, "dict")
])
def test_secret_json(val, enc_type):
    secret = Secret(val=val, secret_key=SECRET_KEY_A)

    data = secret.json()

    assert data["_enc"] is True
    assert data["alg"] == "fernet"
    # Encrypted value is Base64 formatted
    base64.urlsafe_b64decode(data["val"])
    assert data["type"] == enc_type

    # Secrets can be reconstructed from JSON
    secret_b = Secret(enc_payload=secret.json())
    assert secret_b.get(secret_key=SECRET_KEY_A) == val


def test_secret_encrypt_invalid_type():
    with pytest.raises(TypeError) as exc:
        Secret(val=datetime.datetime.now(), secret_key=SECRET_KEY_A)

    assert "can't be encrypted" in str(exc.value)


def test_secret_decrypt_invalid_type():
    secret = Secret(val="test", secret_key=SECRET_KEY_A)
    payload = secret.json()
    payload["type"] = "fake type"

    secret = Secret(enc_payload=payload)

    with pytest.raises(TypeError) as exc:
        secret.get(secret_key=SECRET_KEY_A)

    assert "can't be decrypted" in str(exc.value)


def test_create_wrong_parameters():
    with pytest.raises(ValueError):
        # Mutually exclusive parameters
        Secret(enc_payload={"a": 5}, val="test")

    with pytest.raises(ValueError):
        Secret(enc_payload={"a": 5}, val="test", secret_key=SECRET_KEY_A)


def test_validate_encryption_key():
    assert validate_encryption_key(SECRET_KEY_A)

    # Invalid; contains invalid symbol
    wrong_key = b"erIm8Vj4YjcfD5MF3wrf#dZ8Yt2ttk3GcqrI1H3LWkA="

    with pytest.raises(InvalidEncryptionKey):
        validate_encryption_key(wrong_key)

    # Invalid; longer than 32 characters
    wrong_key = b'YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYQ=='

    with pytest.raises(InvalidEncryptionKey):
        validate_encryption_key(wrong_key)
