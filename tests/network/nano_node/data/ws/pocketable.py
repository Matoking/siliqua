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
                "account": "nano_11p7y8een13ggixxt1ruxz6cchposphsfpx9nxgjtyhrz64apesgnad9ot1x",
                "amount": "1000000000000000000000000000000",
                "hash": "82CDDC385108D25E520B9CB2C7CB539CDF2FD5C9C3D7F4992AB6E18D0135B85F",
                "confirmation_type": "active_quorum",
                "block": {
                    "account": "nano_11p7y8een13ggixxt1ruxz6cchposphsfpx9nxgjtyhrz64apesgnad9ot1x",
                    "balance": "0",
                    "link": "5114AB75C910A20726BFD3E8A3B9335B1738F36D87F4D246EE5A2B91AEB0D8CC",
                    "link_as_account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                    "previous": "4AF3568F9ADDC65302FEDBBF2BAD60FD2175D7E671DDA980D55AEA5D343D8BEA",
                    "representative": "nano_1awsn43we17c1oshdru4azeqjz9wii41dy8npubm4rg11so7dx3jtqgoeahy",
                    "signature": "AB85B448F40F482AC24006F7A3A00D25211B2017CE498CE40728435A41124E4E678675C8D994D4FC4596607499C23470A9188DE4A011253F54F8ABC00457CD0B",
                    "subtype": "send",
                    "type": "state",
                    "work": "9d86cf7e0bb936a9"
                }
            }
        }
    )
]
