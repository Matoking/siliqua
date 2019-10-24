from tests.network.nano_node.conftest import HTTPReplay


DATA = [
    HTTPReplay(
        {
            "action": "active_difficulty"
        },
        {
            "network_minimum": "ffffffc000000000",
            "network_current": "ffffffc000000000",
            "multiplier": "1.0"
        }
    )
]
