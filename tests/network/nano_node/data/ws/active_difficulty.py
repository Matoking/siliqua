from tests.network.nano_node.conftest import WebSocketReplay


DATA = [
    WebSocketReplay(
        "active_difficulty",
        {},
        {
            "topic": "active_difficulty",
            "time": "123456789000",
            "message": {
                "network_minimum": "0000000088664422",
                "network_current": "0000000088664422",
                "multiplier": "1.0"
            }
        }
    )
]
