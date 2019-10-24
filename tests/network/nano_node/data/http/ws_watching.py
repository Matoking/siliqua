from tests.network.nano_node.conftest import HTTPReplay


DATA = [
    HTTPReplay(
        {
            "action": "blocks_info",
            "hashes": [
                "82CDDC385108D25E520B9CB2C7CB539CDF2FD5C9C3D7F4992AB6E18D0135B85F",
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
            }
        }
    ),
    HTTPReplay(
        {
            "action": "blocks_info",
            "hashes": [
                "B92DC6098D6105CDBCC3A6DE45A31451578CF4322759A4A9DD5C54043090F3B1"
            ]
        },
        {
            "blocks": {
                "B92DC6098D6105CDBCC3A6DE45A31451578CF4322759A4A9DD5C54043090F3B1": {
                    "amount": "1000000000000000000000000000000",
                    "balance": "5198051945149496676881551988574957902",
                    "block_account": "nano_3jwrszth46rk1mu7rmb4rhm54us8yg1gw3ipodftqtikf5yqdyr7471nsg1k",
                    "contents": '{\n    "type": "state",\n    "account": "nano_3jwrszth46rk1mu7rmb4rhm54us8yg1gw3ipodftqtikf5yqdyr7471nsg1k",\n    "previous": "C6C2BC9C0F251287DDB3DF8EAC31CE52A62B0D6F42EE13FBF8F6F4247100E896",\n    "representative": "nano_3jwrszth46rk1mu7rmb4rhm54us8yg1gw3ipodftqtikf5yqdyr7471nsg1k",\n    "balance": "5198051945149496676881551988574957902",\n    "link": "E63383D55D5C556EF6D9F09AC12D377887339C6E39D9C7EDE62658B02047120E",\n    "link_as_account": "nano_3sjmihcotq4ofuufmw6tr6pmgy698gg8wggsrzpyebkrp1i6g6igfrzfhpkw",\n    "signature": "BE43C58EF7D94AD9C8F131DA192B553332FD870AFC6CCCA13FF00E7D19F556171A64F6EC875267974F43DB0052C986BE1685689FEA0497D7A9C8D08C07787F0F",\n    "work": "c64ce28af2162ad8"\n}',
                    "height": "353829",
                    "confirmed": "true",
                    "local_timestamp": "1554531903"
                }
            }
        }
    )
]
