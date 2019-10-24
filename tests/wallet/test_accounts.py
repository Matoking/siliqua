import pytest
from siliqua.network import BlockProcessError
from siliqua.util import RawBlock
from siliqua.wallet.accounts import (Account, AccountSource, Block,
                                       LinkBlock, PrecomputedWork)
from siliqua.wallet.exceptions import (InsufficientBalance,
                                         InvalidAccountBlock)
from nanolib.exceptions import (InvalidAccount, InvalidPrivateKey,
                                InvalidPublicKey, InvalidSignature,
                                InvalidWork)
from nanolib.work import solve_work
from tests.wallet.conftest import TEST_DIFFICULTY

PRIVATE_KEY = "1"*64
PUBLIC_KEY = "aca68a2d52fe17bab36d48456569fe7f91f23cb57b971b13faf236ebbcc7fa94"
ACCOUNT_ID = "xrb_3d78japo7ziqqcsptk47eonzwzwjyaydcywq5ebzowjpxgyehynnjc9pd5zj"
REPRESENTATIVE = \
    "xrb_1iwamgozb5ckj9zzojbnb79485dfiw8jegedzwzuzy5b4a19cbs8b4tsdzo3"
ACCOUNT_ID_B = \
    "xrb_1dpgwazap57hd5kyff7g61i3snsg8c1axzfwfg7exkx1qbfdbwsmdjykhtw4"

ACCOUNT_KWARGS = {
    "account_id": ACCOUNT_ID,
    "private_key": PRIVATE_KEY,
    "source": AccountSource.PRIVATE_KEY,
    "representative": REPRESENTATIVE,
}


STATE_LINK_BLOCK_DATA = {
    "account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
    "balance": "0",
    "link": "7EB064709F33C1E93541D48CBCE68C833FF105D1F3F7A9EF6B34CB23A849AB53",
    "previous": "E82CDC903E33AC80C2ACB6F3608FE9CFBDF610F11308F10CDDD8F6347F1CE058",
    "representative": "xrb_3dmtrrws3pocycmbqwawk6xs7446qxa36fcncush4s1pejk16ksbmakis78m",
    "signature": "505E3645F88CD37D4783A7242B8CF49BE9658E19576A17237B3F0BBF8A96249987596C9A65FA98BC904296BF0AB65EE3A9E5D48408A38ED30D9D474567083B0F",
    "type": "state",
    "work": "07ff830e5b022fbd"
}

LEGACY_LINK_BLOCK_DATA = {
    "previous": "56916EA71F487E109AA8412C97550DF45AD2159D8554A3AB111B0CEDAA91A96B",
    "destination": "nano_3u7d5iohy14swyhxhgfm9iq4xa9yibhcgnyj697uwhicp14dhx4woik5e9ek",
    "balance": "000008AE7B02AD7B5BF4C46BC7000000",
    "signature": "AF8CCAFDA2C2222F01F79994DAA99FBCB99F41905C921D90A9DAAD47B383DAF3EE560665F4D026056872BB5E90F97A18CA389F9562C06EFC2A2B9F2CCF614B0A",
    "work": "ca14a212a455b91a",
    "type": "send"
}


