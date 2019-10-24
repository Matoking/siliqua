import time

import pytest
from siliqua.network import AccountSyncStatus
from siliqua.util import RawBlock
from siliqua.wallet import Block
from siliqua.network import BlockProcessError
from siliqua.wallet.util import TimestampSource
from nanolib.exceptions import InvalidSignature
from tests.util import wait_for


class TestJSONRPCProcessor:
    def test_sync_legacy_watching(self, mock_node, node_network_plugin):
        # Synchronize an account blockchain consisting only of legacy blocks
        mock_node.add_replay_datasets([
            "legacy_watching", "active_difficulty", "version"
        ]).start()
        network_plugin = node_network_plugin

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

    def test_sync_state_watching(self, mock_node, node_network_plugin):
        # Synchronize an account blockchain consisting only of state blocks
        mock_node.add_replay_datasets([
            "state_watching", "active_difficulty", "version"
        ]).start()
        network_plugin = node_network_plugin

        network_plugin.account_sync_statuses["xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"] \
            = AccountSyncStatus(
                account_id="xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"
            )

        # Wait until the account has finished syncing
        sync_status = network_plugin.account_sync_statuses[
            "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"]
        wait_for(lambda: sync_status.sync_complete, timeout=2)

        assert network_plugin.processed_block_queue.qsize() == 3

        block_results = [
            network_plugin.processed_block_queue.get_nowait() for _ in range(0, 3)
        ]
        blocks = [
            result.block for result in block_results
        ]
        block_a, block_b, block_c = blocks

        assert block_a.block_hash == "E82CDC903E33AC80C2ACB6F3608FE9CFBDF610F11308F10CDDD8F6347F1CE058"
        assert block_b.block_hash == "96970559D7257F63ACB8383ED57CB510745DE744ABCEC4DC41590CE7E32179EA"
        assert block_c.block_hash == "62EE070DA06632FE1E54BA32FD25B00A5FD4E8CF09354A9B176CBF6BC33CDBDB"

        assert block_a.link == "82CDDC385108D25E520B9CB2C7CB539CDF2FD5C9C3D7F4992AB6E18D0135B85F"
        assert block_a.link == block_a.link_block.block_hash

        assert block_b.link == "7EB064709F33C1E93541D48CBCE68C833FF105D1F3F7A9EF6B34CB23A849AB53"
        # Link blocks are retrieved for receive blocks, not send blocks
        assert not block_b.link_block

        assert not block_c.link_block

    def test_sync_state_watching_incomplete(self, mock_node, node_network_plugin):
        # Synchronize an account blockchain consisting only of state blocks and
        # in which the last block is still unconfirmed
        mock_node.add_replay_datasets([
            "state_watching_incomplete", "active_difficulty", "version"
        ]).start()
        network_plugin = node_network_plugin

        network_plugin.account_sync_statuses["xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"] \
            = AccountSyncStatus(
                account_id="xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"
            )

        # Wait until the account has finished syncing
        sync_status = network_plugin.account_sync_statuses[
            "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"]
        wait_for(
            lambda: sync_status.network_head == "96970559D7257F63ACB8383ED57CB510745DE744ABCEC4DC41590CE7E32179EA",
            timeout=2
        )

        # Sync is not complete as long as there unconfirmed blocks in the
        # blockchain
        assert not sync_status.sync_complete
        assert network_plugin.processed_block_queue.qsize() == 2

        block_results = [
            network_plugin.processed_block_queue.get_nowait() for _ in range(0, 2)
        ]
        blocks = [
            result.block for result in block_results
        ]
        block_a, block_b = blocks

        assert block_a.block_hash == "E82CDC903E33AC80C2ACB6F3608FE9CFBDF610F11308F10CDDD8F6347F1CE058"
        assert block_b.block_hash == "96970559D7257F63ACB8383ED57CB510745DE744ABCEC4DC41590CE7E32179EA"

        assert block_a.link == "82CDDC385108D25E520B9CB2C7CB539CDF2FD5C9C3D7F4992AB6E18D0135B85F"
        assert block_a.link == block_a.link_block.block_hash

        assert block_b.link == "7EB064709F33C1E93541D48CBCE68C833FF105D1F3F7A9EF6B34CB23A849AB53"
        # Link blocks are retrieved for receive blocks, not send blocks
        assert not block_b.link_block

    def test_sync_empty_watching(self, mock_node, node_network_plugin):
        """
        Synchronize account blockchain when no blocks for the account
        exist yet
        """
        mock_node.add_replay_datasets([
            "empty_watching", "active_difficulty", "version"
        ]).start()
        network_plugin = node_network_plugin

        network_plugin.account_sync_statuses["xrb_15n1wthxc5ndjnoufdfe8m4z5j973o6trzwbfys4cu4gtju5mh4xc918fout"] \
            = AccountSyncStatus(
                account_id="xrb_15n1wthxc5ndjnoufdfe8m4z5j973o6trzwbfys4cu4gtju5mh4xc918fout"
            )

        # Wait until the account has finished syncing
        sync_status = network_plugin.account_sync_statuses[
            "xrb_15n1wthxc5ndjnoufdfe8m4z5j973o6trzwbfys4cu4gtju5mh4xc918fout"]
        wait_for(lambda: sync_status.sync_complete, timeout=1)

        assert not sync_status.network_head

    def test_sync_invalid_signature(self, mock_node, node_network_plugin):
        # If the node returns an invalid signature, the network plugin
        # will abort and shut itself down
        mock_node.add_replay_datasets([
            "legacy_watching_invalid_signature", "active_difficulty", "version"
        ]).reload()
        network_plugin = node_network_plugin

        network_plugin.account_sync_statuses["xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf"] \
            = AccountSyncStatus(
                account_id="xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf"
            )

        sync_status = network_plugin.account_sync_statuses[
            "xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf"]

        wait_for(lambda: network_plugin.connection_status.aborted, timeout=2)

        assert not sync_status.network_head
        assert not network_plugin.connected
        assert not network_plugin.started
        assert isinstance(
            network_plugin.connection_status.error, InvalidSignature
        )

    def test_broadcast_block_success(self, mock_node, node_network_plugin):
        # Sync account with two blocks and broadcast the third block
        # while simulating successful transmission
        mock_node.add_replay_datasets(
            ["state_broadcast_success", "active_difficulty", "version"]
        ).reload()
        network_plugin = node_network_plugin

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

    @pytest.mark.parametrize("replay_dataset,expected_error", [
        (
            "state_broadcast_failure_previous_missing",
            BlockProcessError.PREVIOUS_BLOCK_MISSING
        ),
        (
            "state_broadcast_failure_disappear",
            BlockProcessError.UNKNOWN
        ),
        (
            "state_broadcast_failure_timeout",
            BlockProcessError.TIMEOUT
        )
    ])
    def test_broadcast_block_failure_rejected(
            self, mock_node, node_network_plugin, replay_dataset,
            expected_error):
        # Sync account with two blocks and broadcast the third block
        # while simulating failure
        mock_node.add_replay_datasets([
            replay_dataset, "active_difficulty", "version"
        ]).reload()
        network_plugin = node_network_plugin

        network_plugin.account_sync_statuses["xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"] \
            = AccountSyncStatus(
                account_id="xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"
            )

        # For 'timeout' test case, cause a timeout in 1 second to make
        # the test case shorter
        network_plugin.rpc_processor.CONFIRMATION_TIMEOUT_SECONDS = 1

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
        wait_for(
            lambda: network_plugin.processed_block_queue.qsize() == 3,
            timeout=2
        )

        _, _, block = [
            network_plugin.processed_block_queue.get_nowait() for _ in range(0, 3)
        ]

        assert block.rejected
        assert not block.confirmed
        assert block.error == expected_error

        assert block.block_hash == \
            "62EE070DA06632FE1E54BA32FD25B00A5FD4E8CF09354A9B176CBF6BC33CDBDB"

    def test_broadcast_block_duplicate(self, mock_node, node_network_plugin):
        # Try broadcasting a block that is already confirmed
        # The network plugin should silently ignore the resulting error
        mock_node.add_replay_datasets(
            ["state_broadcast_duplicate", "active_difficulty", "version"]
        ).reload()
        network_plugin = node_network_plugin

        network_plugin.account_sync_statuses["xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"] \
            = AccountSyncStatus(
                account_id="xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"
            )

        # Wait until the account has finished syncing
        sync_status = network_plugin.account_sync_statuses[
            "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc"]
        wait_for(lambda: sync_status.sync_complete, timeout=2)

        assert network_plugin.processed_block_queue.qsize() == 2

        # Broadcast the third already confirmed block
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

        assert network_plugin.processed_block_queue.qsize() == 2

        _, block = [
            network_plugin.processed_block_queue.get_nowait() for _ in range(0, 2)
        ]

        assert block.confirmed
        assert not block.rejected

        assert block.block_hash == \
            "96970559D7257F63ACB8383ED57CB510745DE744ABCEC4DC41590CE7E32179EA"

    def test_update_pocketable_blocks(self, mock_node, node_network_plugin):
        # Sync account blockchain with two blocks and make sure two
        # pending blocks are found
        mock_node.add_replay_datasets(
            ["state_pocketable_pending", "active_difficulty", "version"]
        ).reload()
        network_plugin = node_network_plugin

        network_plugin.account_sync_statuses["xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy"] \
            = AccountSyncStatus(
                account_id="xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy"
            )

        # Wait until the account has finished syncing
        sync_status = network_plugin.account_sync_statuses[
            "xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy"]
        wait_for(
            lambda: sync_status.sync_complete, timeout=2)
        wait_for(
            lambda: network_plugin.pocketable_block_queue.qsize() == 2, timeout=2)

        blocks = [
            network_plugin.pocketable_block_queue.get_nowait() for _ in range(0, 2)
        ]
        block_a = next(
            block for block in blocks
            if block.block_hash == "C4BDB10778120F6748959EF7312C443BD0BFF4FE97F02A20B874694EB03DE0D0")
        block_b = next(
            block for block in blocks
            if block.block_hash == "D96D72919D6EEAA9B82FE8046EBE70E20886E4D6C3BA218AD5340DD63AEE09C6")

        assert block_a.account_id == "xrb_3qbettndeemurhst593izae7j6x746bdzktmr16qfh9oa9uizxnuxkxgaiqd"
        assert block_a.amount == 1000000000000000000000000000000
        assert block_a.link_as_account == "xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy"

        assert block_b.account_id == "xrb_36gijoeijuazu7d9urtxm1jqgejw43bi3tcfjx4i98q9mxuqhrsjs5dk1d9i"
        assert block_b.amount == 1000000000000000000000000000
        assert block_b.link_as_account == "xrb_1w77aapnijnm5mo16r3xtpqu7n459r61fqpcdt3kxfmz8gtqgzbozswxmduy"

    def test_wait_for_connection(self, mock_node, node_network_plugin):
        # Run the mock node with no mocked responses;
        # this will cause all requests to fail and causes 'wait_for_connection'
        # to timeout
        mock_node.start()

        with pytest.raises(TimeoutError):
            node_network_plugin.wait_for_connection(timeout=1)

        mock_node.add_replay_datasets(["active_difficulty", "version"]).reload()

        assert node_network_plugin.wait_for_connection(timeout=1)


