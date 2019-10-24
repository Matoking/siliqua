from tests.network.nano_node.conftest import HTTPReplay


DATA = [
    HTTPReplay(
        {
            "action": "blocks_info",
            "hashes": ["991CF190094C00F0B68E2E5F75F6BEE95A2E0BD93CEAA4A6734DB9F19B728948"]
        },
        {
            "blocks": {
                "991CF190094C00F0B68E2E5F75F6BEE95A2E0BD93CEAA4A6734DB9F19B728948": {
                    "amount": "340282366920938463463374607431768211455",
                    "balance": "340282366920938463463374607431768211455",
                    "block_account": "nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3",
                    "contents": "{\n    \"type\": \"open\",\n    \"source\": \"E89208DD038FBB269987689621D52292AE9C35941A7484756ECCED92A65093BA\",\n    \"representative\": \"nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3\",\n    \"account\": \"nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3\",\n    \"work\": \"62f05417dd3fb691\",\n    \"signature\": \"9F0C933C8ADE004D808EA1985FA746A7E95BA2A38F867640F53EC8F180BDFE9E2C1268DEAD7C2664F356E37ABA362BC58E46DBA03E523A7B5A19E4B6EB12BB02\"\n}\n",
                    "height": "1",
                    "local_timestamp": "0"
                }
            }
        }
    )
]
