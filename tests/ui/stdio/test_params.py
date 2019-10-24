import pytest
import os

from siliqua.ui.stdio.params import (
    RepeatParams, FilePathParam, BoolParam, BoolOption, IntParam,
    FloatParam, IntRangeOption, AccountParam, AmountParam
)


VALID_ACCOUNT_ID = \
    "xrb_3gcs3g68i5pip3pc63yuniysae7rfhonn391s5e61krieod68urtjsrmnukw"


class TestRepeatParams:
    def test_repeat_params(self):
        param = RepeatParams(
            ["destination", "amount"],
            [AccountParam, AmountParam]
        )
        assert param.parse("{},100".format(VALID_ACCOUNT_ID)) == {
            "destination": VALID_ACCOUNT_ID,
            "amount": 100
        }

    @pytest.mark.parametrize("val", [
        VALID_ACCOUNT_ID,
        "{},100,1".format(VALID_ACCOUNT_ID)
    ])
    def test_repeat_params_wrong_amount_of_params(self, val):
        param = RepeatParams(
            ["destination", "amount"],
            [AccountParam, AmountParam]
        )

        with pytest.raises(ValueError) as exc:
            param.parse(val)
        assert "got a wrong amount of parameters" in str(exc.value)

    def test_repeat_params_invalid_value(self):
        param = RepeatParams(
            ["destination", "amount"],
            [AccountParam, AmountParam]
        )

        with pytest.raises(ValueError) as exc:
            param.parse("invalid,1000")
        assert "invalid 'destination'" in str(exc.value)
        assert "is not a valid account ID" in str(exc.value)

        with pytest.raises(ValueError) as exc:
            param.parse("{},1000 nanothings".format(VALID_ACCOUNT_ID))
        assert "invalid 'amount'" in str(exc.value)
        assert "invalid NANO denomination" in str(exc.value)


class TestFilePathParam:
    def test_file_path_param(self, tmp_path):
        test_file = tmp_path / "test.file"

        with open(test_file, "w") as f:
            f.write("test")

        param = FilePathParam()
        assert os.path.exists(param.parse(str(test_file)))

    def test_file_path_param_exists(self, tmp_path):
        param = FilePathParam()

        with pytest.raises(ValueError) as exc:
            param.parse(str(tmp_path / "test.file"))
        assert "does not exist" in str(exc.value)

        param = FilePathParam(exists=False)

        # File does not need to exist
        assert param.parse(str(tmp_path / "test.file"))

    def test_file_path_param_dir(self, tmp_path):
        test_path = tmp_path / "test.file"

        os.mkdir(test_path)

        param = FilePathParam()

        # Directories are not accepted
        with pytest.raises(ValueError) as exc:
            param.parse(str(test_path))
        assert "is a directory" in str(exc.value)


class TestBoolParam:
    def test_bool_param(self):
        param = BoolParam()

        assert param.parse("on")
        assert param.parse("1")
        assert param.parse("yes")
        assert param.parse("true")

        assert not param.parse("off")
        assert not param.parse("0")
        assert not param.parse("no")
        assert not param.parse("false")

    def test_bool_param_invalid_value(self):
        param = BoolParam()

        with pytest.raises(ValueError) as exc:
            param.parse("invalid")

        assert "is not a valid truth value" in str(exc.value)


class TestBoolOption:
    def test_bool_option(self):
        option = BoolOption()

        assert option.parse(True)
        assert not option.parse(False)

    def test_bool_option_invalid(self):
        option = BoolOption()

        with pytest.raises(ValueError) as exc:
            assert option.parse(2)
        assert "is not a flag" in str(exc.value)

    def test_bool_option_default(self):
        option = BoolOption()

        with pytest.raises(ValueError) as exc:
            assert option.parse(None)
        assert "is required" in str(exc.value)

        option = BoolOption(default=True)
        assert option.parse(None)


