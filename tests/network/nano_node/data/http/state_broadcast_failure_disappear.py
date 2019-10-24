from tests.network.nano_node.conftest import HTTPReplay


DATA = [
    HTTPReplay(
        {
            "action": "account_history",
            "account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
            "raw": True,
            "reverse": True,
            "count": 500
        },
        {
            "account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
            "history": [
                {
                    "account": "xrb_11p7y8een13ggixxt1ruxz6cchposphsfpx9nxgjtyhrz64apesgnad9ot1x",
                    "amount": "1000000000000000000000000000000",
                    "balance": "1000000000000000000000000000000",
                    "hash": "E82CDC903E33AC80C2ACB6F3608FE9CFBDF610F11308F10CDDD8F6347F1CE058",
                    "link": "82CDDC385108D25E520B9CB2C7CB539CDF2FD5C9C3D7F4992AB6E18D0135B85F",
                    "local_timestamp": "1556254492",
                    "previous": "0000000000000000000000000000000000000000000000000000000000000000",
                    "representative": "xrb_3dmtrrws3pocycmbqwawk6xs7446qxa36fcncush4s1pejk16ksbmakis78m",
                    "signature": "043351B1248406BFF71D4F06F8BC53E988BC56CAD82484136C6A90E21D8A35A5A3A9EC6A99B6AD7F71605A4602CD6672E705B1F22EFA6DFDAD8E1E9A48209907",
                    "subtype": "receive",
                    "type": "state",
                    "work": "538a6fef558ffd93"
                },
                {
                    "account": "xrb_1zoiejrbyey3x6tn5o6eqmmas1szy64x5wzqo9qppf8d6gn6mctm1ndnrgyy",
                    "amount": "1000000000000000000000000000000",
                    "balance": "0",
                    "hash": "96970559D7257F63ACB8383ED57CB510745DE744ABCEC4DC41590CE7E32179EA",
                    "link": "7EB064709F33C1E93541D48CBCE68C833FF105D1F3F7A9EF6B34CB23A849AB53",
                    "local_timestamp": "1556254492",
                    "previous": "E82CDC903E33AC80C2ACB6F3608FE9CFBDF610F11308F10CDDD8F6347F1CE058",
                    "representative": "xrb_3dmtrrws3pocycmbqwawk6xs7446qxa36fcncush4s1pejk16ksbmakis78m",
                    "signature": "505E3645F88CD37D4783A7242B8CF49BE9658E19576A17237B3F0BBF8A96249987596C9A65FA98BC904296BF0AB65EE3A9E5D48408A38ED30D9D474567083B0F",
                    "subtype": "send",
                    "type": "state",
                    "work": "07ff830e5b022fbd"
                }
            ]
        }
    ),
    HTTPReplay(
        {
            "action": "account_history",
            "account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
            "raw": True,
            "reverse": True,
            "head": "96970559D7257F63ACB8383ED57CB510745DE744ABCEC4DC41590CE7E32179EA",
            "count": 500,
        },
        {
            "account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
            "history": [
                {
                    "account": "xrb_1zoiejrbyey3x6tn5o6eqmmas1szy64x5wzqo9qppf8d6gn6mctm1ndnrgyy",
                    "amount": "1000000000000000000000000000000",
                    "balance": "0",
                    "hash": "96970559D7257F63ACB8383ED57CB510745DE744ABCEC4DC41590CE7E32179EA",
                    "link": "7EB064709F33C1E93541D48CBCE68C833FF105D1F3F7A9EF6B34CB23A849AB53",
                    "local_timestamp": "1556254492",
                    "previous": "E82CDC903E33AC80C2ACB6F3608FE9CFBDF610F11308F10CDDD8F6347F1CE058",
                    "representative": "xrb_3dmtrrws3pocycmbqwawk6xs7446qxa36fcncush4s1pejk16ksbmakis78m",
                    "signature": "505E3645F88CD37D4783A7242B8CF49BE9658E19576A17237B3F0BBF8A96249987596C9A65FA98BC904296BF0AB65EE3A9E5D48408A38ED30D9D474567083B0F",
                    "subtype": "send",
                    "type": "state",
                    "work": "07ff830e5b022fbd"
                }
            ]
        }
    ),
    HTTPReplay(
        {
            "action": "blocks_info",
            "hashes": [
                "E82CDC903E33AC80C2ACB6F3608FE9CFBDF610F11308F10CDDD8F6347F1CE058",
                "82CDDC385108D25E520B9CB2C7CB539CDF2FD5C9C3D7F4992AB6E18D0135B85F",
                "96970559D7257F63ACB8383ED57CB510745DE744ABCEC4DC41590CE7E32179EA"
            ]
        },
        {
            "blocks": {
                "82CDDC385108D25E520B9CB2C7CB539CDF2FD5C9C3D7F4992AB6E18D0135B85F": {
                    "amount": "1000000000000000000000000000000",
                    "balance": "0",
                    "block_account": "xrb_11p7y8een13ggixxt1ruxz6cchposphsfpx9nxgjtyhrz64apesgnad9ot1x",
                    "contents": "{\n    \"type\": \"state\",\n    \"account\": \"xrb_11p7y8een13ggixxt1ruxz6cchposphsfpx9nxgjtyhrz64apesgnad9ot1x\",\n    \"previous\": \"4AF3568F9ADDC65302FEDBBF2BAD60FD2175D7E671DDA980D55AEA5D343D8BEA\",\n    \"representative\": \"xrb_1awsn43we17c1oshdru4azeqjz9wii41dy8npubm4rg11so7dx3jtqgoeahy\",\n    \"balance\": \"0\",\n    \"link\": \"5114AB75C910A20726BFD3E8A3B9335B1738F36D87F4D246EE5A2B91AEB0D8CC\",\n    \"link_as_account\": \"xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc\",\n    \"signature\": \"AB85B448F40F482AC24006F7A3A00D25211B2017CE498CE40728435A41124E4E678675C8D994D4FC4596607499C23470A9188DE4A011253F54F8ABC00457CD0B\",\n    \"work\": \"9d86cf7e0bb936a9\"\n}\n",
                    "height": "2",
                    "confirmed": "true",
                    "local_timestamp": "1556254492"
                },
                "96970559D7257F63ACB8383ED57CB510745DE744ABCEC4DC41590CE7E32179EA": {
                    "amount": "1000000000000000000000000000000",
                    "balance": "0",
                    "block_account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                    "contents": "{\n    \"type\": \"state\",\n    \"account\": \"xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc\",\n    \"previous\": \"E82CDC903E33AC80C2ACB6F3608FE9CFBDF610F11308F10CDDD8F6347F1CE058\",\n    \"representative\": \"xrb_3dmtrrws3pocycmbqwawk6xs7446qxa36fcncush4s1pejk16ksbmakis78m\",\n    \"balance\": \"0\",\n    \"link\": \"7EB064709F33C1E93541D48CBCE68C833FF105D1F3F7A9EF6B34CB23A849AB53\",\n    \"link_as_account\": \"xrb_1zoiejrbyey3x6tn5o6eqmmas1szy64x5wzqo9qppf8d6gn6mctm1ndnrgyy\",\n    \"signature\": \"505E3645F88CD37D4783A7242B8CF49BE9658E19576A17237B3F0BBF8A96249987596C9A65FA98BC904296BF0AB65EE3A9E5D48408A38ED30D9D474567083B0F\",\n    \"work\": \"07ff830e5b022fbd\"\n}\n",
                    "height": "2",
                    "confirmed": "true",
                    "local_timestamp": "1556254492"
                },
                "E82CDC903E33AC80C2ACB6F3608FE9CFBDF610F11308F10CDDD8F6347F1CE058": {
                    "amount": "1000000000000000000000000000000",
                    "balance": "1000000000000000000000000000000",
                    "block_account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                    "contents": "{\n    \"type\": \"state\",\n    \"account\": \"xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc\",\n    \"previous\": \"0000000000000000000000000000000000000000000000000000000000000000\",\n    \"representative\": \"xrb_3dmtrrws3pocycmbqwawk6xs7446qxa36fcncush4s1pejk16ksbmakis78m\",\n    \"balance\": \"1000000000000000000000000000000\",\n    \"link\": \"82CDDC385108D25E520B9CB2C7CB539CDF2FD5C9C3D7F4992AB6E18D0135B85F\",\n    \"link_as_account\": \"xrb_31pfuiw7448kdsb1q97krz7o998z7zcwmiyqykekofq3jn1mdg4z7nkczee6\",\n    \"signature\": \"043351B1248406BFF71D4F06F8BC53E988BC56CAD82484136C6A90E21D8A35A5A3A9EC6A99B6AD7F71605A4602CD6672E705B1F22EFA6DFDAD8E1E9A48209907\",\n    \"work\": \"538a6fef558ffd93\"\n}\n",
                    "height": "1",
                    "confirmed": "true",
                    "local_timestamp": "1556254492"
                }
            }
        }
    ),
    HTTPReplay(
        {
            "action": "accounts_pending",
            "accounts": ["xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"],
            "threshold": "100000000000000000000000000",
            "source": True
        },
        {
            "blocks": {
                "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc": ""
            }
        }
    ),
    HTTPReplay(
        {
            "action": "process",
            "block": '{"account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc", "previous": "96970559D7257F63ACB8383ED57CB510745DE744ABCEC4DC41590CE7E32179EA", "representative": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc", "balance": "0", "link": "0000000000000000000000000000000000000000000000000000000000000000", "link_as_account": "xrb_1111111111111111111111111111111111111111111111111111hifc8npp", "signature": "BBC27F177C2C2DD574AE8EB8523A1A504B5790C65C95ACE744E3033A63BB158DDF95F9B7B88B902C8D743A64EA25785662CD454044E9C3000BC79C3BF7F1E809", "work": "561bab16393cb3c4", "type": "state"}'
        },
        {
            "hash": "62EE070DA06632FE1E54BA32FD25B00A5FD4E8CF09354A9B176CBF6BC33CDBDB"
        }
    ),
    HTTPReplay(
        {
            "action": "blocks_info",
            "hashes": [
                "62EE070DA06632FE1E54BA32FD25B00A5FD4E8CF09354A9B176CBF6BC33CDBDB"
            ]
        },
        {
            "error": "Block not found"
        }
    ),
]
