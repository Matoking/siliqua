import base64
import copy
import json
import os.path

import pytest
from nanolib import Block as RawBlock
from nanolib import InvalidAccount, InvalidPrivateKey, generate_seed
from siliqua.network import BlockSyncResult
from siliqua.wallet import (Account, AccountSource, Block, Secret, Transaction,
                            Wallet, WalletProperties, WalletSeedAlgorithm)
from siliqua.wallet.exceptions import (AccountAlreadyExists,
                                       InvalidEncryptionKey,
                                       TransactionAlreadyExists, WalletLocked)
from tests.util import to_hex
from tests.wallet.conftest import TEST_DIFFICULTY

SECRETS_ENCRYPTED_WALLET_PATH = os.path.join(
    "tests", "wallet", "data", "secrets_encrypted.wallet")
BOTH_ENCRYPTED_WALLET_PATH = os.path.join(
    "tests", "wallet", "data", "both_encrypted.wallet")


class TestWalletProperties:
    def test_wallet_properties_seed_algorithm(self, wallet_properties):
        assert wallet_properties.seed_algorithm == WalletSeedAlgorithm.NANO

        # Invalid seed algorithm isn't allowed
        with pytest.raises(ValueError) as exc:
            wallet_properties.seed_algorithm = "fake"

        assert "is not a valid WalletSeedAlgorithm" in str(exc.value)

    def test_wallet_properties_seed(self, wallet_properties):
        assert len(wallet_properties.seed) == 64
        int(wallet_properties.seed, 16)  # Seed is hex

        with pytest.raises(ValueError) as exc:
            wallet_properties.seed = "invalid"

        assert "Seed must be a 64-character hex" in str(exc.value)

    def test_wallet_properties_gap_limit(self, wallet_properties):
        # Gap limit can be 0
        wallet_properties.gap_limit = 0

        # but gap limit can't be below 0
        with pytest.raises(ValueError) as exc:
            wallet_properties.gap_limit = -1

        assert "Positive integer is required" in str(exc.value)

        # Gap limit can be None
        wallet_properties.gap_limit = None

    def test_wallet_properties_representative(self, wallet_properties):
        wallet_properties.representative = None
        assert not wallet_properties.representative

        # Added representative is normalized to 'xrb_'
        wallet_properties.representative = \
            "nano_16aj46aj46aj46aj46aj46aj46aj46aj46aj46aj46aj46aj46ajbtsyew7c"
        assert wallet_properties.representative == \
            "xrb_16aj46aj46aj46aj46aj46aj46aj46aj46aj46aj46aj46aj46ajbtsyew7c"

        # Invalid account IDs not allowed
        with pytest.raises(InvalidAccount):
            wallet_properties.representative = "invalid"

    def test_wallet_properties_version(self, wallet_properties):
        wallet_properties.version = 2

        # Version can't be a float
        with pytest.raises(TypeError) as exc:
            wallet_properties.version = 1.5

        assert "Only integers" in str(exc.value)

        # Versoin cannot be None
        with pytest.raises(ValueError) as exc:
            wallet_properties.version = None

        assert "Version is required" in str(exc.value)