class TestIntParam:
    def test_int_param(self):
        param = IntParam()

        assert param.parse(2) == 2
        assert param.parse("4") == 4

    @pytest.mark.parametrize("val", [
        1.2, "1.2", "invalid", None
    ])
    def test_int_param_invalid(self, val):
        param = IntParam()

        with pytest.raises(ValueError) as exc:
            param.parse(val)
        assert "is not an integer" in str(exc.value)


class TestFloatParam:
    def test_float_param(self):
        param = FloatParam()

        assert param.parse("1.2") == pytest.approx(1.2)
        assert param.parse("1") == pytest.approx(1.0)
        assert param.parse(1.25) == pytest.approx(1.25)

    @pytest.mark.parametrize("val", [
        "invalid", "1.2.3", "1,22"
    ])
    def test_float_param_invalid(self, val):
        param = FloatParam()

        with pytest.raises(ValueError) as exc:
            param.parse(val)
        assert "to float" in str(exc.value)


class TestIntRangeOption:
    def test_int_range(self):
        option = IntRangeOption(minimum=0, maximum=10)

        assert option.parse(10) == 10
        assert option.parse(5) == 5
        assert option.parse(0) == 0

    def test_int_range_noninteger(self):
        option = IntRangeOption(minimum=0, maximum=2)

        with pytest.raises(ValueError) as exc:
            option.parse(11.5)

        assert "is not an integer" in str(exc.value)

    def test_int_range_outside_range(self):
        option = IntRangeOption(minimum=0, maximum=10)

        for val in [-1, 11]:
            with pytest.raises(ValueError) as exc:
                option.parse(11)
            assert "is not in range" in str(exc.value)

    def test_int_range_default(self):
        option = IntRangeOption(minimum=0, maximum=10)

        with pytest.raises(ValueError) as exc:
            option.parse(None)

        assert "is required" in str(exc.value)

        option = IntRangeOption(minimum=0, maximum=10, default=5)

        assert option.parse(None) == 5

    def test_int_range_required_parameters(self):
        entries = [
            {"minimum": 0},
            {"maximum": 10},
            {}
        ]

        for kwargs in entries:
            with pytest.raises(ValueError) as exc:
                IntRangeOption(**kwargs)
            assert "requires both 'minimum' and 'maximum'" in str(exc.value)


class TestAccountParam:
    def test_account_param(self):
        VALID_A = \
            "xrb_3gcs3g68i5pip3pc63yuniysae7rfhonn391s5e61krieod68urtjsrmnukw"
        VALID_B = \
            "nano_3s6gej11qrxn8kzfmy9pw67x1befyiyqh6q4zkbo3r9szag5wa6fqke5bmcw"

        INVALID_A = "invalid"
        INVALID_B = \
            "nano_3s6gej11qrxn8kzfmy9pw67x1befyiyqh6q4zkbo3r9szag5wa6fqke5bmcv"
        param = AccountParam()

        assert param.parse(VALID_A) == VALID_A
        assert param.parse(VALID_B) == VALID_B

        for val in [INVALID_A, INVALID_B]:
            with pytest.raises(ValueError) as exc:
                param.parse(val)
            assert "is not a valid account ID" in str(exc.value)


class TestAmountParam:
    def test_amount_param(self):
        param = AmountParam()

        assert param.parse("1000") == 1000
        assert param.parse("1234") == 1234
        assert param.parse("1 Mnano") == 1000000000000000000000000000000
        assert param.parse("1.234567 Mnano") == 1234567000000000000000000000000

    def test_amount_param_invalid(self):
        param = AmountParam()

        with pytest.raises(ValueError) as exc:
            param.parse("100 raw 1")
        assert "value does not follow the format" in str(exc.value)

    def test_amount_param_invalid_amount(self):
        param = AmountParam()

        with pytest.raises(ValueError) as exc:
            param.parse("0.11.2 Mnano")
        assert "invalid amount" in str(exc.value)

    def test_amount_param_invalid_denomination(self):
        param = AmountParam()

        with pytest.raises(ValueError) as exc:
            # Denominations are case-sensitive
            param.parse("1000 mnano")
        assert "invalid NANO denomination" in str(exc.value)
