import time

from nanolib.exceptions import InvalidSignature
from siliqua.network import AccountSyncStatus
from siliqua.network.exceptions import UnsupportedProtocolVersion
from siliqua.util import RawBlock
from siliqua.wallet import Block
from siliqua.wallet.accounts import TimestampSource
from tests.util import wait_for


class TestJSONRPCProcessor:
    def test_sync_watching(
            self, mock_nanovault_node, nanovault_network_plugin):
        # This test is almost identical to the same test in
        # test_nano_node.py.
        mock_nanovault_node.add_replay_datasets([
            "legacy_watching", "active_difficulty", "nanovault_version"
        ]).start()
        network_plugin = nanovault_network_plugin

        network_plugin.account_sync_statuses["xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf"] \
            = AccountSyncStatus(
                account_id="xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf"
            )

        # Wait until the account has finished syncing
        sync_status = network_plugin.account_sync_statuses[
            "xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf"]
        wait_for(lambda: sync_status.sync_complete, timeout=2)

        assert network_plugin.processed_block_queue.qsize() == 5

        block_results = [
            network_plugin.processed_block_queue.get_nowait() for _ in range(0, 5)
        ]
        blocks = [
            result.block for result in block_results
        ]
        block_a, block_b, block_c, block_d, block_e = blocks

        # Ensure blocks are in the correct order and have the corresponding
        # link blocks
        assert block_a.block_hash == "088EE46429CA936F76C4EAA20B97F6D33E5D872971433EE0C1311BCB98764456"
        assert block_b.block_hash == "13552AC3928E93B5C6C215F61879358E248D4A5246B8B3D1EEC5A566EDCEE077"
        assert block_c.block_hash == "D6E1921FA6B341EE1D3EC36F31AF3B7B73EE17F82CA80B76002EDBA30B82B447"
        assert block_d.block_hash == "94EA9E9DC69B7634560B56B21EF47A04C7ADC7CF80BB911267A9D7C824EEB83C"
        assert block_e.block_hash == "BCDEF4D74B0D93231B1C6CFDBA21DC189CFF4D69BE8FAC07278968FE0BC09FFC"

        assert block_a.source == "E749404912F8C239E2F413B7C604E5732F428C9DEC4BA649AEBB54AC964EBFA4"
        assert block_a.source == block_a.link_block.block_hash

        assert not block_b.source
        assert not block_b.link_block

        assert block_c.source == "786E621F133DDC9DA97808CEF006499845D3ED660C0630BCC7B21FE313F869F8"
        assert block_c.source == block_c.link_block.block_hash

        assert block_d.source == "548E61BAF6CF07E418324D2D08DAB0FC710681837E94C30242E14C97169AB529"
        assert block_d.source == block_d.link_block.block_hash

        assert not block_e.source

        # Ensure the other queues are empty
        assert network_plugin.pocketable_block_queue.empty()
        assert network_plugin.broadcast_block_queue.empty()

        sync_status = network_plugin.account_sync_statuses[
            "xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf"]

        assert sync_status.sync_complete
        assert sync_status.network_head == block_e.block_hash
        assert not sync_status.wallet_head
        assert not sync_status.ready_to_pocket

    def test_broadcast_block_success(
            self, mock_nanovault_node, nanovault_network_plugin):
        # Sync account with two blocks and broadcast the third block
        # while simulating successful transmission
        mock_nanovault_node.add_replay_datasets(
            ["state_broadcast_success", "nanovault_version"]
        ).reload()
        network_plugin = nanovault_network_plugin

        network_plugin.account_sync_statuses["xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"] \
            = AccountSyncStatus(
                account_id="xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"
            )

        # Wait until the account has finished syncing
        sync_status = network_plugin.account_sync_statuses[
            "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"]
        wait_for(lambda: sync_status.sync_complete, timeout=2)

        assert network_plugin.processed_block_queue.qsize() == 2

        # Broadcast the third block
        block = Block(
            block=RawBlock.from_dict({
                "account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                "balance": "0",
                "link": "0000000000000000000000000000000000000000000000000000000000000000",
                "previous": "96970559D7257F63ACB8383ED57CB510745DE744ABCEC4DC41590CE7E32179EA",
                "representative": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                "signature": "BBC27F177C2C2DD574AE8EB8523A1A504B5790C65C95ACE744E3033A63BB158DDF95F9B7B88B902C8D743A64EA25785662CD454044E9C3000BC79C3BF7F1E809",
                "type": "state",
                "work": "561bab16393cb3c4"
            })
        )

        network_plugin.broadcast_block_queue.put(block)

        wait_for(network_plugin.broadcast_block_queue.empty, timeout=2)
        wait_for(lambda: sync_status.sync_complete, timeout=2)

        assert network_plugin.processed_block_queue.qsize() == 3

        _, _, block = [
            network_plugin.processed_block_queue.get_nowait() for _ in range(0, 3)
        ]

        assert block.confirmed
        assert not block.rejected

        assert block.block_hash == \
            "62EE070DA06632FE1E54BA32FD25B00A5FD4E8CF09354A9B176CBF6BC33CDBDB"

    def test_old_version(
            self, mock_nanovault_node, nanovault_network_plugin):
        # This test is almost identical to the same test in
        # test_nano_node.py.
        mock_nanovault_node.add_replay_datasets([
            "nanovault_old_version"
        ]).start()
        network_plugin = nanovault_network_plugin

        wait_for(lambda: network_plugin.connection_status.aborted, timeout=1)

        assert isinstance(
            network_plugin.connection_status.error,
            UnsupportedProtocolVersion
        )