class TestWalletOperations:
    def test_wallet_balance(self, wallet_factory, pocketable_block_factory):
        wallet = wallet_factory(balance=12345)

        # Pocket NANO in two other accounts as well
        account_b = wallet.accounts[5]
        account_c = wallet.accounts[10]

        account_b.receive_block(
            pocketable_block_factory(
                account_id=account_b.account_id,
                amount=10000
            )
        )
        account_c.receive_block(
            pocketable_block_factory(
                account_id=account_c.account_id,
                amount=20000
            )
        )

        assert wallet.balance == 42345

    def test_wallet_representative(
            self, wallet_factory, pocketable_block_factory):
        wallet = wallet_factory(balance=0)

        account_a = wallet.accounts[0]
        account_a.representative = None

        account_b = wallet.accounts[1]
        account_b.representative = \
            "xrb_1e9dxacspemqghwwt4mzwtasdis43ny7topxuntuserzwi5xmx671erpjs4u"

        account_a.receive_block(
            pocketable_block_factory(
                account_id=account_a.account_id,
                amount=10000
            )
        )
        # Empty representative is used if no representative is set
        # for the account
        assert account_a.blocks[0].representative == \
            "xrb_1111111111111111111111111111111111111111111111111111hifc8npp"

        account_b.receive_block(
            pocketable_block_factory(
                account_id=account_b.account_id,
                amount=1000
            )
        )
        # Account representative is used if available
        assert account_b.blocks[0].representative == \
            "xrb_1e9dxacspemqghwwt4mzwtasdis43ny7topxuntuserzwi5xmx671erpjs4u"

        # If no account representative is available, but the account
        # blockchain has at least one block, use the representative
        # for the latest block
        account_b.representative = None
        account_b.receive_block(
            pocketable_block_factory(
                account_id=account_b.account_id,
                amount=1000
            )
        )

        assert account_b.blocks[1].representative == \
            "xrb_1e9dxacspemqghwwt4mzwtasdis43ny7topxuntuserzwi5xmx671erpjs4u"

    def test_wallet_refill_accounts(self, wallet):
        # Default gap limit is 20, so there should be 20 accounts
        assert len([
            account for account in wallet.accounts
            if account.source == AccountSource.SEED
        ]) == 20

        # Increase gap limit and refill accounts
        wallet.properties.gap_limit = 30
        wallet.refill_accounts()

        assert len([
            account for account in wallet.accounts
            if account.source == AccountSource.SEED
        ]) == 30

        # Decrease gap limit and refill accounts
        # Nothing should happen
        wallet.properties.gap_limit = 10
        wallet.refill_accounts()

        assert len([
            account for account in wallet.accounts
            if account.source == AccountSource.SEED
        ]) == 30

    def test_wallet_refill_accounts_regenerate_missing(self, wallet):
        wallet.properties.gap_limit = 5
        while wallet.accounts:  # Remove existing accounts
            wallet.remove_account(wallet.accounts[0])

        wallet.refill_accounts()

        # Seed account should be generated in order
        assert [acc.seed_index for acc in wallet.accounts] == [0, 1, 2, 3, 4]

        # Remove an account in the middle and ensure it is generated again
        wallet.remove_account(wallet.accounts[2])
        wallet.refill_accounts()

        # The regenerated account will be appended at the end
        assert [acc.seed_index for acc in wallet.accounts] == [0, 1, 3, 4, 2]

    def test_wallet_add_account_from_private_key(self, wallet):
        # Add a spendable account using a private key
        account = wallet.add_account_from_private_key(private_key="1"*64)
        assert len(wallet.accounts) == 21

        assert account.account_id == \
            "xrb_3d78japo7ziqqcsptk47eonzwzwjyaydcywq5ebzowjpxgyehynnjc9pd5zj"
        assert account.source == AccountSource.PRIVATE_KEY
        assert account.public_key == \
            "aca68a2d52fe17bab36d48456569fe7f91f23cb57b971b13faf236ebbcc7fa94"

        # Same private key can't be added twice
        with pytest.raises(AccountAlreadyExists):
            wallet.add_account_from_private_key(private_key="1"*64)

        with pytest.raises(InvalidPrivateKey):
            wallet.add_account_from_private_key("invalid")

        account_id = \
            "xrb_1x1cg4dgaop8i5gksrsrj891mmrzrqz7r37r48ocrnqkypqph3pbtgtk8whz"
        private_key = \
            "142a67048c4e0def1fdf3234d17b844a619c9f6dca1fde97b9e0225980f1d7a5"

        # A watching account will be updated if the same account is added
        # using a private key
        wallet.add_account_from_account_id(account_id)
        assert wallet.account_map[account_id].source == AccountSource.WATCHING

        wallet.add_account_from_private_key(private_key)
        assert wallet.account_map[account_id].source == \
            AccountSource.PRIVATE_KEY
        assert wallet.account_map[account_id].private_key

    def test_wallet_add_account_from_account_id(self, wallet):
        # Add a watching-only account using the account ID
        account = wallet.add_account_from_account_id(
            account_id="xrb_3d78japo7ziqqcsptk47eonzwzwjyaydcywq5ebzowjpxgyehynnjc9pd5zj"
        )
        assert len(wallet.accounts) == 21

        assert account.account_id == \
            "xrb_3d78japo7ziqqcsptk47eonzwzwjyaydcywq5ebzowjpxgyehynnjc9pd5zj"
        assert account.source == AccountSource.WATCHING
        assert account.public_key == \
            "aca68a2d52fe17bab36d48456569fe7f91f23cb57b971b13faf236ebbcc7fa94"
        assert not account.private_key

        with pytest.raises(InvalidAccount):
            wallet.add_account_from_account_id(account_id="invalid")

    def test_wallet_add_account(self, wallet, watching_account_factory):
        with pytest.raises(TypeError) as exc:
            wallet.add_account(
                "xrb_3d78japo7ziqqcsptk47eonzwzwjyaydcywq5ebzowjpxgyehynnjc9pd5zj")

        assert "Parameter isn't an Account instance" in str(exc.value)

        # Try adding the same account twice
        account = watching_account_factory()
        wallet.add_account(account)

        with pytest.raises(AccountAlreadyExists):
            wallet.add_account(account)

        account = watching_account_factory()

        # The representative should be set to the representative defined
        # in wallet properties if one isn't set in the Account instance
        # itself
        wallet.properties.representative = \
            "xrb_1iwamgozb5ckj9zzojbnb79485dfiw8jegedzwzuzy5b4a19cbs8b4tsdzo3"
        account.representative = None
        wallet.add_account(account)

        assert account.representative == \
            "xrb_1iwamgozb5ckj9zzojbnb79485dfiw8jegedzwzuzy5b4a19cbs8b4tsdzo3"

        # If account already has its own representative, it will be retained
        # instead
        account = watching_account_factory()
        account.representative = \
            "xrb_3d78japo7ziqqcsptk47eonzwzwjyaydcywq5ebzowjpxgyehynnjc9pd5zj"
        wallet.add_account(account)

        assert account.representative == \
            "xrb_3d78japo7ziqqcsptk47eonzwzwjyaydcywq5ebzowjpxgyehynnjc9pd5zj"

    def test_wallet_remove_account(self, wallet, watching_account_factory):
        account = watching_account_factory()
        wallet.add_account(account)

        wallet.remove_account(account)

        assert account.account_id not in wallet.account_map
        assert account not in wallet.accounts

        # Account can't be removed twice
        with pytest.raises(KeyError) as exc:
            wallet.remove_account(account)

        assert "Account not in the wallet" in str(exc.value)

    def test_wallet_add_transaction(self, wallet):
        account_id = \
            "xrb_3d78japo7ziqqcsptk47eonzwzwjyaydcywq5ebzowjpxgyehynnjc9pd5zj"
        tx = Transaction(
            txid="a transaction",
            account_id=account_id,
            block_hash="a"*64
        )

        wallet.add_transaction(tx)

        assert wallet.transaction_map[tx.txid] == tx

        # Same transaction can't be added twice
        with pytest.raises(TransactionAlreadyExists):
            wallet.add_transaction(tx)

    def test_wallet_remove_transaction(self, wallet):
        account_id = \
            "xrb_3d78japo7ziqqcsptk47eonzwzwjyaydcywq5ebzowjpxgyehynnjc9pd5zj"
        tx = Transaction(
            txid="a transaction",
            account_id=account_id,
            block_hash="a"*64
        )

        wallet.add_transaction(tx)
        assert tx.txid in wallet.transaction_map

        wallet.remove_transaction(tx)
        assert tx.txid not in wallet.transaction_map

        with pytest.raises(KeyError) as exc:
            wallet.remove_transaction(tx)

        assert "Transaction not in the wallet" in str(exc.value)

    def test_wallet_get_work_units_to_solve(
            self, wallet, pocketable_block_factory):
        # Test that 'get_work_units_to_solve' returns a list of work units
        # that haven't been finished yet
        for i in range(0, 10):
            account = wallet.accounts[i]
            for _ in range(0, 5):
                wallet.accounts[i].receive_block(
                    pocketable_block_factory(
                        account_id=account.account_id,
                        amount=10000
                    )
                )

        # Complete work for some of the blocks
        blocks_to_complete = [
            wallet.accounts[0].blocks[0],
            wallet.accounts[0].blocks[2],
            wallet.accounts[2].blocks[0],
            wallet.accounts[2].blocks[1],
            wallet.accounts[5].blocks[4]
        ]
        block_hashes = [
            block.block_hash for block in blocks_to_complete
        ]

        for block in blocks_to_complete:
            block.solve_work(difficulty=TEST_DIFFICULTY)

        work_units = wallet.get_work_units_to_solve(
            work_difficulty=TEST_DIFFICULTY
        )

        # 55 should be returned, as 5 already have valid work
        assert len(work_units) == 55
        assert len([
            work_unit for work_unit in work_units
            if work_unit.block_hash not in block_hashes
        ]) == 55

        # 10 should be for precomputed work units
        assert len([
            work_unit for work_unit in work_units
            if not work_unit.block_hash and work_unit.work_block_hash
        ]) == 10

    def test_wallet_update_solved_blocks(
            self, wallet, pocketable_block_factory):
        # Create 50 unsolved blocks and solve 5 of them, ensuring they're
        # updated correctly
        for i in range(0, 10):
            account = wallet.accounts[i]
            for _ in range(0, 5):
                wallet.accounts[i].receive_block(
                    pocketable_block_factory(
                        account_id=account.account_id,
                        amount=10000
                    )
                )

        # Complete work for some of the blocks
        block_hashes_to_solve = [
            wallet.accounts[0].blocks[0].block_hash,
            wallet.accounts[0].blocks[2].block_hash,
            wallet.accounts[2].blocks[0].block_hash,
            wallet.accounts[2].blocks[1].block_hash,
            wallet.accounts[5].blocks[4].block_hash
        ]
        solved_work_units = wallet.get_work_units_to_solve(TEST_DIFFICULTY)
        solved_work_units = [
            work_unit for work_unit in solved_work_units
            if work_unit.block_hash in block_hashes_to_solve
        ]

        for work_unit in solved_work_units:
            work_unit.difficulty = TEST_DIFFICULTY
            work_unit.solve_work()

        # Check that there are 60 work units to solve before update
        # 50 for blocks and 10 precomputed PoWs
        assert len(wallet.get_work_units_to_solve(TEST_DIFFICULTY)) == 60

        # and 55 after updating
        wallet.update_solved_blocks(solved_work_units)
        assert len(wallet.get_work_units_to_solve(TEST_DIFFICULTY)) == 55

    def test_wallet_update_solved_blocks_precomputed_work(
            self, wallet, pocketable_block_factory):
        # Empty accounts won't get precomputed work
        assert len(wallet.get_work_units_to_solve(TEST_DIFFICULTY)) == 0

        account = wallet.accounts[0]
        account.receive_block(
            pocketable_block_factory(
                account_id=account.account_id,
                amount=10000
            )
        )

        assert len(wallet.get_work_units_to_solve(TEST_DIFFICULTY)) == 2
        assert len(
            wallet.get_work_units_to_solve(
                TEST_DIFFICULTY, precompute_work=False
            )
        ) == 1

        work_units = wallet.get_work_units_to_solve(TEST_DIFFICULTY)
        for work_unit in work_units:
            work_unit.difficulty = to_hex(10000, 16)
            work_unit.solve_work()

        wallet.update_solved_blocks(work_units)

        # Precomputed work should now exist
        assert account.precomputed_work

        work = account.precomputed_work.work

        # Precomputed work will be used when adding a new block
        account.receive_block(
            pocketable_block_factory(
                account_id=account.account_id,
                amount=20000
            )
        )

        assert account.blocks[-1].work == work
        assert not account.precomputed_work

    def test_wallet_get_blocks_to_broadcast(
            self, wallet, account_factory):
        # Create four accounts with 5 blocks each
        # Add work for select blocks and ensure correct blocks are
        # selected for broadcasting
        for _ in range(0, 4):
            wallet.add_account(
                account_factory(
                    10000, block_count=5, complete=True, confirm=False
                )
            )

        # For 1st account, 1st block is complete (broadcast 1st)
        # For 2nd account, 2nd block is complete (broadcast nothing)
        # For 3rd account, 1st and 3rd blocks are complete (broadcast 1st)
        # For 4th account, 1st, 2nd and 4th blocks are complete
        #                  (broadcast 1st and 2nd)
        account_a = wallet.accounts[20]
        account_a.blocks[1].work = None
        account_a.blocks[2].work = None
        account_a.blocks[3].work = None
        account_a.blocks[4].work = None

        account_b = wallet.accounts[21]
        account_b.blocks[0].work = None
        account_b.blocks[2].work = None
        account_b.blocks[3].work = None
        account_b.blocks[4].work = None

        account_c = wallet.accounts[22]
        account_c.blocks[1].work = None
        account_c.blocks[3].work = None
        account_c.blocks[4].work = None

        account_d = wallet.accounts[23]
        account_d.blocks[2].work = None
        account_d.blocks[4].work = None

        broadcast_block_hashes = [
            account_a.blocks[0].block_hash,
            account_c.blocks[0].block_hash,
            account_d.blocks[0].block_hash,
            account_d.blocks[1].block_hash
        ]

        for account in wallet.accounts:
            account.update_confirmed_head()

        blocks_to_broadcast = wallet.get_blocks_to_broadcast()

        assert len(blocks_to_broadcast) == 4
        for i in range(0, 4):
            assert blocks_to_broadcast[i].block_hash == broadcast_block_hashes[i]

    def test_wallet_update_pocketable_blocks(
            self, wallet, legacy_pocketable_block_factory,
            pocketable_block_factory):
        account = wallet.accounts[0]

        link_block_a = legacy_pocketable_block_factory(
            account_id=account.account_id,
            amount=5000
        )
        link_block_b = pocketable_block_factory(
            account_id=account.account_id,
            amount=10000
        )

        wallet.update_pocketable_blocks([
            link_block_a, link_block_b
        ])
        block_a, block_b = account.blocks

        assert account.balance == 15000
        assert block_a.link_block.block_hash == link_block_a.block_hash
        assert block_b.link_block.block_hash == link_block_b.block_hash

    def test_wallet_update_broadcast_blocks(
            self, wallet, account_factory):
        for _ in range(0, 2):
            wallet.add_account(
                account_factory(
                    10000, block_count=5, complete=True, confirm=True
                )
            )

        account_a = wallet.accounts[20]
        account_a.confirmed_head = None
        account_a.blocks[4].confirmed = False

        account_a.update_confirmed_head()

        account_b = wallet.accounts[21]
        account_b.confirmed_head = None
        account_b.blocks[3].confirmed = False
        account_b.blocks[4].confirmed = False

        account_b.update_confirmed_head()

        broadcast_blocks = [
            copy.deepcopy(account_a.blocks[4]),
            copy.deepcopy(account_b.blocks[3]),
            copy.deepcopy(account_b.blocks[4])
        ]

        # 3 blocks to broadcast
        assert len(wallet.get_blocks_to_broadcast()) == 3

        # After update, no blocks left to broadcast
        wallet.update_broadcast_blocks(broadcast_blocks)
        assert len(wallet.get_blocks_to_broadcast()) == 0

    def test_update_processed_blocks(self, wallet, account_factory):
        account = account_factory(balance=10000, block_count=4, complete=True)
        blocks = account.blocks

        # Add the account with only the first block pre-existing
        account = Account(
            account_id=account.account_id,
            source=account.source,
            blocks=[blocks[0]]
        )
        wallet.add_account(account)

        assert not account.blocks[0].confirmed
        assert not account.confirmed_head

        # Process the first block; it should be confirmed
        # Make copies of blocks as we add them to be processed.
        # Blocks entered into the network plugin's queues are copied
        # to prevent the blocks in the Account instance from being
        # inadvertedly modified
        wallet.update_processed_blocks([
            BlockSyncResult(block=copy.deepcopy(blocks[0]), confirmed=True)
        ])
        assert len(account.blocks) == 1
        assert account.blocks[0].confirmed
        assert account.confirmed_head == account.blocks[0]

        # Process the next two blocks, they should be added and confirmed
        wallet.update_processed_blocks([
            BlockSyncResult(block=copy.deepcopy(blocks[1]), confirmed=True),
            BlockSyncResult(block=copy.deepcopy(blocks[2]), confirmed=True)
        ])
        assert len(account.blocks) == 3
        assert account.blocks[1].confirmed
        assert account.blocks[2].confirmed
        assert account.confirmed_head == account.blocks[2]

        # Try rejecting the third block;
        # which can't be removed after confirmation.
        with pytest.raises(ValueError) as exc:
            wallet.update_processed_blocks([
                BlockSyncResult(block=copy.deepcopy(blocks[2]), rejected=True)
            ])

        assert "Can't reject a confirmed block" in str(exc.value)

        # Reject the fourth block, which can be removed since it isn't
        # confirmed
        account.add_block(blocks[3])
        assert not account.blocks[3].confirmed

        wallet.update_processed_blocks([
            BlockSyncResult(block=copy.deepcopy(blocks[3]), rejected=True)
        ])

        assert len(account.blocks) == 3
        assert account.confirmed_head == account.blocks[2]

    @pytest.mark.parametrize("encrypt_wallet", [True, False])
    def test_wallet_is_wallet_file_valid(
            self, encrypt_wallet, wallet_factory, wallet_path):
        wallet = wallet_factory()
        wallet.change_passphrase(
            passphrase="password",
            encrypt_wallet=encrypt_wallet,
            encrypt_secrets=False
        )
        wallet.save(wallet_path)

        assert Wallet.is_wallet_file_valid(wallet_path)

    @pytest.mark.parametrize(
        "content",
        ["{}", "invalid json"]
    )
    def test_wallet_is_wallet_file_valid_invalid_content(
            self, wallet_path, content):
        with open(wallet_path, "w+") as f:
            f.write(content)

        assert not Wallet.is_wallet_file_valid(wallet_path)

    @pytest.mark.parametrize(
        "encrypt_wallet,encrypt_secrets",
        [(True, False), (False, True), (True, True), (False, False)]
    )
    def test_wallet_is_wallet_file_encrypted(
            self, encrypt_wallet, encrypt_secrets, wallet_factory,
            wallet_path):
        wallet = wallet_factory(balance=1000, confirmed=True)
        wallet.change_passphrase(
            passphrase="password",
            encrypt_wallet=encrypt_wallet,
            encrypt_secrets=encrypt_secrets,
        )
        wallet.save(wallet_path)

        assert Wallet.is_wallet_file_encrypted(wallet_path) == encrypt_wallet


