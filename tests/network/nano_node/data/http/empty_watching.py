from tests.network.nano_node.conftest import HTTPReplay


DATA = [
    HTTPReplay(
        {
            "action": "account_history",
            "account": "xrb_15n1wthxc5ndjnoufdfe8m4z5j973o6trzwbfys4cu4gtju5mh4xc918fout",
            "count": 500,
            "raw": True,
            "reverse": True
        },
        {
            "error": "Account not found"
        }
    )
]
