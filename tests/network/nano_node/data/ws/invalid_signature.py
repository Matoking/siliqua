from tests.network.nano_node.conftest import WebSocketReplay


DATA = [
    WebSocketReplay(
        "confirmation",
        {
            "accounts": ["xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"],
            "confirmation_type": "all"
        },
        {
            "topic": "confirmation",
            "time": "123456701000",
            "message": {
                "account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                "amount": "1000000000000000000000000000000",
                "hash": "E82CDC903E33AC80C2ACB6F3608FE9CFBDF610F11308F10CDDD8F6347F1CE058",
                "confirmation_type": "active_quorum",
                "block": {
                    "account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                    "balance": "1000000000000000000000000000000",
                    "link": "82CDDC385108D25E520B9CB2C7CB539CDF2FD5C9C3D7F4992AB6E18D0135B85F",
                    "link_as_account": "xrb_31pfuiw7448kdsb1q97krz7o998z7zcwmiyqykekofq3jn1mdg4z7nkczee6",
                    "previous": "0000000000000000000000000000000000000000000000000000000000000000",
                    "representative": "xrb_3dmtrrws3pocycmbqwawk6xs7446qxa36fcncush4s1pejk16ksbmakis78m",
                    "signature": "043351B1248406BFF71D4F06F8BC53E988BC56CAD82484136C6A90E21D8A35A5A3A9EC6A99B6AD7F71605A4602CD6672E705B1F22EFA6DFDAD8E1E9A48209908",
                    "subtype": "receive",
                    "type": "state",
                    "work": "538a6fef558ffd93"
                }
            }
        }
    )
]
