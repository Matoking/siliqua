from tests.network.nanovault.conftest import WebSocketReplay


DATA = [
    WebSocketReplay(
        ["xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"],
        {
            "event": "newTransaction",
            "data": {
                "account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                "amount": "1000000000000000000000000000000",
                "is_send": "false",
                "subtype": "receive",
                "hash": "E82CDC903E33AC80C2ACB6F3608FE9CFBDF610F11308F10CDDD8F6347F1CE058",
                "block": {
                    "account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                    "balance": "1000000000000000000000000000000",
                    "link": "82CDDC385108D25E520B9CB2C7CB539CDF2FD5C9C3D7F4992AB6E18D0135B85F",
                    "link_as_account": "xrb_31pfuiw7448kdsb1q97krz7o998z7zcwmiyqykekofq3jn1mdg4z7nkczee6",
                    "previous": "0000000000000000000000000000000000000000000000000000000000000000",
                    "representative": "xrb_3dmtrrws3pocycmbqwawk6xs7446qxa36fcncush4s1pejk16ksbmakis78m",
                    "signature": "043351B1248406BFF71D4F06F8BC53E988BC56CAD82484136C6A90E21D8A35A5A3A9EC6A99B6AD7F71605A4602CD6672E705B1F22EFA6DFDAD8E1E9A48209907",
                    "type": "state",
                    "work": "538a6fef558ffd93"
                }
            }
        }
    ),
    WebSocketReplay(
        [
            "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
            "xrb_3sjmihcotq4ofuufmw6tr6pmgy698gg8wggsrzpyebkrp1i6g6igfrzfhpkw"
        ],
        {
            "event": "newTransaction",
            "data": {
                "account": "xrb_3sjmihcotq4ofuufmw6tr6pmgy698gg8wggsrzpyebkrp1i6g6igfrzfhpkw",
                "amount": "1000000000000000000000000000000",
                "is_send": "false",
                "subtype": "receive",
                "hash": "19A49CD5E8AA7C84E0C656ADA7FDF16FEE340A1D815825939F972F1BBB3358FF",
                "block": {
                    "account": "xrb_3sjmihcotq4ofuufmw6tr6pmgy698gg8wggsrzpyebkrp1i6g6igfrzfhpkw",
                    "type": "state",
                    "representative": "xrb_3sjmihcotq4ofuufmw6tr6pmgy698gg8wggsrzpyebkrp1i6g6igfrzfhpkw",
                    "previous": "0000000000000000000000000000000000000000000000000000000000000000",
                    "work": "635e5e82d44339b3",
                    "signature": "5BDD313A280C6B6358CE4A405FB937E57E965689A95508478FF08CAE0F3DA0EE10D6CA006C37FB251C0C9795DBB39AA221650A74F53D1B1BBE55089CF0BEFE0E",
                    "link": "B92DC6098D6105CDBCC3A6DE45A31451578CF4322759A4A9DD5C54043090F3B1",
                    "link_as_account": "xrb_3gbfrr6rtra7spye9bpyapjjancqjmt56btsnknxtq4n1irb3wxjb7c3dudo",
                    "balance": "1000000000000000000000000000000"
                }
            }
        }
    ),
    WebSocketReplay(
        [
            "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
            "xrb_3sjmihcotq4ofuufmw6tr6pmgy698gg8wggsrzpyebkrp1i6g6igfrzfhpkw"
        ],
        {
            "event": "newTransaction",
            "data": {
                "account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                "amount": "1000000000000000000000000000000",
                "is_send": "true",
                "subtype": "send",
                "hash": "96970559D7257F63ACB8383ED57CB510745DE744ABCEC4DC41590CE7E32179EA",
                "block": {
                    "account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                    "balance": "0",
                    "link": "7EB064709F33C1E93541D48CBCE68C833FF105D1F3F7A9EF6B34CB23A849AB53",
                    "link_as_account": "xrb_1zoiejrbyey3x6tn5o6eqmmas1szy64x5wzqo9qppf8d6gn6mctm1ndnrgyy",
                    "previous": "E82CDC903E33AC80C2ACB6F3608FE9CFBDF610F11308F10CDDD8F6347F1CE058",
                    "representative": "xrb_3dmtrrws3pocycmbqwawk6xs7446qxa36fcncush4s1pejk16ksbmakis78m",
                    "signature": "505E3645F88CD37D4783A7242B8CF49BE9658E19576A17237B3F0BBF8A96249987596C9A65FA98BC904296BF0AB65EE3A9E5D48408A38ED30D9D474567083B0F",
                    "type": "state",
                    "work": "07ff830e5b022fbd"
                }
            }
        }
    )
]
