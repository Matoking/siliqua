from tests.network.nano_node.conftest import HTTPReplay


DATA = [
    HTTPReplay(
        {
            "action": "account_history",
            "account": "xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy",
            "raw": True,
            "reverse": True,
            "count": 500
        },
        {
            "account": "xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy",
            "history": [
                {
                    "account": "xrb_3jwrszth46rk1mu7rmb4rhm54us8yg1gw3ipodftqtikf5yqdyr7471nsg1k",
                    "amount": "1000000000000000000000000000000",
                    "hash": "A972FF5D6C00BFD18EDD70C74469204E640C81F0D30B62E0069A24209F1D82F9",
                    "local_timestamp": "1551151678",
                    "opened": "xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy",
                    "representative": "xrb_1anrzcuwe64rwxzcco8dkhpyxpi8kd7zsjc1oeimpc3ppca4mrjtwnqposrs",
                    "signature": "0286E1CEEE126CF7A79AFE54FFF8DD214CA6F01C50022F23BC9D39EC16562E5713047F5D76B85BABF90C8FEE561297F6EE02E0EFC60913EB22037988536E0D0D",
                    "source": "4737430974086B6356ED4C888FC5CC44A728C0DC60019CFCA776DA4E7C1849C8",
                    "type": "open",
                    "work": "6a17e12c42ece9cf"
                },
                {
                    "account": "xrb_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3",
                    "balance": "1000000000000000000000000000000",
                    "hash": "D9917582FB96AF84C02250F62A5340DD1318C76B33EC3C421D15F6EFED1DFD55",
                    "link": "65706F636820763120626C6F636B000000000000000000000000000000000000",
                    "local_timestamp": "1551151678",
                    "previous": "A972FF5D6C00BFD18EDD70C74469204E640C81F0D30B62E0069A24209F1D82F9",
                    "representative": "xrb_1anrzcuwe64rwxzcco8dkhpyxpi8kd7zsjc1oeimpc3ppca4mrjtwnqposrs",
                    "signature": "4C5D3D70621148324494E6BED751F168441919DBF722617EE913CB1418486E51052D711DCD9129C4D84144120F5903A3A840C61C4C5A4E31B57DFD5489E57E07",
                    "subtype": "epoch",
                    "type": "state",
                    "work": "0dad271fd745907c"
                }
            ]
        }
    ),
    HTTPReplay(
        {
            "action": "account_history",
            "account": "xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy",
            "raw": True,
            "reverse": True,
            "head": "D9917582FB96AF84C02250F62A5340DD1318C76B33EC3C421D15F6EFED1DFD55",
            "count": 500,
        },
        {
            "account": "xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy",
            "history": [
                {
                    "account": "xrb_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3",
                    "balance": "1000000000000000000000000000000",
                    "hash": "D9917582FB96AF84C02250F62A5340DD1318C76B33EC3C421D15F6EFED1DFD55",
                    "link": "65706F636820763120626C6F636B000000000000000000000000000000000000",
                    "local_timestamp": "1551151678",
                    "previous": "A972FF5D6C00BFD18EDD70C74469204E640C81F0D30B62E0069A24209F1D82F9",
                    "representative": "xrb_1anrzcuwe64rwxzcco8dkhpyxpi8kd7zsjc1oeimpc3ppca4mrjtwnqposrs",
                    "signature": "4C5D3D70621148324494E6BED751F168441919DBF722617EE913CB1418486E51052D711DCD9129C4D84144120F5903A3A840C61C4C5A4E31B57DFD5489E57E07",
                    "subtype": "epoch",
                    "type": "state",
                    "work": "0dad271fd745907c"
                }
            ]
        }
    ),
    HTTPReplay(
        {
            "action": "blocks_info",
            "hashes": [
                "A972FF5D6C00BFD18EDD70C74469204E640C81F0D30B62E0069A24209F1D82F9",
                "4737430974086B6356ED4C888FC5CC44A728C0DC60019CFCA776DA4E7C1849C8",
                "D9917582FB96AF84C02250F62A5340DD1318C76B33EC3C421D15F6EFED1DFD55"
            ]
        },
        {
            "blocks": {
                "4737430974086B6356ED4C888FC5CC44A728C0DC60019CFCA776DA4E7C1849C8": {
                    "amount": "1000000000000000000000000000000",
                    "balance": "1188502559713844364307617738000000000",
                    "block_account": "xrb_3jwrszth46rk1mu7rmb4rhm54us8yg1gw3ipodftqtikf5yqdyr7471nsg1k",
                    "contents": "{\n    \"type\": \"send\",\n    \"previous\": \"59F09FED5508B3D8D631819AE67C3BA6CD766C1E0E462AAD8E1626412205CDC1\",\n    \"destination\": \"xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy\",\n    \"balance\": \"00E4E5B34824F06B0A875B156AC96400\",\n    \"work\": \"ff78d1f2cf012776\",\n    \"signature\": \"988CDA336956C371E9A8C89A4A19D6FDEF0ABBFCAA05820FF61631A168D43E0BD755478586368CFE2924D15E82EC2FBFACCCCF9E337B76C2E92FA33A21CE710B\"\n}\n",
                    "height": "4497",
                    "confirmed": "true",
                    "local_timestamp": "1551151678"
                },
                "A972FF5D6C00BFD18EDD70C74469204E640C81F0D30B62E0069A24209F1D82F9": {
                    "amount": "1000000000000000000000000000000",
                    "balance": "1000000000000000000000000000000",
                    "block_account": "xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy",
                    "contents": "{\n    \"type\": \"open\",\n    \"source\": \"4737430974086B6356ED4C888FC5CC44A728C0DC60019CFCA776DA4E7C1849C8\",\n    \"representative\": \"xrb_1anrzcuwe64rwxzcco8dkhpyxpi8kd7zsjc1oeimpc3ppca4mrjtwnqposrs\",\n    \"account\": \"xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy\",\n    \"work\": \"6a17e12c42ece9cf\",\n    \"signature\": \"0286E1CEEE126CF7A79AFE54FFF8DD214CA6F01C50022F23BC9D39EC16562E5713047F5D76B85BABF90C8FEE561297F6EE02E0EFC60913EB22037988536E0D0D\"\n}\n",
                    "height": "1",
                    "confirmed": "true",
                    "local_timestamp": "1551151678"
                },
                "D9917582FB96AF84C02250F62A5340DD1318C76B33EC3C421D15F6EFED1DFD55": {
                    "amount": "0",
                    "balance": "1000000000000000000000000000000",
                    "block_account": "xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy",
                    "contents": "{\n    \"type\": \"state\",\n    \"account\": \"xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy\",\n    \"previous\": \"A972FF5D6C00BFD18EDD70C74469204E640C81F0D30B62E0069A24209F1D82F9\",\n    \"representative\": \"xrb_1anrzcuwe64rwxzcco8dkhpyxpi8kd7zsjc1oeimpc3ppca4mrjtwnqposrs\",\n    \"balance\": \"1000000000000000000000000000000\",\n    \"link\": \"65706F636820763120626C6F636B000000000000000000000000000000000000\",\n    \"link_as_account\": \"xrb_1sdifxjpia5p86i86u5hefoi1111111111111111111111111111g7jhnpfy\",\n    \"signature\": \"4C5D3D70621148324494E6BED751F168441919DBF722617EE913CB1418486E51052D711DCD9129C4D84144120F5903A3A840C61C4C5A4E31B57DFD5489E57E07\",\n    \"work\": \"0dad271fd745907c\"\n}\n",
                    "height": "2",
                    "confirmed": "true",
                    "local_timestamp": "1551151678"
                }
            }
        }
    ),
    HTTPReplay(
        {
            "action": "blocks_info",
            "hashes": [
                "C4BDB10778120F6748959EF7312C443BD0BFF4FE97F02A20B874694EB03DE0D0",
                "D96D72919D6EEAA9B82FE8046EBE70E20886E4D6C3BA218AD5340DD63AEE09C6"
            ]
        },
        {
            "blocks": {
                "C4BDB10778120F6748959EF7312C443BD0BFF4FE97F02A20B874694EB03DE0D0": {
                    "amount": "1000000000000000000000000000000",
                    "balance": "0",
                    "block_account": "xrb_3qbettndeemurhst593izae7j6x746bdzktmr16qfh9oa9uizxnuxkxgaiqd",
                    "contents": "{\n    \"type\": \"state\",\n    \"account\": \"xrb_3qbettndeemurhst593izae7j6x746bdzktmr16qfh9oa9uizxnuxkxgaiqd\",\n    \"previous\": \"2B64510C860CA6A5CA962CAD70DA1D14EB325B40CD11858D85F64DC595C825D6\",\n    \"representative\": \"xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy\",\n    \"balance\": \"0\",\n    \"link\": \"70A5422D4846931CEA02603DD5AFB2D0433E0806DECA5E832EB67F33B5777D35\",\n    \"link_as_account\": \"xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy\",\n    \"signature\": \"1CEACEC7E1CD95BC5977149FA8A6D858626A620E87AB2F003A1352B6CB4EB1AD0F4F200D47563AA6A8C29D6FD017AEBC6A7936DD075001CDFE36697E279E0F06\",\n    \"work\": \"26c1462244a50eca\"\n}\n",
                    "height": "4",
                    "confirmed": "true",
                    "local_timestamp": "1556238404"
                },
                "D96D72919D6EEAA9B82FE8046EBE70E20886E4D6C3BA218AD5340DD63AEE09C6": {
                    "amount": "1000000000000000000000000000",
                    "balance": "0",
                    "block_account": "xrb_36gijoeijuazu7d9urtxm1jqgejw43bi3tcfjx4i98q9mxuqhrsjs5dk1d9i",
                    "contents": "{\n    \"type\": \"state\",\n    \"account\": \"xrb_36gijoeijuazu7d9urtxm1jqgejw43bi3tcfjx4i98q9mxuqhrsjs5dk1d9i\",\n    \"previous\": \"0E603599652E42541297DEF21A7B4A7ADFB005D79F7310A3D52FBC040E158AE2\",\n    \"representative\": \"xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy\",\n    \"balance\": \"0\",\n    \"link\": \"70A5422D4846931CEA02603DD5AFB2D0433E0806DECA5E832EB67F33B5777D35\",\n    \"link_as_account\": \"xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy\",\n    \"signature\": \"0D0AB50DC183D5816D3F0F7ABD0F8E4754E3D0B7FF872B9BFC959B2C64310138C9929EA66C6D8AB8F5E42D8C5816D7145F981CB0E8713AA3949786A7A5CEFB0F\",\n    \"work\": \"f12c73ebb90da6d4\"\n}\n",
                    "height": "2",
                    "confirmed": "true",
                    "local_timestamp": "1551151665"
                }
            }
        }
    ),
    HTTPReplay(
        {
            "action": "accounts_pending",
            "accounts": ["xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy"],
            "threshold": "100000000000000000000000000",
            "source": True
        },
        {
            "blocks": {
                "xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy": {
                    "C4BDB10778120F6748959EF7312C443BD0BFF4FE97F02A20B874694EB03DE0D0": {
                        "amount": "1000000000000000000000000000000",
                        "source": "xrb_3qbettndeemurhst593izae7j6x746bdzktmr16qfh9oa9uizxnuxkxgaiqd"
                    },
                    "D96D72919D6EEAA9B82FE8046EBE70E20886E4D6C3BA218AD5340DD63AEE09C6": {
                        "amount": "1000000000000000000000000000",
                        "source": "xrb_36gijoeijuazu7d9urtxm1jqgejw43bi3tcfjx4i98q9mxuqhrsjs5dk1d9i"
                    }
                }
            }
        }
    )
]