class TestWalletEncryption:
    def test_wallet_encrypt_secrets(
            self, wallet, account_factory):
        for _ in range(0, 4):
            wallet.add_account(
                account_factory(balance=10000)
            )

        # Encrypt the wallet
        wallet.change_passphrase(
            "password", encrypt_secrets=True, encrypt_wallet=False)

        # Ensure everything is encrypted
        assert isinstance(wallet.properties.seed, Secret)
        for account in wallet.accounts:
            assert isinstance(account.private_key, Secret)

        # Check the keys are in place
        assert wallet.secret_key
        assert not wallet.wallet_key

        assert wallet.encryption.secrets_encrypted
        assert not wallet.encryption.wallet_encrypted

        # Remove the encryption
        wallet.change_passphrase(
            None, encrypt_secrets=False, encrypt_wallet=False)

        assert isinstance(wallet.properties.seed, str)
        for account in wallet.accounts:
            assert isinstance(account.private_key, str)

        assert not wallet.secret_key
        assert not wallet.wallet_key

        assert not wallet.encryption.secrets_encrypted
        assert not wallet.encryption.wallet_encrypted

    def test_wallet_set_secret_encryption(self, wallet):
        SECRET_KEY_A = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
        SECRET_KEY_B = "MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE="

        seed = wallet.properties.seed

        wallet.set_secret_encryption(SECRET_KEY_A)
        assert wallet.encryption.secrets_encrypted
        assert \
            wallet.properties.get_secret("seed", secret_key=SECRET_KEY_A) \
            == seed

        wallet.set_secret_encryption(SECRET_KEY_B)
        assert wallet.encryption.secrets_encrypted
        assert \
            wallet.properties.get_secret("seed", secret_key=SECRET_KEY_B) \
            == seed

        # Can't encrypt again with the same key
        with pytest.raises(ValueError) as exc:
            wallet.set_secret_encryption(SECRET_KEY_B)

        assert "is already encrypted with this key" in str(exc.value)

    def test_wallet_ensure_secrets_unlocked(self, encrypted_wallet):
        wallet = encrypted_wallet

        wallet.properties.gap_limit = 25

        # Wallet is unlocked, so this will work
        wallet.refill_accounts()
        assert len(wallet.accounts) == 25

        # Lock the account and try again
        wallet.lock()
        wallet.properties.gap_limit = 30

        with pytest.raises(WalletLocked) as exc:
            wallet.refill_accounts()

        assert "The wallet secrets have to be unlocked" in str(exc.value)

    def test_wallet_unlock(self, encrypted_wallet):
        wallet = encrypted_wallet
        wallet.lock()

        # Unlock with correct passphrase
        wallet.unlock(passphrase="password")
        wallet.lock()

        # Try unlocking with the wrong passphrase
        with pytest.raises(InvalidEncryptionKey) as exc:
            wallet.unlock(passphrase="wrong")

        assert "Incorrect passphrase" in str(exc.value)

    def test_wallet_save_secrets(self, wallet, tmp_path):
        # Encrypt only the secrets
        wallet_path = tmp_path / "test.nanowallet"

        wallet.change_passphrase(
            "password", encrypt_secrets=True, encrypt_wallet=False)
        wallet.save(path=wallet_path)

        with open(wallet_path, "r") as f:
            wallet_data = json.load(f)

        assert wallet_data["properties"]["seed"].get("_enc", False)

        for account in wallet_data["accounts"]:
            assert account["private_key"].get("_enc", False)

    def test_wallet_save_encrypted_wallet(self, wallet, tmp_path):
        # Encrypt everything
        wallet_path = tmp_path / "test.nanowallet"

        wallet.change_passphrase(
            passphrase="password", encrypt_secrets=True, encrypt_wallet=True)
        wallet.save(path=wallet_path)

        with open(wallet_path, "r") as f:
            wallet_data = json.load(f)

        assert not wallet_data.get("properties", None)
        assert wallet_data["wallet_data"].get("_enc", False)
        assert wallet_data["key_iteration_count"] > 0
        assert wallet_data.get("secrets_encrypted", None) is None
        assert wallet_data.get("secret_checksum", None) is None

    def test_wallet_load_secrets(self):
        # Load wallet with only encrypted secrets
        # Passphrase not required
        wallet = Wallet.load(SECRETS_ENCRYPTED_WALLET_PATH)
        assert not wallet.wallet_key
        assert not wallet.secret_key

        assert isinstance(wallet.properties.seed, Secret)
        for account in wallet.accounts:
            assert isinstance(account.private_key, Secret)

    def test_wallet_load_encrypted_wallet(self):
        # Load wallet which has been encrypted entirely
        # Passphrase required
        with pytest.raises(WalletLocked) as exc:
            Wallet.load(BOTH_ENCRYPTED_WALLET_PATH)

        assert "Wallet is encrypted but passphrase was not provided" in str(exc.value)

        # Wrong passphrase
        with pytest.raises(InvalidEncryptionKey) as exc:
            Wallet.load(BOTH_ENCRYPTED_WALLET_PATH, passphrase="wrong")

        assert "Incorrect passphrase" in str(exc.value)

        # Correct passphrase
        wallet = Wallet.load(BOTH_ENCRYPTED_WALLET_PATH, passphrase="password")
        assert wallet.wallet_key
        assert not wallet.secret_key

        assert isinstance(wallet.properties.seed, Secret)

        for account in wallet.accounts:
            assert isinstance(account.private_key, Secret)

    def test_wallet_change_passphrase_empty(self, wallet):
        # Encryption can't be done with an empty passphrase
        with pytest.raises(ValueError) as exc:
            wallet.change_passphrase(
                passphrase="", encrypt_secrets=True, encrypt_wallet=False)

        assert "Passphrase has to be non-empty" in str(exc.value)

    def test_wallet_remove_secret_encryption(self, encrypted_wallet):
        wallet = encrypted_wallet
        wallet.remove_encryption()

        assert not wallet.secret_key
        assert not wallet.encryption.secrets_encrypted

        assert isinstance(wallet.properties.seed, str)
        for account in wallet.accounts:
            assert isinstance(account.private_key, str)