class TestWebSocketProcessor:
    def test_active_difficulty(
            self, mock_node, mock_ws_node, ws_node_network_plugin):
        # HTTP server won't broadcast the difficulty
        mock_node.add_replay_datasets(["legacy_watching", "version"]).start()

        # WebSocket server will broadcast the difficulty
        mock_ws_node.add_replay_datasets(["active_difficulty"]).start()
        network_plugin = ws_node_network_plugin

        wait_for(
            lambda: network_plugin.work_difficulty == "0000000088664422",
            timeout=1
        )

    def test_confirmed_blocks(
            self, mock_node, mock_ws_node, ws_node_network_plugin):
        mock_node.add_replay_datasets([
            "active_difficulty", "version", "ws_watching"
        ]).start()
        mock_ws_node.add_replay_datasets(["watching"]).start()
        network_plugin = ws_node_network_plugin

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
            self, mock_node, mock_ws_node, ws_node_network_plugin):
        # If the node returns an invalid signature, the network plugin
        # will abort and shut itself down
        mock_node.add_replay_datasets([
            "active_difficulty", "version"
        ]).reload()
        mock_ws_node.add_replay_datasets(["invalid_signature"]).start()
        network_plugin = ws_node_network_plugin

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
            self, mock_node, mock_ws_node, ws_node_network_plugin):
        mock_node.add_replay_datasets([
            "active_difficulty", "version", "ws_watching"
        ]).start()
        mock_ws_node.add_replay_datasets(["pocketable"]).start()
        network_plugin = ws_node_network_plugin

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
