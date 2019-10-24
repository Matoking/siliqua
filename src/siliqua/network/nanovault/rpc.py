from nanolib.work import WORK_DIFFICULTY
from siliqua.network.exceptions import UnsupportedProtocolVersion
from siliqua.network.nano_node.rpc import \
    RPCProcessor as NanoNodeRPCNetworkProcessor


class RPCProcessor(NanoNodeRPCNetworkProcessor):
    """
    NanoVault servers work identically to NANO nodes, but miss a few
    endpoints we can ignore
    """
    async def check_node_version(self):
        protocol_version = self.connection_status.meta.get(
            "protocol_version", None
        )

        if protocol_version:
            return True

        GENESIS_HASH = "991CF190094C00F0B68E2E5F75F6BEE95A2E0BD93CEAA4A6734DB9F19B728948"

        # NanoVault servers don't expose the 'version' RPC method.
        # Instead, do a 'blocks_info' request and check that the
        # 'confirmed' field exists. If so, the node version is at least 19.
        response = await self.do_json_post(
            self.rpc_url,
            params={
                "action": "blocks_info",
                # Genesis block, which should be found by even
                # newly started nodes
                "hashes": [GENESIS_HASH]
            }
        )

        if "confirmed" not in response["blocks"][GENESIS_HASH]:
            raise UnsupportedProtocolVersion(
                required_version=self.REQUIRED_PROTOCOL_VERSION,
                current_version=16
            )

        # Since we don't know the exact version, go with the lowest
        # supported version to prevent making unknown requests
        self.connection_status.meta["protocol_version"] = 17

    async def update_active_difficulty(self):
        # NanoVault servers don't seem to report the difficulty in any way?
        # Again, assume things will work out
        self.work_difficulty = WORK_DIFFICULTY
