import binascii
import random

import pytest
from siliqua.wallet.accounts import LinkBlock
from siliqua.wallet.exceptions import InvalidEncryptionKey
from siliqua.wallet.util import (HexDict, Secret, WalletSerializable,
                                 sort_blocks_for_broadcast, wallet_parameter)

SECRET_KEY_A = b'erIm8Vj4YjcfD5MF3wrfGdZ8Yt2ttk3GcqrI1H3LWkA='
SECRET_KEY_B = b'5nb5Hkpw0R4QcVwXvl-jf05l1nceoHWwrVHQTR851uo='



class SubObject(WalletSerializable):
    SERIALIZE_PROPS = {
        "name": {"type": str}
    }

    def __init__(self, **kwargs):
        self.name = kwargs.get("name", None)


class SimpleObject(WalletSerializable):
    SERIALIZE_PROPS = {
        "string": {"type": str},
        "secret_string": {"type": str, "secret": True},
        "sub_object": {"type": SubObject}
    }

    def __init__(self, **kwargs):
        self.string = kwargs.get("string", None)
        self.secret_string = kwargs.get("secret_string", None)
        self.sub_object = kwargs.get("sub_object", SubObject())

    @wallet_parameter
    def set_string(self, string):
        self._string = string

    @wallet_parameter
    def set_secret_string(self, secret_string, is_secret):
        self._secret_string = secret_string

    @wallet_parameter
    def set_sub_object(self, sub_object):
        self._sub_object = sub_object

    string = property(lambda x: x._string, set_string)
    secret_string = property(lambda x: x._secret_string, set_secret_string)
    sub_object = property(lambda x: x._sub_object, set_sub_object)


def test_serialize_with_default_params():
    # WalletSerializable with default None values should serialize into
    # an empty dict
    test_obj = SimpleObject(string=None, secret_string=None)

    assert test_obj.to_dict() == {"sub_object": {}}

    test_obj_b = SimpleObject.from_dict({})

    assert test_obj_b.string is None
    assert test_obj_b.secret_string is None


def test_serialize_with_set_params():
    test_obj = SimpleObject(
        string="hello there", sub_object=SubObject(name="sub string")
    )

    assert test_obj.to_dict() == {
        "string": "hello there", "sub_object": {"name": "sub string"}
    }

    test_obj_b = SimpleObject.from_dict(test_obj.to_dict())
    assert test_obj.string == test_obj_b.string


def test_serialize_with_secret_string():
    test_obj = SimpleObject(
        string="public string", secret_string="deep dark secrets")

    assert test_obj.to_dict() == {
        "secret_string": "deep dark secrets",
        "string": "public string",
        "sub_object": {}
    }

    # Encrypt the test object to hide 'secret_string'
    test_obj.encrypt_secrets(secret_key=SECRET_KEY_A)

    assert isinstance(test_obj.secret_string, Secret)
    enc_d = test_obj.to_dict()
    assert enc_d["secret_string"]["_enc"] is True
    assert enc_d["secret_string"]["val"]
    assert enc_d["string"] == "public string"

    # Now decrypt to reveal 'secret_string' again
    test_obj.decrypt_secrets(secret_key=SECRET_KEY_A)

    assert test_obj.secret_string == "deep dark secrets"
    assert test_obj.to_dict() == {
        "string": "public string",
        "secret_string": "deep dark secrets",
        "sub_object": {}
    }


def test_serializable_get_secret():
    test_obj = SimpleObject(
        string="public string", secret_string="deep dark secrets")

    # If the value isn't encrypted, just return as is
    test_obj.get_secret("secret_string") == "deep dark secrets"

    test_obj.encrypt_secrets(secret_key=SECRET_KEY_A)

    assert test_obj.get_secret("secret_string", secret_key=SECRET_KEY_A) == \
        "deep dark secrets"

    # Secret key is required
    with pytest.raises(ValueError) as exc:
        test_obj.get_secret("secret_string")

    assert "Secret key is required" in str(exc.value)

    # Invalid secret key
    with pytest.raises(InvalidEncryptionKey):
        test_obj.get_secret("secret_string", secret_key=SECRET_KEY_B)


def test_serializable_set_secret():
    test_obj = SimpleObject(
        string="public string", secret_string="deep dark secrets")

    # Without secret key no encryption is done
    test_obj.set_secret("secret_string", "deeper dark secrets")
    assert test_obj.secret_string == "deeper dark secrets"

    # With secret key, the field is encrypted if it isn't already
    # encrypted
    test_obj.set_secret(
        "secret_string", "deepest dark secrets", secret_key=SECRET_KEY_A)
    assert isinstance(test_obj.secret_string, Secret)
    assert test_obj.get_secret("secret_string", secret_key=SECRET_KEY_A) == \
        "deepest dark secrets"

    # Any secret key can be used to encrypt the field
    test_obj.set_secret(
        "secret_string", "the deepest dark secrets", secret_key=SECRET_KEY_B)
    assert test_obj.get_secret("secret_string", secret_key=SECRET_KEY_B) == \
        "the deepest dark secrets"

    # Non-secret field can't be encrypted
    with pytest.raises(ValueError) as exc:
        test_obj.set_secret("string", "whatever", secret_key=SECRET_KEY_A)

    assert "Tried to encrypt field 'string'" in str(exc.value)