class TestLinkBlock:
    def test_link_block_create_state(self):
        block = RawBlock.from_dict(STATE_LINK_BLOCK_DATA)

        link_block = LinkBlock(block=block, amount=10000)

        assert link_block.amount == 10000
        assert link_block.block_hash == \
            "96970559D7257F63ACB8383ED57CB510745DE744ABCEC4DC41590CE7E32179EA"
        assert link_block.recipient == \
            "xrb_1zoiejrbyey3x6tn5o6eqmmas1szy64x5wzqo9qppf8d6gn6mctm1ndnrgyy"

    def test_link_block_create_legacy(self):
        block = RawBlock.from_dict(LEGACY_LINK_BLOCK_DATA)

        link_block = LinkBlock(block=block, amount=10000)

        assert link_block.amount == 10000
        assert link_block.block_hash == \
            "D5721A0E8485C15DB60577C0573ABA961EA51BF496C720A890E31CD910E62B2B"
        assert link_block.recipient == \
            "nano_3u7d5iohy14swyhxhgfm9iq4xa9yibhcgnyj697uwhicp14dhx4woik5e9ek"

    def test_link_block_data_required(self):
        with pytest.raises(ValueError) as exc:
            LinkBlock(amount=10000)

        assert "'block_data' or 'block' is required" in str(exc.value)

    def test_link_block_create_block_or_block_data(self):
        block = RawBlock.from_dict(STATE_LINK_BLOCK_DATA)

        with pytest.raises(ValueError) as exc:
            LinkBlock(block=block, block_data=STATE_LINK_BLOCK_DATA, amount=10000)

        assert "Only 'block_data' or 'block' is accepted" in str(exc.value)

    def test_link_block_verify_invalid_signature(self):
        block_data = STATE_LINK_BLOCK_DATA.copy()
        block_data["signature"] = "0"*128

        block = RawBlock.from_dict(block_data, verify=False)

        with pytest.raises(InvalidSignature):
            LinkBlock(block=block, amount=10000, verify=True)

    def test_link_block_verify_invalid_work(self):
        block_data = STATE_LINK_BLOCK_DATA.copy()
        block_data["work"] = "0"*16

        block = RawBlock.from_dict(block_data, verify=False)

        with pytest.raises(InvalidWork):
            LinkBlock(block=block, amount=10000, verify=True)


class TestBlock:
    def test_block_create_block_or_block_data(self):
        with pytest.raises(ValueError) as exc:
            Block(
                block_data=STATE_LINK_BLOCK_DATA,
                block=RawBlock.from_dict(STATE_LINK_BLOCK_DATA)
            )

        assert "Only 'block_data' or 'block'" in str(exc.value)

        with pytest.raises(ValueError) as exc:
            Block(block_data=None, block=None)

        assert "'block_data' or 'block' is required" in str(exc.value)


class TestAccountProperties:
    def test_account_create_account_id(self):
        account = Account(**ACCOUNT_KWARGS)

        assert account.account_id == ACCOUNT_ID

        # Account ID can't be invalid
        kwargs = ACCOUNT_KWARGS.copy()
        kwargs["account_id"] = "invalid"
        with pytest.raises(InvalidAccount):
            Account(**kwargs)

        # Account ID is required
        del kwargs["account_id"]
        with pytest.raises(ValueError) as exc:
            Account(**kwargs)

        assert "Field 'account_id' is required" in str(exc.value)

    def test_account_create_private(self):
        account = Account(**ACCOUNT_KWARGS)

        assert account.private_key == PRIVATE_KEY

        # Private key can't be invalid
        kwargs = ACCOUNT_KWARGS.copy()
        kwargs["private_key"] = "invalid"
        with pytest.raises(InvalidPrivateKey):
            Account(**kwargs)

    def test_account_create_source(self):
        kwargs = {
            "account_id": ACCOUNT_ID,
            "private_key": PRIVATE_KEY,
            "public_key": PUBLIC_KEY
        }

        # Invalid account source
        with pytest.raises(ValueError) as exc:
            Account(source="non existent", **kwargs)

        assert "is not a valid AccountSource" in str(exc.value)

        # Missing account source
        with pytest.raises(ValueError) as exc:
            Account(**kwargs)

        assert "Field 'source' is required" in str(exc.value)

    def test_account_create_representative(self):
        account = Account(**ACCOUNT_KWARGS)
        assert account.representative == REPRESENTATIVE

        kwargs = ACCOUNT_KWARGS.copy()
        kwargs["representative"] = "invalid"

        # Invalid representative
        with pytest.raises(InvalidAccount) as exc:
            Account(**kwargs)

        assert "while changing property 'representative'" in str(exc.value)


