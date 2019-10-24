import pytest
from siliqua.util import AccountIDDict, account_ids_equal, normalize_account_id


ACCOUNT_NANO_A = \
    "nano_3456cu49o6oco9uor9ytszhh9yozfbpbjffu94fpekmtet99pum8rmyr318x"
ACCOUNT_XRB_A = \
    "xrb_3456cu49o6oco9uor9ytszhh9yozfbpbjffu94fpekmtet99pum8rmyr318x"

ACCOUNT_NANO_B = \
    "nano_17mrjcdchuu3m58hdbmkjdi7gpf9zfnusn4cz45zunm5inrz9xq3pj4iyyfy"
ACCOUNT_XRB_B = \
    "xrb_17mrjcdchuu3m58hdbmkjdi7gpf9zfnusn4cz45zunm5inrz9xq3pj4iyyfy"


class TestAccountIDDict:
    def test_account_id_dict(self):
        d = AccountIDDict()
        d[ACCOUNT_NANO_A] = "test"

        assert ACCOUNT_XRB_A in d
        assert ACCOUNT_NANO_A in d

        assert d[ACCOUNT_NANO_A] == "test"
        assert d[ACCOUNT_XRB_A] == "test"

        assert d.keys() == [ACCOUNT_XRB_A]
        assert d.items() == [(ACCOUNT_XRB_A, "test")]

        assert ACCOUNT_XRB_B not in d

        del d[ACCOUNT_NANO_A]

        assert ACCOUNT_XRB_A not in d

    def test_account_id_dict_invalid_key(self):
        d = AccountIDDict()

        with pytest.raises(ValueError):
            d["test"] = "invalid"


def test_account_ids_equal():
    assert account_ids_equal(ACCOUNT_NANO_A, ACCOUNT_XRB_A)
    assert account_ids_equal(ACCOUNT_NANO_A, ACCOUNT_NANO_A)
    assert account_ids_equal(ACCOUNT_NANO_B, ACCOUNT_XRB_B)
    assert account_ids_equal(ACCOUNT_XRB_B, ACCOUNT_XRB_B)

    assert not account_ids_equal(ACCOUNT_NANO_A, ACCOUNT_NANO_B)
    assert not account_ids_equal(ACCOUNT_NANO_A, ACCOUNT_XRB_B)
    assert not account_ids_equal(ACCOUNT_NANO_B, ACCOUNT_XRB_A)
    assert not account_ids_equal(ACCOUNT_XRB_A, ACCOUNT_XRB_B)


def test_normalize_account_id():
    assert normalize_account_id(ACCOUNT_NANO_A) == ACCOUNT_XRB_A
    assert normalize_account_id(ACCOUNT_XRB_A) == ACCOUNT_XRB_A

    assert normalize_account_id(ACCOUNT_XRB_B) == ACCOUNT_XRB_B
    assert normalize_account_id(ACCOUNT_NANO_B) == ACCOUNT_XRB_B