def test_serializable_wallet_parameter():
    test_obj = SimpleObject(string="public string")

    test_obj.string = "test string"
    assert test_obj.string == "test string"

    # Non-secret fields can't be set to a secret value
    with pytest.raises(ValueError) as exc:
        test_obj.string = Secret(val="test string 2", secret_key=SECRET_KEY_A)

    assert "Non-secret field 'string' can't" in str(exc.value)

    # If field's type is a sub class of WalletSerializable, wallet_parameter
    # enforces the type automatically
    test_obj.sub_object = SubObject(name="test")
    assert test_obj.sub_object.name == "test"

    with pytest.raises(ValueError) as exc:
        test_obj.sub_object = "wrong type"

    assert "Field 'sub_object' value has to be an SubObject instance" in str(exc.value)


class ListItem(WalletSerializable):
    SERIALIZE_PROPS = {
        "name": {"type": str},
        "count": {"type": int},
        "secret": {"type": str, "secret": True}
    }

    def __init__(self, **kwargs):
        self.name = kwargs.get("name", None)
        self.count = kwargs.get("count", None)
        self.secret = kwargs.get("secret", None)


class ComplexObject(WalletSerializable):
    SERIALIZE_PROPS = {
        "string": {"type": str},
        "items": {"list": True, "type": ListItem},
        "names": {"type": dict},
        "byte": {"type": bytes},
    }

    def __init__(self, **kwargs):
        self.string = kwargs.get("string", None)
        self.items = kwargs.get("items", [])
        self.names = kwargs.get("names", {})
        self.byte = kwargs.get("byte", None)


def test_complex_serialize():
    DICT_DATA = {
        "items": [
            {"count": 5, "name": "One", "secret": "op"},
            {"count": 100, "name": "Two"}
        ],
        "names": {"First": "Jimmy", "Second": "Bimmy"},
        "string": "Test string",
        "byte": "aGVsbG8gdGhlcmU=",  # Bytes are serialized using Base64
    }
    # Create a more complex object and serialize it
    test_obj = ComplexObject(
        string="Test string",
        items=[
            ListItem(name="One", count=5, secret="op"),
            ListItem(name="Two", count=100)
        ],
        names={"First": "Jimmy", "Second": "Bimmy"},
        byte=b"hello there"
    )

    d = test_obj.to_dict()
    assert d == DICT_DATA

    # Encrypt the object and ensure it is done recursively
    # by checking an inner object
    test_obj.encrypt_secrets(secret_key=SECRET_KEY_A)
    assert isinstance(test_obj.items[0].secret, Secret)

    d = test_obj.to_dict()

    assert d["items"][0]["secret"].get("_enc", False)

    # Deserialize from the encrypted dict
    test_obj_b = ComplexObject.from_dict(d)
    test_obj_b.decrypt_secrets(secret_key=SECRET_KEY_A)

    assert test_obj_b.to_dict() == DICT_DATA


class TestHexDict:
    def test_hex_dict(self):
        d = HexDict()
        d["aaff55"] = "test"
        d["ffaa99"] = "another test"

        assert d["aaff55"] == "test"

        del d["aaff55"]

        assert d.keys() == ["FFAA99"]

        assert "ffaa99" in d
        assert "FFAA99" in d
        assert "FFFFFF" not in d

    def test_hex_dict_invalid_keys(self):
        d = HexDict()
        # Non-hex values not allowed
        with pytest.raises(binascii.Error):
            d["test"] = "blah"


def test_sort_blocks_for_broadcast(wallet_factory):
    wallet = wallet_factory(balance=10000)
    account_ids = [
        wallet.accounts[0].account_id,
        wallet.accounts[10].account_id,
        wallet.accounts[5].account_id,
        wallet.accounts[8].account_id
    ]

    blocks = []

    destination = account_ids[1]
    for _ in range(0, 5):
        for j in range(0, 4):
            source = account_ids[j]
            try:
                destination = account_ids[j+1]
            except IndexError:
                destination = account_ids[0]

            send_block = wallet.send(
                source=source, destination=destination, amount=1000
            )
            link_block = LinkBlock(
                amount=1000, block=send_block.block
            )
            receive_block = wallet.account_map[destination].receive_block(
                link_block
            )

            blocks += [send_block, receive_block]

    block_hashes = [block.block_hash for block in blocks]

    # Shuffle the blocks and sort them, ensuring the order remains the same
    random.shuffle(blocks)
    blocks = sort_blocks_for_broadcast(blocks)

    assert block_hashes == [block.block_hash for block in blocks]