class TestAccountBlockOperations:
    def test_account_receive_first(self, pocketable_block_factory):
        """
        Receive the first state block on an account and check that it's
        an open block
        """
        account = Account(**ACCOUNT_KWARGS)

        assert account.balance == 0

        # Create a fake block to receive 10000 raw
        link_block = pocketable_block_factory(account_id=ACCOUNT_ID, amount=10000)

        account.receive_block(link_block)
        first_block = account.blocks[0]

        assert account.balance == 10000

        # Check the receiving block
        assert first_block.link == first_block.link_block.block_hash
        assert first_block.amount == 10000
        assert first_block.block_type == "state"
        assert first_block.tx_type == "open"

        # Check the sending block
        assert first_block.link_block.link_as_account == ACCOUNT_ID

        assert first_block.prev is None
        assert first_block.next is None

    def test_account_receive_multiple(self, pocketable_block_factory):
        """
        Receive two state blocks to start an account blockchain
        """
        account = Account(**ACCOUNT_KWARGS)

        # Create fake blocks to receive 10000 and 20000 raw respectively
        link_block_a = pocketable_block_factory(
            account_id=ACCOUNT_ID, amount=10000)
        link_block_b = pocketable_block_factory(
            account_id=ACCOUNT_ID, amount=20000)

        account.receive_block(link_block_a)
        account.receive_block(link_block_b)

        assert account.balance == 30000

        first_block, second_block = account.blocks

        # Blockchain forms a linked list
        assert first_block.next == second_block
        assert second_block.prev == first_block

        assert second_block.block_type == "state"
        assert second_block.tx_type == "receive"
        assert second_block.previous == first_block.block_hash
        assert second_block.amount == 20000
        assert second_block.balance == 30000
        assert second_block.link == link_block_b.block_hash

    def test_account_receive_legacy_first(
            self, legacy_pocketable_block_factory):
        """
        Receive a legacy receive block to start an account blockchain
        """
        account = Account(**ACCOUNT_KWARGS)

        # Create a fake block to receive 10000 raw
        link_block = legacy_pocketable_block_factory(
            account_id=ACCOUNT_ID, amount=10000)

        account.receive_block(link_block)

        assert account.balance == 10000

        first_block = account.blocks[0]

        # Check the receiving block
        assert first_block.link == first_block.link_block.block_hash
        assert first_block.amount == 10000
        assert first_block.block_type == "state"
        assert first_block.tx_type == "open"

        assert first_block.prev is None
        assert first_block.next is None

    def test_account_receive_legacy_multiple(self, legacy_pocketable_block_factory):
        """
        Receive two legacy receive blocks to start an account blockchain
        """
        account = Account(**ACCOUNT_KWARGS)

        # Create two fake blocks to receive 10000 and 20000 raw respectively
        link_block_a = legacy_pocketable_block_factory(
            account_id=ACCOUNT_ID, amount=10000)
        link_block_b = legacy_pocketable_block_factory(
            account_id=ACCOUNT_ID, amount=20000)

        account.receive_block(link_block_a)
        account.receive_block(link_block_b)

        assert account.balance == 30000

        first_block, second_block = account.blocks

        # Blockchain forms a linked list
        assert first_block.next == second_block
        assert second_block.prev == first_block

        assert second_block.block_type == "state"
        assert second_block.tx_type == "receive"
        assert second_block.previous == first_block.block_hash
        assert second_block.amount == 20000
        assert second_block.balance == 30000
        assert second_block.link == link_block_b.block_hash

    def test_account_receive_duplicate(self, pocketable_block_factory):
        """
        Try receiving the same block twice
        """
        account = Account(**ACCOUNT_KWARGS)

        link_block = pocketable_block_factory(account_id=ACCOUNT_ID, amount=10000)

        account.receive_block(link_block)
        assert account.balance == 10000

        # Second attempt will do nothing
        assert account.receive_block(link_block) is None
        assert account.balance == 10000

    def test_account_add_block_different_account(
            self, account_factory):
        account = Account(**ACCOUNT_KWARGS)

        block = account_factory(balance=1000).blocks[0]

        with pytest.raises(InvalidAccountBlock) as exc:
            account.add_block(block)

        assert "The block doesn't belong to this account's blockchain" \
            in str(exc.value)

    def test_account_add_block_not_block(
            self, account_factory, pocketable_block_factory):
        account = Account(**ACCOUNT_KWARGS)

        link_block = pocketable_block_factory(
            account_id=ACCOUNT_ID, amount=1000)

        with pytest.raises(TypeError) as exc:
            account.add_block(link_block)

        assert "Argument has to be a Block instance" in str(exc.value)

    def test_account_add_block_wrong_order(self, pocketable_block_factory):
        """
        Try adding blocks to an account in wrong order
        """
        account = Account(**ACCOUNT_KWARGS)

        for _ in range(0, 3):
            account.receive_block(
                pocketable_block_factory(account_id=ACCOUNT_ID, amount=1000)
            )

        block_a = account.blocks[0]
        block_c = account.blocks[2]

        # Recreate account
        account = Account(**ACCOUNT_KWARGS)
        account.add_block(block_a)

        # Block added in wrong order
        with pytest.raises(InvalidAccountBlock) as exc:
            account.add_block(block_c)

        assert "isn't a successor to the current head" in str(exc.value)

    def test_account_add_block_first_non_open(self, pocketable_block_factory):
        """
        Try adding a non-open block as the first block to an account
        """
        account = Account(**ACCOUNT_KWARGS)

        for _ in range(0, 2):
            account.receive_block(
                pocketable_block_factory(account_id=ACCOUNT_ID, amount=1000)
            )

        block_b = account.blocks[1]

        # Recreate account
        account = Account(**ACCOUNT_KWARGS)

        with pytest.raises(InvalidAccountBlock) as exc:
            account.add_block(block_b)

        assert "First block for an account has to be an 'open' block" in str(exc.value)

    def test_account_add_block_precomputed_work(
            self, pocketable_block_factory):
        account = Account(**ACCOUNT_KWARGS)

        account.receive_block(
            pocketable_block_factory(account_id=ACCOUNT_ID, amount=1000)
        )

        # Precompute work
        account.precomputed_work = PrecomputedWork(
            work=solve_work(
                account.blocks[-1].block_hash, difficulty=TEST_DIFFICULTY
            ),
            difficulty=TEST_DIFFICULTY
        )

        block = account.receive_block(
            pocketable_block_factory(account_id=ACCOUNT_ID, amount=1000)
        )

        # The precomputed work is used
        assert block.work
        assert not account.precomputed_work

    def test_account_add_block_invalid_precomputed_work(
            self, pocketable_block_factory):
        account = Account(**ACCOUNT_KWARGS)
        account.receive_block(
            pocketable_block_factory(account_id=ACCOUNT_ID, amount=1000)
        )

        # Precompute work
        account.precomputed_work = PrecomputedWork(
            work=solve_work(
                account.blocks[-1].block_hash, difficulty=TEST_DIFFICULTY
            ),
            difficulty=TEST_DIFFICULTY
        )

        # Use an arbitrarily high difficulty to make the precomputed work
        # invalid
        account.precomputed_work.difficulty = "f"*16

        # Precomputed work is discarded silently since it was invalid
        # at the time the block was received
        block = account.receive_block(
            pocketable_block_factory(account_id=ACCOUNT_ID, amount=1000)
        )
        assert not block.work
        assert not account.precomputed_work

    def test_account_reject_block_non_confirmed(self, account_factory):
        # Create an account with 5 non-confirmed blocks and reject the 4th
        # block
        account = account_factory(
            balance=10000, block_count=5, complete=True, confirm=False)

        block = account.blocks[3]
        account.reject_block(
            block,
            error=BlockProcessError.PREVIOUS_BLOCK_MISSING
        )

        assert len(account.blocks) == 3
        assert len(account.block_map) == 6

        # Trying to reject the block again does nothing
        # This can happen since network and wallet are in different threads
        account.reject_block(
            block, error=BlockProcessError.PREVIOUS_BLOCK_MISSING
        )

        assert len(account.blocks) == 3
        assert len(account.block_map) == 6

    def test_account_reject_block_confirmed(self, account_factory):
        # Create an account with 5 confirmed blocks and try to reject
        # the 4th block
        account = account_factory(
            balance=10000, block_count=5, complete=True, confirm=True)

        with pytest.raises(ValueError) as exc:
            account.reject_block(
                account.blocks[3],
                error=BlockProcessError.PREVIOUS_BLOCK_MISSING
            )

        assert "Can't reject a confirmed block" in str(exc.value)

    def test_account_remove_block_non_confirmed(self, account_factory):
        # Create an account with 5 non-confirmed blocks
        # and remove the 4th block
        account = account_factory(
            balance=10000, block_count=5, complete=True, confirm=False)

        assert len(account.blocks) == 5
        # Block map includes link blocks as well
        assert len(account.block_map) == 10

        assert not account.confirmed_head
        # Remove the fourth block and ensure the fifth is removed as well
        block_d = account.blocks[3]
        block_hash_d = block_d.block_hash
        block_hash_e = block_d.next.block_hash

        account.remove_block(block_d)

        assert len(account.blocks) == 3
        assert len(account.block_map) == 6

        assert block_hash_d not in account.block_map
        assert block_hash_e not in account.block_map

        assert not account.confirmed_head

    def test_account_remove_block_confirmed(self, account_factory):
        # Create an account with 5 confirmed blocks
        # and remove the 4th block
        account = account_factory(
            balance=10000, block_count=5, complete=True, confirm=True)

        assert len(account.blocks) == 5
        assert len(account.block_map) == 10

        assert account.confirmed_head == account.blocks[4]

        block_d = account.blocks[3]

        account.remove_block(block_d)

        assert len(account.blocks) == 3
        assert len(account.block_map) == 6

        assert account.confirmed_head == account.blocks[2]

    def test_account_legacy_block_disallowed_after_state(
            self, pocketable_block_factory, legacy_receive_block_factory):
        """
        Add a state block and then try adding a legacy receive block
        """
        account = Account(**ACCOUNT_KWARGS)

        account.receive_block(
            pocketable_block_factory(account_id=ACCOUNT_ID, amount=10000)
        )

        with pytest.raises(InvalidAccountBlock) as exc:
            # Once a state block is added to a chain, only state blocks are
            # allowed
            account.add_block(
                legacy_receive_block_factory(
                    prev_block=account.blocks[0],
                    private_key=PRIVATE_KEY,
                    amount=20000
                )
            )

        assert "State block can't be followed by a legacy block" in str(exc.value)

    def test_account_send_legacy_block(self, legacy_pocketable_block_factory):
        """
        Receive NANO from a legacy block and then spend it
        """
        account = Account(**ACCOUNT_KWARGS)

        account.receive_block(
            legacy_pocketable_block_factory(account_id=ACCOUNT_ID, amount=10000)
        )

        first_block = account.blocks[0]

        send_block = account.send(account_id=ACCOUNT_ID_B, amount=6000)

        assert account.balance == 4000

        assert send_block.balance == 4000
        # Since we're sending, the amount is negative
        assert send_block.amount == -6000
        assert send_block.previous == first_block.block_hash

    def test_account_send_float_not_allowed(self, account_factory):
        """
        Try sending NANO using a float amount
        """
        account = account_factory(balance=10000)

        with pytest.raises(TypeError) as exc:
            account.send(account_id=ACCOUNT_ID_B, amount=100.5)

        assert "Floating numbers are not allowed" in str(exc.value)

    def test_account_send_private_key_required(self, account_factory):
        """
        Try sending NANO from a watching-only account
        """
        account = account_factory(balance=10000)
        account.private_key = None

        with pytest.raises(ValueError) as exc:
            account.send(account_id=ACCOUNT_ID_B, amount=100)

        assert "Private key required to send" in str(exc.value)

    def test_account_send_string_amount(self, account_factory):
        """
        Try sending NANO using amounts encapsulated in strings
        """
        account = account_factory(balance=10000)

        block = account.send(account_id=ACCOUNT_ID_B, amount="1000")

        assert block.amount == -1000
        assert account.balance == 9000

        with pytest.raises(ValueError) as exc:
            account.send(account_id=ACCOUNT_ID_B, amount="1000.5")

        assert "Strings can only contain an integer" in str(exc.value)

    def test_account_send_incorrect_amount(self, account_factory):
        account = account_factory(balance=10000)

        # Try sending a zero and negative amounts, both should fail
        for amount in (0, -1000):
            with pytest.raises(ValueError) as exc:
                account.send(account_id=ACCOUNT_ID_B, amount=amount)

            assert "Value must be at least 1 raw" in str(exc.value)

    def test_account_legacy_send_balance(self):
        """
        Test that balance is calculated correctly for legacy send blocks
        """
        account = Account(
            account_id="xrb_1jeqoxg7cpo5xgyxhcwzsndeuqp6yyr9m63k8tfu9mskjdfo7iq95p1ktb8j",
            source=AccountSource.WATCHING,
            representative="xrb_3dmtrrws3pocycmbqwawk6xs7446qxa36fcncush4s1pejk16ksbmakis78m"
        )
        account.add_block(
            Block(
                block_data={
                    "account": "xrb_1jeqoxg7cpo5xgyxhcwzsndeuqp6yyr9m63k8tfu9mskjdfo7iq95p1ktb8j",
                    "type": "open",
                    "representative": "xrb_3dmtrrws3pocycmbqwawk6xs7446qxa36fcncush4s1pejk16ksbmakis78m",
                    "source": "01BB6121002B428124BB0C546B3195F36108D30F8E664DC60777F3B4102A705F",
                    "work": "e847031ddf0c4cef",
                    "signature": "E23FA05FC070E176195A4860EC2E73966AE040A91B6F972B5843B31879BBBD32EF0D0186FF9EC2EF1714274FF45B7FF715FDF99BB3ED4571AD8798A28BAF1B0E",
                },
                link_block=LinkBlock(
                    block_data={
                        "account": "xrb_1uz6t43ztbffhft3zonpwf4hrjd9gorg53j8ac48ijppo6t4kj1px9jnimwj",
                        "destination": "xrb_1jeqoxg7cpo5xgyxhcwzsndeuqp6yyr9m63k8tfu9mskjdfo7iq95p1ktb8j",
                        "type": "send",
                        "previous": "D04DEDF65FE1A99AA6759285512A6DE6708961443538C80CA588B032017497D6",
                        "work": "547ac17fc277bd4c",
                        "signature": "60C7D5546289179A480477BBEB62CB9BE8ABDD6B52DA4FC95D3BB28D0C88922D1D9022537626D835E67A407C8CDDFE376DE2C46EE4F04F1FEE88D2AABEAA6D09",
                        "balance": "00018CE88D23D425E48205A276400000"
                    },
                    amount=1000000000000000000000000000
                )
            )
        )
        account.add_block(
            Block(
                block_data={
                    "account": "xrb_1jeqoxg7cpo5xgyxhcwzsndeuqp6yyr9m63k8tfu9mskjdfo7iq95p1ktb8j",
                    "destination": "xrb_384jppoodym71cppdj3a9gaim197q9uq365u5jqt6c4zhth13t9as4sj5zs8",
                    "type": "send",
                    "previous": "2453CA428DE7BCA437CDCBCD587646B4E508701E78E5B364F1DF5CF3A80B9F24",
                    "work": "6692fe717be16f9c",
                    "signature": "11E5BFB1304CD12D6960403B98778F76A6023FFFF30174DD21304EE757BD264E8F87FC6649E916BC9DFA861ACB94631C5E388C6ABF412C08891F9818C6CA1B09",
                    "balance": "00000000033A5A7A8401B34F47000000"
                }
            )
        )

        assert account.balance == 999000000000000000000000000
        assert account.blocks[1].balance == 999000000000000000000000000
        assert account.blocks[1].amount == -1000000000000000000000000

    def test_account_send_insufficient_balance(self, account_factory):
        account = account_factory(balance=10000)

        with pytest.raises(InsufficientBalance):
            account.send(account_id=ACCOUNT_ID_B, amount=10001)

    def test_account_change_representative_empty(self):
        account = Account(**ACCOUNT_KWARGS)

        account.change_representative(ACCOUNT_ID_B)

        # Changing the representative on an empty account doesn't
        # create a new block
        assert len(account.blocks) == 0
        assert account.representative == ACCOUNT_ID_B

    def test_account_change_representative_change_block(self, account_factory):
        account = account_factory(balance=10000)

        # On a non-empty account, changing the representative creates
        # a change block
        account.change_representative(ACCOUNT_ID_B)

        second_block = account.blocks[1]

        assert second_block.block_type == "state"
        assert second_block.tx_type == "change"
        assert second_block.representative == ACCOUNT_ID_B

    def test_account_change_representative_already_active(
            self, account_factory):
        account = account_factory(balance=10000)

        account.change_representative(ACCOUNT_ID_B)

        with pytest.raises(ValueError) as exc:
            account.change_representative(ACCOUNT_ID_B)

        assert "is already assigned for this account" in str(exc.value)

    def test_account_change_representative_invalid_account_id(self):
        account = Account(**ACCOUNT_KWARGS)

        with pytest.raises(InvalidAccount):
            account.change_representative("invalid")

    def test_account_update_confirmed_head(self, account_factory):
        account_a, account_b, account_c, account_d = [
            account_factory(
                balance=10000, block_count=5, complete=True, confirm=True)
            for _ in range(0, 4)
        ]

        account_a.confirmed_head = None
        account_b.confirmed_head = None
        account_c.confirmed_head = None
        account_d.confirmed_head = None

        # For 1st account, confirm 1st block (confirmed head = 1st)
        # For 2nd account, confirm 2nd block (confirmed head = None)
        # For 3rd account, confirm 1st and 3rd block (confirmed head = 1st)
        # For 4th account, confirm 1st, 2nd and 4th block (confirmed head = 2nd)
        account_a.blocks[1].confirmed = False
        account_a.blocks[2].confirmed = False
        account_a.blocks[3].confirmed = False
        account_a.blocks[4].confirmed = False

        account_b.blocks[0].confirmed = False
        account_b.blocks[2].confirmed = False
        account_b.blocks[3].confirmed = False
        account_b.blocks[4].confirmed = False

        account_c.blocks[1].confirmed = False
        account_c.blocks[3].confirmed = False
        account_c.blocks[4].confirmed = False

        account_d.blocks[2].confirmed = False
        account_d.blocks[4].confirmed = False

        account_a.update_confirmed_head()
        account_b.update_confirmed_head()
        account_c.update_confirmed_head()
        account_d.update_confirmed_head()

        assert account_a.confirmed_head == account_a.blocks[0]
        assert not account_b.confirmed_head
        assert account_c.confirmed_head == account_c.blocks[0]
        assert account_d.confirmed_head == account_d.blocks[1]

    def test_account_complete_blockchain(self):
        """
        Complete account's blockchain one block at a time and check
        the account's balance after each block
        """
        from tests.wallet.data.account_blocks import ACCOUNTS

        for account_entry in ACCOUNTS:
            block_entries = account_entry["blocks"]
            account_id = account_entry["account_id"]
            account = Account(
                account_id=account_id,
                source=AccountSource.WATCHING
            )

            assert account.balance == 0

            for entry in block_entries:
                block_data = entry["block_data"]
                link_block_entry = entry.get("link_block", None)

                link_block = None
                if link_block_entry:
                    link_block = LinkBlock(
                        block_data=link_block_entry["block_data"],
                        amount=int(link_block_entry["amount"])
                    )

                block = Block(
                    block_data=block_data,
                    link_block=link_block
                )

                account.add_block(block)

                assert account.balance == int(entry["balance"])
                assert account.blocks[-1].balance == int(entry["balance"])
                assert account.blocks[-1].tx_type == entry["tx_type"]
                assert account.blocks[-1].amount == int(entry["amount"])
