from tests.network.nano_node.conftest import HTTPReplay


DATA = [
    HTTPReplay(
        {"action": "version"},
        {
            "node_vendor": "Nano 19.0",
            "protocol_version": "17",
            "rpc_version": "1",
            "store_version": "14"
        }
    )
]
