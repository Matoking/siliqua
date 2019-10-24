from tests.network.nano_node.conftest import HTTPReplay


DATA = [
    HTTPReplay(
        {"action": "version"},
        {
            "node_vendor": "Nano 18.0",
            "protocol_version": "16",
            "rpc_version": "1",
            "store_version": "13"
        }
    )
]