class TestWebSocketProcessor:
    def test_confirmed_blocks(
            self, mock_nanovault_node, mock_nanovault_ws_node,
            nanovault_ws_node_network_plugin):
        mock_nanovault_node.add_replay_datasets([
            "nanovault_version", "ws_watching"
        ]).start()
        mock_nanovault_ws_node.add_replay_datasets(["watching"]).start()
        network_plugin = nanovault_ws_node_network_plugin

        # Start watching a single account
        network_plugin.account_sync_statuses["xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"] \
            = AccountSyncStatus(
                account_id="xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"
            )
        sync_status_a = network_plugin.account_sync_statuses["xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"]

        wait_for(
            lambda: sync_status_a.network_head == "E82CDC903E33AC80C2ACB6F3608FE9CFBDF610F11308F10CDDD8F6347F1CE058",
            timeout=1
        )

        # Add another account to watch. Network server should update
        # the subscription options accordingly.
        network_plugin.account_sync_statuses["xrb_3sjmihcotq4ofuufmw6tr6pmgy698gg8wggsrzpyebkrp1i6g6igfrzfhpkw"] \
            = AccountSyncStatus(
                account_id="xrb_3sjmihcotq4ofuufmw6tr6pmgy698gg8wggsrzpyebkrp1i6g6igfrzfhpkw"
            )
        sync_status_b = network_plugin.account_sync_statuses["xrb_3sjmihcotq4ofuufmw6tr6pmgy698gg8wggsrzpyebkrp1i6g6igfrzfhpkw"]

        wait_for(
            lambda: sync_status_a.network_head == "96970559D7257F63ACB8383ED57CB510745DE744ABCEC4DC41590CE7E32179EA",
            timeout=1
        )
        wait_for(
            lambda: sync_status_b.network_head == "19A49CD5E8AA7C84E0C656ADA7FDF16FEE340A1D815825939F972F1BBB3358FF",
            timeout=1
        )

        # Check that the blocks have correct timestamps
        block_results = [
            network_plugin.processed_block_queue.get_nowait()
            for _ in range(0, 3)
        ]
        blocks = [result.block for result in block_results]
        block_a, block_b, block_c = blocks

        assert block_a.block_hash == "E82CDC903E33AC80C2ACB6F3608FE9CFBDF610F11308F10CDDD8F6347F1CE058"
        assert block_b.block_hash == "19A49CD5E8AA7C84E0C656ADA7FDF16FEE340A1D815825939F972F1BBB3358FF"
        assert block_c.block_hash == "96970559D7257F63ACB8383ED57CB510745DE744ABCEC4DC41590CE7E32179EA"

        assert block_a.timestamp.source == TimestampSource.BROADCAST
        assert int(block_a.timestamp.date.timestamp()) > time.time() - 10
        assert block_a.link_block.block_hash == "82CDDC385108D25E520B9CB2C7CB539CDF2FD5C9C3D7F4992AB6E18D0135B85F"

        assert block_b.timestamp.source == TimestampSource.BROADCAST
        assert int(block_b.timestamp.date.timestamp()) > time.time() - 10
        assert block_b.link_block.block_hash == "B92DC6098D6105CDBCC3A6DE45A31451578CF4322759A4A9DD5C54043090F3B1"

        assert block_c.timestamp.source == TimestampSource.BROADCAST
        assert int(block_c.timestamp.date.timestamp()) > time.time() - 10
        assert not block_c.link_block

    def test_invalid_signature(
            self, mock_nanovault_node, mock_nanovault_ws_node,
            nanovault_ws_node_network_plugin):
        # If the node returns an invalid signature, the network plugin
        # will abort and shut itself down
        mock_nanovault_ws_node.add_replay_datasets(["invalid_signature"]).start()
        network_plugin = nanovault_ws_node_network_plugin

        # Start watching a single account
        network_plugin.account_sync_statuses["xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"] \
            = AccountSyncStatus(
                account_id="xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"
            )
        sync_status = network_plugin.account_sync_statuses[
            "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"]

        wait_for(lambda: network_plugin.connection_status.aborted, timeout=2)
        wait_for(lambda: not network_plugin.started, timeout=2)

        assert not sync_status.network_head
        assert not network_plugin.connected
        assert not network_plugin.started
        assert isinstance(
            network_plugin.connection_status.error, InvalidSignature
        )

    def test_pocketable_blocks(
            self, mock_nanovault_node, mock_nanovault_ws_node,
            nanovault_ws_node_network_plugin):
        mock_nanovault_node.add_replay_datasets([
            "nanovault_version", "ws_watching"
        ]).start()
        mock_nanovault_ws_node.add_replay_datasets(["pocketable"]).start()
        network_plugin = nanovault_ws_node_network_plugin

        # Start watching a single account
        network_plugin.account_sync_statuses["xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"] \
            = AccountSyncStatus(
                account_id="xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"
            )

        wait_for(
            lambda: network_plugin.pocketable_block_queue.qsize() == 1,
            timeout=1
        )

        link_block = network_plugin.pocketable_block_queue.get()

        assert link_block.block_hash == "82CDDC385108D25E520B9CB2C7CB539CDF2FD5C9C3D7F4992AB6E18D0135B85F"
        assert link_block.amount == 1000000000000000000000000000000
        assert link_block.recipient == "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"

        assert link_block.timestamp.source == TimestampSource.BROADCAST
        assert int(link_block.timestamp.date.timestamp()) > time.time() - 10
