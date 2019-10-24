import pytest
import json
import copy

from siliqua.server import WalletServer
from siliqua.wallet import Account, AccountSource, Block, LinkBlock
from siliqua.wallet.secret import Secret
from siliqua.ui.stdio import logger

from tests.util import hook


class TestCreateWallet:
    def test_create_wallet_non_encrypted(
            self, stdio, wallet_path, wallet_loader):
        result = stdio(["create-wallet", str(wallet_path)], success=True)
        assert "Saved wallet" in result["data"]["message"]
        assert "test.wallet" in result["data"]["message"]
        assert not result["data"]["wallet_encrypted"]
        assert not result["data"]["secrets_encrypted"]

        wallet = wallet_loader(wallet_path)

        assert len(wallet.accounts) == 20
        assert isinstance(wallet.accounts[0].private_key, str)

    def test_create_wallet_existing_wallet(self, stdio, wallet_path):
        with open(wallet_path, "w") as f:
            f.write("I exist")

        result = stdio(["create-wallet", str(wallet_path)], success=False)
        assert result["data"]["error"] == "wallet_exists"

    def test_create_wallet_seed(self, stdio, wallet_path, wallet_loader):
        stdio(
            ["create-wallet", str(wallet_path)],
            env={"SEED": "2df7255d3a93ebb8c8efb06f98a49064c9f8fdf1a0caf0ab579456c7f4db1bd7"}
        )

        wallet = wallet_loader(wallet_path)
        assert wallet.properties.seed == \
            "2df7255d3a93ebb8c8efb06f98a49064c9f8fdf1a0caf0ab579456c7f4db1bd7"

    def test_create_wallet_gap_limit(self, stdio, wallet_path, wallet_loader):
        stdio(
            ["create-wallet", str(wallet_path), "--gap-limit", "50"]
        )

        wallet = wallet_loader(wallet_path)

        assert wallet.properties.gap_limit == 50
        assert len(wallet.accounts) == 50

    def test_create_wallet_invalid_seed(self, stdio, wallet_path):
        result = stdio(
            ["create-wallet", str(wallet_path)],
            env={"SEED": "invalid"},
            success=False
        )

        assert result["data"]["error"] == "invalid_seed"

    def test_create_wallet_encrypt(
            self, stdio, wallet_path, wallet_loader):
        result = stdio(
            ["create-wallet", str(wallet_path), "--encrypt-secrets"],
            env={"PASSPHRASE": "test_password"}
        )

        assert result["data"]["secrets_encrypted"]
        assert not result["data"]["wallet_encrypted"]

        wallet = wallet_loader(wallet_path)

        assert wallet.encryption.secrets_encrypted
        assert not wallet.encryption.wallet_encrypted

        wallet.unlock("test_password")

    def test_create_wallet_encrypt_key_iteration_count(
            self, stdio, wallet_path, wallet_loader):
        stdio(
            [
                "create-wallet", str(wallet_path), "--encrypt-secrets",
                "--key-iteration-count", "25000"
            ],
            env={"PASSPHRASE": "test_password"}
        )

        wallet = wallet_loader(wallet_path)

        assert wallet.encryption.key_iteration_count == 25000

    def test_create_wallet_encrypt_no_passphrase(
            self, stdio, wallet_path):
        result = stdio(
            ["create-wallet", str(wallet_path), "--encrypt-secrets"],
            success=False
        )

        assert result["data"]["error"] == "missing_passphrase"


class TestCalculateKeyIterationCount:
    def test_calculate_key_iteration_count(self, stdio):
        result = stdio(["calculate-key-iteration-count", "0.5"])

        assert result["data"]["seconds"] == pytest.approx(0.5)

        assert result["data"]["key_iteration_count"] > 0
        assert isinstance(result["data"]["key_iteration_count"], int)


class TestChangeEncryption:
    def test_change_encryption(self, stdio, wallet_path, wallet_loader):
        # Change wallet's encryption from secrets encrypted to
        # secrets + wallet encrypted, and change the passphrase at the same
        # time
        stdio(
            ["create-wallet", str(wallet_path), "--encrypt-secrets"],
            env={"PASSPHRASE": "test_password"}
        )
        result = stdio(
            [
                "--wallet", str(wallet_path), "change-encryption",
                "--encrypt-secrets", "--encrypt-wallet"
            ],
            env={
                "PASSPHRASE": "test_password",
                "NEW_PASSPHRASE": "test_password2"
            }
        )

        assert "Encryption changed" in result["data"]["message"]

        wallet = wallet_loader(wallet_path, passphrase="test_password2")

        assert wallet.encryption.secrets_encrypted
        assert wallet.encryption.wallet_encrypted

    def test_change_encryption_missing_passphrase(self, stdio, wallet_path):
        stdio(
            ["create-wallet", str(wallet_path)],
        )
        result = stdio(
            [
                "--wallet", str(wallet_path), "change-encryption",
                "--encrypt-secrets", "--encrypt-wallet"
            ],
            success=False
        )

        assert result["data"]["error"] == "missing_passphrase"

    def test_change_encryption_incorrect_passphrase(self, stdio, wallet_path):
        # Try to change encryption with an incorrect passphrase
        stdio(
            ["create-wallet", str(wallet_path), "--encrypt-wallet"],
            env={"PASSPHRASE": "password"}
        )
        result = stdio(
            [
                "--wallet", str(wallet_path), "change-encryption",
                "--encrypt-secrets"
            ],
            env={"PASSPHRASE": "incorrect", "NEW_PASSPHRASE": "new"},
            success=False
        )

        assert result["data"]["error"] == "incorrect_passphrase"

    def test_change_encryption_key_iteration_count(
            self, stdio, wallet_path, wallet_loader):
        stdio(
            ["create-wallet", str(wallet_path), "--encrypt-wallet"],
            env={"PASSPHRASE": "password"}
        )
        stdio(
            [
                "--wallet", str(wallet_path), "change-encryption",
                "--encrypt-secrets", "--key-iteration-count", "25000"
            ],
            env={"PASSPHRASE": "password", "NEW_PASSPHRASE": "password"},
        )

        wallet = wallet_loader(wallet_path)
        assert wallet.encryption.key_iteration_count == 25000


@pytest.mark.add_encrypted_test
class TestGetWalletSeed:
    def test_get_wallet_seed(
            self, stdio, wallet_path, wallet_factory, wallet_loader,
            is_encrypted_test):
        wallet = wallet_factory(balance=10000)

        if is_encrypted_test:
            wallet.unlock("password")
            seed = wallet.properties.get_secret(
                "seed", secret_key=wallet.secret_key
            )
            wallet.lock()
        else:
            seed = wallet.properties.seed

        wallet.save(wallet_path)

        result = stdio(["--wallet", wallet_path, "get-wallet-seed"])

        assert result["data"]["seed"] == seed

    def test_get_wallet_seed_no_seed(
            self, stdio, wallet_path, wallet_factory, wallet_loader):
        wallet = wallet_factory()

        wallet.properties.seed = None
        wallet.properties.seed_algorithm = None
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "get-wallet-seed"
        ], success=False)

        assert result["data"]["error"] == "seed_required"


@pytest.mark.add_encrypted_test
class TestGetBalance:
    def test_get_balance(
            self, stdio, wallet_path, empty_wallet, wallet_loader,
            account_factory):
        wallet = empty_wallet

        account_a = account_factory(balance=1000, complete=True, confirm=True)
        account_b = account_factory(balance=2000, complete=True, confirm=False)
        account_b.name = "Test account"

        # A watching-only account
        account_c = account_factory(balance=4000, complete=True, confirm=True)

        account_c.private_key = None
        account_c.source = AccountSource.WATCHING

        wallet.add_account(account_a)
        wallet.add_account(account_b)
        wallet.add_account(account_c)

        wallet.save(wallet_path)

        result = stdio(["--wallet", wallet_path, "get-balance"])
        data = result["data"]

        assert data["spendable_balance"] == "3000"
        assert data["unspendable_balance"] == "4000"

        assert data["accounts"][account_a.account_id]["spendable"]
        assert data["accounts"][account_a.account_id]["balance"] == "1000"

        assert data["accounts"][account_b.account_id]["name"] == \
            "Test account"

        assert not data["accounts"][account_c.account_id]["spendable"]
        assert data["accounts"][account_c.account_id]["balance"] == "4000"


@pytest.mark.add_encrypted_test
class TestAddAccount:
    def test_add_account_from_account_id(
            self, stdio, wallet_path, zero_balance_wallet, wallet_loader):
        wallet = zero_balance_wallet
        wallet.save(wallet_path)

        account_id = \
            "xrb_175rc45en4483h9dr6h6s73rpard9rpnbnmu1zsgex3s9mmqft7he1yw65jx"

        result = stdio([
            "--wallet", str(wallet_path), "add-account",
            "--account-id", account_id
        ])

        assert result["data"]["account_id"] == account_id

        wallet = wallet_loader(wallet_path)
        assert wallet.account_map[account_id].account_id == account_id
        assert wallet.account_map[account_id].source == AccountSource.WATCHING

    def test_add_account_from_public_key(
            self, stdio, wallet_path, zero_balance_wallet, wallet_loader):
        wallet = zero_balance_wallet
        wallet.save(wallet_path)

        public_key = \
            "2f532af1013ea8f17832f7ea509314160a55027014102be5dd5bbd2bc119b32d"
        account_id = \
            "xrb_1dtm7dri4hoay7w57xzcc4bja7iccn39171i7hkxtpxx7h1jmesfnq9risht"

        result = stdio([
            "--wallet", str(wallet_path), "add-account",
            "--public-key", public_key
        ])

        assert result["data"]["account_id"] == account_id

        wallet = wallet_loader(wallet_path)
        assert wallet.account_map[account_id].account_id == account_id
        assert wallet.account_map[account_id].source == AccountSource.WATCHING

    def test_add_account_from_private_key(
            self, stdio, wallet_path, zero_balance_wallet, wallet_loader,
            is_encrypted_test):
        wallet = zero_balance_wallet
        wallet.save(wallet_path)

        private_key = \
            "60611eb404754617f5dd72a9d2dcc3408bc77cca912ce4cab57b54e9c2e3152a"
        account_id = \
            "xrb_3eh3jd5ykeub88rstdbakhp331rjhuxyh4jdza6rc14p6uzzr6e33trwikpy"

        result = stdio([
            "--wallet", str(wallet_path), "add-account"
        ], env={"PRIVATE_KEY": private_key})

        assert result["data"]["account_id"] == account_id

        wallet = wallet_loader(wallet_path)
        assert wallet.account_map[account_id].account_id == account_id
        assert wallet.account_map[account_id].source == \
            AccountSource.PRIVATE_KEY

        if is_encrypted_test:
            assert isinstance(
                wallet.account_map[account_id].private_key, Secret
            )
        else:
            assert wallet.account_map[account_id].private_key == private_key

    def test_add_account_from_private_key_after_account_id(
            self, stdio, wallet_path, zero_balance_wallet, wallet_loader,
            is_encrypted_test):
        wallet = zero_balance_wallet
        wallet.save(wallet_path)

        private_key = \
            "60611eb404754617f5dd72a9d2dcc3408bc77cca912ce4cab57b54e9c2e3152a"
        account_id = \
            "xrb_3eh3jd5ykeub88rstdbakhp331rjhuxyh4jdza6rc14p6uzzr6e33trwikpy"

        stdio([
            "--wallet", wallet_path, "add-account", "--account-id",
            account_id
        ])
        result = stdio([
            "--wallet", wallet_path, "add-account"
        ], env={"PRIVATE_KEY": private_key})

        assert result["data"]["account_id"] == account_id

        wallet = wallet_loader(wallet_path)
        assert wallet.account_map[account_id].account_id == account_id
        assert wallet.account_map[account_id].source == \
            AccountSource.PRIVATE_KEY

        if is_encrypted_test:
            assert isinstance(
                wallet.account_map[account_id].private_key, Secret
            )
        else:
            assert wallet.account_map[account_id].private_key == private_key

    def test_add_account_duplicate(
            self, stdio, wallet_path, zero_balance_wallet, wallet_loader):
        wallet = zero_balance_wallet
        wallet.save(wallet_path)

        account_id = \
            "xrb_3eh3jd5ykeub88rstdbakhp331rjhuxyh4jdza6rc14p6uzzr6e33trwikpy"

        args = [
            "--wallet", str(wallet_path), "add-account", "--account-id",
            account_id
        ]
        stdio(args)

        # Trying to add account twice causes an error
        result = stdio(args, success=False)

        assert result["data"]["error"] == "account_already_exists"

    def test_add_account_multiple_args(
            self, stdio, wallet_path, zero_balance_wallet, wallet_loader):
        wallet = zero_balance_wallet
        wallet.save(wallet_path)

        private_key = \
            "60611eb404754617f5dd72a9d2dcc3408bc77cca912ce4cab57b54e9c2e3152a"
        account_id = \
            "xrb_3eh3jd5ykeub88rstdbakhp331rjhuxyh4jdza6rc14p6uzzr6e33trwikpy"

        result = stdio([
            "--wallet", wallet_path, "add-account", "--account-id",
            account_id
        ], env={"PRIVATE_KEY": private_key}, success=False)

        assert result["data"]["error"] == "one_parameter_required"


@pytest.mark.add_encrypted_test
class TestRemoveAccount:
    def test_remove_account(
            self, stdio, zero_balance_wallet, wallet_path, wallet_loader):
        wallet = zero_balance_wallet
        account_id = wallet.accounts[0].account_id
        wallet.save(wallet_path)

        assert len(wallet.accounts) == 20

        result = stdio([
            "--wallet", wallet_path, "remove-account", account_id
        ])

        assert result["data"]["account_id"] == account_id

        wallet = wallet_loader(wallet_path)

        assert account_id not in wallet.account_map
        assert len(wallet.accounts) == 19

    def test_remove_account_account_not_found(
            self, stdio, empty_wallet, wallet_path):
        empty_wallet.save(wallet_path)

        account_id = \
            "xrb_3eh3jd5ykeub88rstdbakhp331rjhuxyh4jdza6rc14p6uzzr6e33trwikpy"

        result = stdio([
            "--wallet", wallet_path, "remove-account", account_id
        ], success=False)

        assert result["data"]["error"] == "account_not_found"


@pytest.mark.add_encrypted_test
class TestGenerateAccount:
    def test_generate_account(
            self, stdio, zero_balance_wallet, wallet_path, wallet_loader):
        wallet = zero_balance_wallet
        assert len(wallet.accounts) == 20
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "generate-account"
        ])

        account_id = result["data"]["new_accounts"][0]

        wallet = wallet_loader(wallet_path)
        assert len(wallet.accounts) == 21
        assert wallet.accounts[20].account_id == account_id
        assert wallet.accounts[20].source == AccountSource.SEED

    def test_generate_account_count(
            self, stdio, zero_balance_wallet, wallet_path, wallet_loader):
        wallet = zero_balance_wallet
        assert len(wallet.accounts) == 20
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "generate-account", "--count", "5"
        ])

        new_account_ids = result["data"]["new_accounts"]

        wallet = wallet_loader(wallet_path)
        assert len(wallet.accounts) == 25
        assert wallet.accounts[20].account_id == new_account_ids[0]
        assert wallet.accounts[24].account_id == new_account_ids[4]

    def test_generate_account_seed_required(
            self, stdio, empty_wallet, wallet_path, wallet_loader):
        wallet = empty_wallet
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "generate-account"
        ], success=False)

        assert result["data"]["error"] == "seed_required"


@pytest.mark.add_encrypted_test
class TestSync:
    def test_sync_receive(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory,
            wallet_loader, pocketable_block_factory,
            legacy_pocketable_block_factory):
        wallet = wallet_factory(balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id_a = wallet.accounts[0].account_id
        account_id_b = wallet.accounts[1].account_id

        link_block_a = legacy_pocketable_block_factory(
            account_id=account_id_a,
            amount=2000)
        link_block_b = pocketable_block_factory(
            account_id=account_id_b,
            amount=4000)

        wallet_mock_node.add_pocketable_blocks([link_block_a, link_block_b])
        wallet_mock_node.start()

        result = stdio([
            "--wallet", str(wallet_path), "sync", "--timeout", "0"
        ])

        data = result["data"]

        assert len(data["new_blocks"]) == 2
        assert data["new_blocks"][account_id_a][0]["tx_type"] == "receive"
        assert data["new_blocks"][account_id_a][0]["amount"] == "2000"
        assert data["new_blocks"][account_id_a][0]["block_data"]["account"] \
            == account_id_a

        assert data["new_blocks"][account_id_b][0]["tx_type"] == "open"
        assert data["new_blocks"][account_id_b][0]["amount"] == "4000"
        assert data["new_blocks"][account_id_b][0]["block_data"]["account"] \
            == account_id_b

        assert len(data["received_blocks"]) == 2
        assert data["received_blocks"][account_id_a][0]["amount"] == "2000"
        assert data["received_blocks"][account_id_a][0]["source"] == \
            link_block_a.account

        assert data["received_blocks"][account_id_b][0]["amount"] == "4000"
        assert data["received_blocks"][account_id_b][0]["source"] == \
            link_block_b.account

        assert not data["rejected_blocks"]

        wallet = wallet_loader(wallet_path)

        assert len(wallet.accounts[0].blocks) == 2
        assert len(wallet.accounts[1].blocks) == 1

        # Account #0 has a balance of 12000
        # (10000 from wallet_factory and 2000 we just received)
        assert wallet.accounts[0].balance == 12000
        assert wallet.accounts[1].balance == 4000

    def test_sync_rejected(
            self, low_difficulty, mock_node, wallet_factory, wallet_loader, wallet_path,
            stdio):
        # Create a bare-bones wallet with only one account
        # This account contains one pending block which will be rejected
        wallet = wallet_factory(balance=0)
        wallet.properties.seed = None
        wallet.properties.seed_algorithm = None
        wallet.accounts = []
        wallet.add_account(
            Account(
                account_id="xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                source=AccountSource.WATCHING
            )
        )
        wallet.accounts[0].add_block(
            Block(
                block_data={
                    "account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                    "balance": "1000000000000000000000000000000",
                    "link": "82CDDC385108D25E520B9CB2C7CB539CDF2FD5C9C3D7F4992AB6E18D0135B85F",
                    "previous": "0000000000000000000000000000000000000000000000000000000000000000",
                    "representative": "xrb_3dmtrrws3pocycmbqwawk6xs7446qxa36fcncush4s1pejk16ksbmakis78m",
                    "signature": "043351B1248406BFF71D4F06F8BC53E988BC56CAD82484136C6A90E21D8A35A5A3A9EC6A99B6AD7F71605A4602CD6672E705B1F22EFA6DFDAD8E1E9A48209907",
                    "type": "state",
                    "work": "538a6fef558ffd93"
                },
                link_block=LinkBlock(
                    block_data={
                        "account": "xrb_11p7y8een13ggixxt1ruxz6cchposphsfpx9nxgjtyhrz64apesgnad9ot1x",
                        "previous": "4AF3568F9ADDC65302FEDBBF2BAD60FD2175D7E671DDA980D55AEA5D343D8BEA",
                        "representative": "xrb_1awsn43we17c1oshdru4azeqjz9wii41dy8npubm4rg11so7dx3jtqgoeahy",
                        "balance": "0",
                        "link": "5114AB75C910A20726BFD3E8A3B9335B1738F36D87F4D246EE5A2B91AEB0D8CC",
                        "link_as_account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                        "signature": "AB85B448F40F482AC24006F7A3A00D25211B2017CE498CE40728435A41124E4E678675C8D994D4FC4596607499C23470A9188DE4A011253F54F8ABC00457CD0B",
                        "work": "9d86cf7e0bb936a9",
                        "type": "state"
                    },
                    amount=1000000000000000000000000000000
                ),
                confirmed=True
            )
        )
        wallet.accounts[0].add_block(
            Block(
                block_data={
                    "account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                    "balance": "0",
                    "link": "7EB064709F33C1E93541D48CBCE68C833FF105D1F3F7A9EF6B34CB23A849AB53",
                    "previous": "E82CDC903E33AC80C2ACB6F3608FE9CFBDF610F11308F10CDDD8F6347F1CE058",
                    "representative": "xrb_3dmtrrws3pocycmbqwawk6xs7446qxa36fcncush4s1pejk16ksbmakis78m",
                    "signature": "505E3645F88CD37D4783A7242B8CF49BE9658E19576A17237B3F0BBF8A96249987596C9A65FA98BC904296BF0AB65EE3A9E5D48408A38ED30D9D474567083B0F",
                    "type": "state",
                    "work": "07ff830e5b022fbd"
                },
                confirmed=True
            )
        )
        wallet.accounts[0].add_block(
            Block(
                block_data={
                    "account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                    "previous": "96970559D7257F63ACB8383ED57CB510745DE744ABCEC4DC41590CE7E32179EA",
                    "representative": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                    "balance": "0",
                    "link": "0000000000000000000000000000000000000000000000000000000000000000",
                    "link_as_account": "xrb_1111111111111111111111111111111111111111111111111111hifc8npp",
                    "signature": "BBC27F177C2C2DD574AE8EB8523A1A504B5790C65C95ACE744E3033A63BB158DDF95F9B7B88B902C8D743A64EA25785662CD454044E9C3000BC79C3BF7F1E809",
                    "work": "561bab16393cb3c4",
                    "type": "state"
                },
                confirmed=False
            )
        )
        account_id = wallet.accounts[0].account_id

        wallet.save(wallet_path)

        mock_node.add_replay_datasets([
            "state_broadcast_failure_previous_missing",
            "active_difficulty", "version"
        ]).start()

        result = stdio([
            "--wallet", str(wallet_path), "sync", "--timeout", "0"
        ], success=False)
        data = result["data"]

        assert len(data["rejected_blocks"][account_id]) == 1
        assert data["rejected_blocks"][account_id][0]["hash"] == \
            "62EE070DA06632FE1E54BA32FD25B00A5FD4E8CF09354A9B176CBF6BC33CDBDB"
        assert data["rejected_blocks"][account_id][0]["block_error"] == \
            "previous_block_missing"

        assert data["error"] == "block_rejected"

        wallet = wallet_loader(wallet_path)

        # The rejected block was removed
        assert len(wallet.accounts[0].blocks) == 2

    def test_sync_finish_work(
            self, wallet_mock_node, wallet_factory, wallet_loader, wallet_path,
            account_factory, stdio):
        # Create a wallet with one account and 50 blocks to complete.
        # Ensure that with '--finish-work' flag set, all blocks have complete
        # PoW after the command has finished
        wallet = wallet_factory(balance=0)
        wallet.properties.seed = None
        wallet.properties.seed_algorithm = None
        wallet.accounts = []
        wallet.add_account(
            account_factory(balance=1000, block_count=50, complete=False)
        )
        assert not wallet.accounts[0].blocks[0].work

        wallet.save(wallet_path)

        wallet_mock_node.start()

        stdio([
            "--wallet", wallet_path, "sync", "--finish-work", "--timeout", "0"
        ])

        wallet = wallet_loader(wallet_path)

        for block in wallet.accounts[0].blocks[0:50]:
            assert block.work

    def test_sync_finish_sync(
            self, wallet_mock_node, wallet_factory, wallet_loader, wallet_path,
            account_factory, stdio):
        # Create a wallet with one account and 50 blocks to complete.
        # Ensure that with '--finish-sync' flag set, all blocks have been
        # confirmed after the command has finished
        wallet = wallet_factory(balance=0)
        wallet.properties.seed = None
        wallet.properties.seed_algorithm = None
        wallet.accounts = []
        wallet.add_account(
            account_factory(
                balance=1000, block_count=50, complete=True, confirm=False
            )
        )
        assert not wallet.accounts[0].blocks[0].confirmed

        wallet_mock_node.start()
        wallet.save(wallet_path)

        stdio([
            "--wallet", wallet_path, "sync", "--finish-sync", "--timeout", "0"
        ])

        wallet = wallet_loader(wallet_path)

        for block in wallet.accounts[0].blocks[0:50]:
            assert block.confirmed

    def test_sync_block_count(
            self, wallet_mock_node, wallet_factory, wallet_path,
            pocketable_block_factory, account_factory, stdio):
        wallet = wallet_factory(balance=0)
        wallet.properties.seed = None
        wallet.properties.seed_algorithm = None
        account_id = wallet.accounts[0].account_id

        link_blocks = [
            pocketable_block_factory(account_id=account_id, amount=2000)
            for _ in range(0, 20)
        ]
        link_block_hashes = [
            link_block.block_hash for link_block in link_blocks
        ]

        wallet_mock_node.add_pocketable_blocks(link_blocks)
        wallet_mock_node.start()

        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "sync", "--finish-sync", "--timeout", "0",
            "--result-count", "10"
        ])

        # Only the ten latest confirmed blocks are returned
        assert len(result["data"]["received_blocks"][account_id]) == 10
        assert [
            new_result["block_data"]["link"] for new_result
            in result["data"]["new_blocks"][account_id]
        ] == link_block_hashes[10:]

    def test_sync_empty_watching_only_pocketable(
            self, wallet_mock_node, wallet_factory, wallet_path,
            pocketable_block_factory, stdio):
        """
        Watching-only account that has pending pocketable blocks
        shouldn't stop the sync from completing
        """
        wallet = wallet_factory(balance=0)
        wallet.accounts = []
        wallet.save(wallet_path)

        stdio([
            "--wallet", wallet_path, "add-account", "--account-id",
            "xrb_3eh3jd5ykeub88rstdbakhp331rjhuxyh4jdza6rc14p6uzzr6e33trwikpy"
        ])

        link_block = pocketable_block_factory(
            account_id="xrb_3eh3jd5ykeub88rstdbakhp331rjhuxyh4jdza6rc14p6uzzr6e33trwikpy",
            amount=4000
        )

        wallet_mock_node.add_pocketable_blocks([link_block])
        wallet_mock_node.start()

        result = stdio([
            "--wallet", wallet_path, "sync", "--finish-sync", "--finish-work",
            "--timeout", "0"
        ])

        assert result["data"]["new_blocks"] == {}
        assert result["data"]["received_blocks"] == {}


@pytest.mark.add_encrypted_test
class TestSend:
    def test_send(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory,
            wallet_loader):
        wallet = wallet_factory(balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = wallet.accounts[0].account_id
        destination = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"

        wallet_mock_node.start()

        result = stdio([
            "--wallet", str(wallet_path), "send",
            account_id, destination, "6000"
        ])

        wallet = wallet_loader(wallet_path)

        block = wallet.accounts[0].blocks[-1]
        assert block.confirmed
        assert block.link_as_account == destination
        assert block.amount == -6000
        assert not block.description

        data = result["data"]
        assert data["hash"] == block.block_hash
        assert data["confirmed"]
        assert data["has_valid_work"]
        assert data["amount"] == "-6000"
        assert data["destination"] == destination

        assert wallet.accounts[0].balance == 4000

    def test_send_difficulty_change(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory,
            wallet_loader, caplog):
        """
        Send NANO to another account. The first broadcast will fail due to
        increased network difficulty.
        """
        wallet = wallet_factory(balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = wallet.accounts[0].account_id
        destination = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"

        wallet_mock_node.start()
        wallet_mock_node.raise_difficulty_after(block_count=0)

        result = stdio([
            "--wallet", str(wallet_path), "send",
            account_id, destination, "6000"
        ])

        wallet = wallet_loader(wallet_path)

        block = wallet.accounts[0].blocks[-1]
        block_hash = block.block_hash
        assert block.confirmed
        assert block.link_as_account == destination
        assert block.amount == -6000
        assert not block.description

        data = result["data"]
        assert data["hash"] == block.block_hash
        assert data["confirmed"]
        assert data["has_valid_work"]
        assert data["amount"] == "-6000"
        assert data["destination"] == destination

        assert wallet.accounts[0].balance == 4000

        # Check that proof-of-work was regenerated by reading logs
        assert caplog.text.count(
            "Regenerating proof-of-work for rejected block {}".format(
                block_hash
            ),
            1
        )

        assert caplog.text.count(
            "Rejected block {}. Reason: insufficient_work".format(block_hash),
            1
        )

        assert caplog.text.count("Confirmed block {}".format(block_hash), 1)

    def test_send_no_wait(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory,
            wallet_loader):
        wallet = wallet_factory(balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = wallet.accounts[0].account_id
        destination = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"

        wallet_mock_node.start()

        result = stdio([
            "--wallet", str(wallet_path), "send",
            account_id, destination, "6000", "--no-wait-until-confirmed"
        ])

        wallet = wallet_loader(wallet_path)

        block = wallet.accounts[0].blocks[-1]
        assert not block.confirmed
        assert block.link_as_account == destination
        assert block.amount == -6000
        assert not block.description

        data = result["data"]
        assert data["hash"] == block.block_hash
        assert not data["confirmed"]
        assert not data["has_valid_work"]
        assert data["amount"] == "-6000"
        assert data["destination"] == destination

        assert wallet.accounts[0].balance == 4000

    def test_send_description(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory,
            wallet_loader):
        wallet = wallet_factory(balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = wallet.accounts[0].account_id
        destination = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"

        wallet_mock_node.start()

        stdio([
            "--wallet", str(wallet_path), "send",
            account_id, destination, "6000",
            "--description", "A description for this block"
        ])

        wallet = wallet_loader(wallet_path)

        assert wallet.accounts[0].blocks[-1].description == \
            "A description for this block"

    def test_send_with_denomination(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory,
            wallet_loader):
        wallet = wallet_factory(balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = wallet.accounts[0].account_id
        destination = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"

        wallet_mock_node.start()

        result = stdio([
            "--wallet", str(wallet_path), "send",
            account_id, destination, "0.000000000000000000006 nano"
        ])

        wallet = wallet_loader(wallet_path)

        block = wallet.accounts[0].blocks[-1]
        assert block.confirmed
        assert block.link_as_account == destination
        assert block.amount == -6000

        data = result["data"]
        assert data["hash"] == block.block_hash
        assert data["confirmed"]
        assert data["has_valid_work"]
        assert data["amount"] == "-6000"
        assert data["destination"] == destination

        assert wallet.accounts[0].balance == 4000

    def test_send_spendable_account_required(
            self, stdio, wallet_mock_node, wallet_path, wallet_factory,
            watching_account_factory):
        wallet = wallet_factory(balance=0)
        wallet.accounts = []
        wallet.add_account(watching_account_factory())
        account_id = wallet.accounts[0].account_id

        wallet.save(wallet_path)

        wallet_mock_node.start()

        destination = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"

        result = stdio([
            "--wallet", wallet_path, "send", account_id,
            destination, "1000"
        ], success=False)

        assert result["data"]["error"] == "spendable_account_required"

    def test_send_duplicate_txid(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory,
            wallet_loader):
        wallet = wallet_factory(balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = wallet.accounts[0].account_id
        destination = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"

        wallet_mock_node.start()

        stdio([
            "--wallet", wallet_path, "send", account_id, destination, "5000",
            "--txid", "onlyonce"
        ])
        result = stdio([
            "--wallet", wallet_path, "send", account_id, destination, "5000",
            "--txid", "onlyonce"
        ], success=False)

        assert result["data"]["error"] == "transaction_already_exists"

    def test_send_insufficient_balance(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory):
        wallet = wallet_factory(balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = wallet.accounts[0].account_id
        destination = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"

        wallet_mock_node.start()

        result = stdio([
            "--wallet", str(wallet_path), "send",
            account_id, destination, "10001"
        ], success=False)

        assert result["data"]["error"] == "insufficient_balance"

    def test_send_nonexistent_source(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory):
        wallet = wallet_factory(balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = \
            "xrb_1111111111111111111111111111111111111111111111111111hifc8npp"
        destination = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"

        wallet_mock_node.start()

        result = stdio([
            "--wallet", str(wallet_path), "send",
            account_id, destination, "10001"
        ], success=False)

        assert result["data"]["error"] == "account_not_found"

    def test_send_broadcast_failure(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory,
            wallet_loader):
        wallet = wallet_factory(balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = wallet.accounts[0].account_id
        destination = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"

        wallet_mock_node.fail_broadcast_after(block_count=0)
        wallet_mock_node.start()

        result = stdio([
            "--wallet", str(wallet_path), "send",
            account_id, destination, "5000"
        ], success=False)

        assert result["data"]["block_error"] == "source_block_missing"
        assert result["data"]["error"] == "block_rejected"

        # Rejected block won't be saved
        wallet = wallet_loader(wallet_path)
        assert wallet.accounts[0].balance == 10000

    def test_send_broadcast_timeout(
            self, low_difficulty, mock_node, stdio, wallet_path, wallet_factory,
            wallet_loader):
        wallet = wallet_factory(balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = wallet.accounts[0].account_id
        destination = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"

        mock_node.add_replay_datasets(["active_difficulty", "version"]).start()

        result = stdio([
            "--wallet", wallet_path, "send", account_id, destination, "5000",
            "--timeout", "1"
        ], success=False)

        assert result["data"]["error"] == "network_timeout"

        # In case of a timeout, the block is still saved to the wallet
        wallet = wallet_loader(wallet_path)

        assert len(wallet.accounts[0].blocks) == 2
        assert wallet.accounts[0].blocks[-1].link_as_account == \
            destination


DESTINATION_A = \
    "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"
DESTINATION_B = \
    "xrb_1q7weoyzfw9z4836o11yfjfnqmf953yq8o4hcyp1thdak6xymqup4xczs5n8"


@pytest.mark.add_encrypted_test
class TestSendMany:
    def test_send_many(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory,
            wallet_loader):
        wallet = wallet_factory(
            balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = wallet.accounts[0].account_id

        wallet_mock_node.start()

        result = stdio([
            "--wallet", str(wallet_path), "send-many",
            account_id,
            "{},1000".format(DESTINATION_A),
            "{},2000".format(DESTINATION_B)
        ])

        wallet = wallet_loader(wallet_path)

        block_a = wallet.accounts[0].blocks[-2]
        block_b = wallet.accounts[0].blocks[-1]

        assert block_a.link_as_account == DESTINATION_A
        assert block_a.confirmed
        assert block_a.amount == -1000
        assert not block_a.description

        assert block_b.link_as_account == DESTINATION_B
        assert block_b.confirmed
        assert block_b.amount == -2000
        assert not block_b.description

        data = result["data"]
        assert data["blocks"][0]["destination"] == DESTINATION_A
        assert data["blocks"][0]["amount"] == "-1000"
        assert data["blocks"][0]["has_valid_work"]

        assert data["blocks"][1]["destination"] == DESTINATION_B
        assert data["blocks"][1]["amount"] == "-2000"
        assert data["blocks"][1]["has_valid_work"]

        assert wallet.accounts[0].balance == 7000

    def test_send_many_no_wait(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory,
            wallet_loader):
        wallet = wallet_factory(
            balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = wallet.accounts[0].account_id

        wallet_mock_node.start()

        result = stdio([
            "--wallet", str(wallet_path), "send-many",
            account_id,
            "{},1000".format(DESTINATION_A),
            "{},2000".format(DESTINATION_B),
            "--no-wait-until-confirmed"
        ])

        wallet = wallet_loader(wallet_path)

        block_a = wallet.accounts[0].blocks[-2]
        block_b = wallet.accounts[0].blocks[-1]

        assert block_a.link_as_account == DESTINATION_A
        assert not block_a.confirmed
        assert block_a.amount == -1000
        assert not block_a.description

        assert block_b.link_as_account == DESTINATION_B
        assert not block_b.confirmed
        assert block_b.amount == -2000
        assert not block_b.description

        data = result["data"]
        assert not data["blocks"][0]["confirmed"]
        assert data["blocks"][0]["destination"] == DESTINATION_A
        assert data["blocks"][0]["amount"] == "-1000"
        assert "block_error" not in data["blocks"][0]

        assert not data["blocks"][1]["confirmed"]
        assert data["blocks"][1]["destination"] == DESTINATION_B
        assert data["blocks"][1]["amount"] == "-2000"
        assert "block_error" not in data["blocks"][1]

        assert wallet.accounts[0].balance == 7000

    def test_send_many_description(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory,
            wallet_loader):
        wallet = wallet_factory(
            balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = wallet.accounts[0].account_id
        destination_a = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"
        destination_b = \
            "xrb_1q7weoyzfw9z4836o11yfjfnqmf953yq8o4hcyp1thdak6xymqup4xczs5n8"

        wallet_mock_node.start()

        stdio([
            "--wallet", str(wallet_path), "send-many",
            account_id,
            "{},1000".format(destination_a),
            "{},2000".format(destination_b),
            "--description", "Test description"
        ])

        wallet = wallet_loader(wallet_path)

        block_a = wallet.accounts[0].blocks[-2]
        block_b = wallet.accounts[0].blocks[-1]

        assert block_a.description == "Test description"
        assert block_b.description == "Test description"

    def test_send_many_with_denominations(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory,
            wallet_loader):
        wallet = wallet_factory(
            balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = wallet.accounts[0].account_id
        destination_a = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"
        destination_b = \
            "xrb_1q7weoyzfw9z4836o11yfjfnqmf953yq8o4hcyp1thdak6xymqup4xczs5n8"

        wallet_mock_node.start()

        result = stdio([
            "--wallet", str(wallet_path), "send-many",
            account_id,
            "{},0.000000000000000000001 nano".format(destination_a),
            "{},0.000000000000000000000000002 Mnano".format(destination_b)
        ])

        wallet = wallet_loader(wallet_path)

        block_a = wallet.accounts[0].blocks[-2]
        block_b = wallet.accounts[0].blocks[-1]

        assert block_a.link_as_account == destination_a
        assert block_a.confirmed
        assert block_a.amount == -1000

        assert block_b.link_as_account == destination_b
        assert block_b.confirmed
        assert block_b.amount == -2000

        data = result["data"]
        assert data["blocks"][0]["destination"] == destination_a
        assert data["blocks"][0]["amount"] == "-1000"

        assert data["blocks"][1]["destination"] == destination_b
        assert data["blocks"][1]["amount"] == "-2000"

        assert wallet.accounts[0].balance == 7000

    def test_send_many_spendable_account_required(
            self, stdio, wallet_mock_node, wallet_path, wallet_factory,
            watching_account_factory):
        wallet = wallet_factory(balance=0)
        wallet.accounts = []
        wallet.add_account(watching_account_factory())
        account_id = wallet.accounts[0].account_id

        wallet.save(wallet_path)

        wallet_mock_node.start()

        destination_a = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"

        result = stdio([
            "--wallet", wallet_path, "send-many", account_id,
            "{},1000".format(destination_a)
        ], success=False)

        assert result["data"]["error"] == "spendable_account_required"

    def test_send_many_insufficient_balance(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory):
        wallet = wallet_factory(
            balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = wallet.accounts[0].account_id
        destination_a = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"
        destination_b = \
            "xrb_1q7weoyzfw9z4836o11yfjfnqmf953yq8o4hcyp1thdak6xymqup4xczs5n8"

        wallet_mock_node.start()

        result = stdio([
            "--wallet", str(wallet_path), "send-many",
            account_id,
            "{},5000".format(destination_a),
            "{},5001".format(destination_b)
        ], success=False)

        assert result["data"]["error"] == "insufficient_balance"

    def test_send_many_nonexistent_source(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory):
        wallet = wallet_factory(
            balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = \
            "xrb_1111111111111111111111111111111111111111111111111111hifc8npp"
        destination_a = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"
        destination_b = \
            "xrb_1q7weoyzfw9z4836o11yfjfnqmf953yq8o4hcyp1thdak6xymqup4xczs5n8"

        wallet_mock_node.start()

        result = stdio([
            "--wallet", str(wallet_path), "send-many",
            account_id,
            "{},5000".format(destination_a),
            "{},5001".format(destination_b)
        ], success=False)

        assert result["data"]["error"] == "account_not_found"

    def test_send_many_invalid_destination(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory):
        wallet = wallet_factory(balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = \
            "xrb_1111111111111111111111111111111111111111111111111111hifc8npp"

        result = stdio([
            "--wallet", str(wallet_path), "send-many",
            account_id, "wrong,1000"
        ], raw=True)

        assert "invalid 'destination': is not a valid account ID" in result

    def test_send_many_broadcast_failure(
            self, wallet_mock_node, stdio, wallet_path, wallet_factory,
            wallet_loader):
        # Send three transactions and cause the second one to fail,
        # which also causes the third one to be rejected
        wallet = wallet_factory(balance=10000, confirmed=True)
        wallet.save(wallet_path)

        account_id = wallet.accounts[0].account_id
        destination_a = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"
        destination_b = \
            "xrb_1q7weoyzfw9z4836o11yfjfnqmf953yq8o4hcyp1thdak6xymqup4xczs5n8"
        destination_c = \
            "xrb_33dd14f3jygie9mkq5s76oo9p1zf8137f1gt65mbsptnktijqb4uzs7hgdkm"

        wallet_mock_node.fail_broadcast_after(block_count=1)
        wallet_mock_node.start()

        result = stdio([
            "--wallet", str(wallet_path), "send-many",
            account_id,
            "{},1000".format(destination_a),
            "{},2000".format(destination_b),
            "{},3000".format(destination_c)
        ], success=False)

        data = result["data"]
        assert data["error"] == "block_rejected"

        assert data["blocks"][0]["confirmed"]

        assert data["blocks"][1]["block_error"] == "source_block_missing"
        assert data["blocks"][2]["block_error"] == "previous_block_rejected"

        # Rejected blocks (2nd and 3rd) won't be saved
        wallet = wallet_loader(wallet_path)
        assert wallet.accounts[0].balance == 9000
        assert wallet.accounts[0].blocks[-1].amount == -1000

    def test_send_many_broadcast_timeout(
            self, mock_node, stdio, wallet_path, wallet_factory,
            wallet_loader):
        wallet = wallet_factory(balance=10000, confirmed=True)
        wallet.save(wallet_path)

        mock_node.add_replay_datasets(["active_difficulty", "version"]).start()

        account_id = wallet.accounts[0].account_id
        destination_a = \
            "xrb_36t3jt9g5r33i817oimdpre1fyofoha5j4k4rq6ofokrokigf3q6xfhe6r6m"
        destination_b = \
            "xrb_1q7weoyzfw9z4836o11yfjfnqmf953yq8o4hcyp1thdak6xymqup4xczs5n8"

        result = stdio([
            "--wallet", wallet_path, "send-many", account_id,
            "{},1000".format(destination_a), "{},2000".format(destination_b),
            "--timeout", "1"
        ], success=False)

        assert result["data"]["error"] == "network_timeout"

        # The blocks are saved despite the timeout
        wallet = wallet_loader(wallet_path)

        assert wallet.accounts[0].blocks[-1].link_as_account == \
            destination_b
        assert wallet.accounts[0].blocks[-2].link_as_account == \
            destination_a


@pytest.mark.add_encrypted_test
class TestListAccounts:
    def test_list_accounts(self, stdio, wallet_path, wallet_loader):
        stdio(["create-wallet", str(wallet_path)])
        wallet = wallet_loader(wallet_path)
        wallet.accounts[4].name = "Fifth account"
        wallet.save(wallet_path)

        result = stdio(["--wallet", str(wallet_path), "list-accounts"])

        assert len(result["data"]["accounts"]) == 20
        assert result["data"]["accounts"][4]["name"] == "Fifth account"


@pytest.mark.add_encrypted_test
class TestGetAccountPrivateKey:
    def test_get_account_private_key(
            self, stdio, wallet_path, wallet_factory, wallet_loader,
            is_encrypted_test):
        wallet = wallet_factory()
        account_id = wallet.accounts[0].account_id

        if is_encrypted_test:
            wallet.unlock("password")
            private_key = wallet.accounts[0].get_secret(
                "private_key", secret_key=wallet.secret_key
            )
            wallet.lock()
        else:
            private_key = wallet.accounts[0].private_key

        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "get-account-private-key",
            account_id
        ])

        assert result["data"]["account_id"] == account_id
        assert result["data"]["private_key"] == private_key

    def test_get_account_private_key_account_not_found(
            self, stdio, wallet_path, wallet_factory):
        wallet = wallet_factory()
        wallet.save(wallet_path)

        account_id = \
            "xrb_1111111111111111111111111111111111111111111111111111hifc8npp"

        result = stdio([
            "--wallet", wallet_path, "get-account-private-key",
            account_id
        ], success=False)

        assert result["data"]["error"] == "account_not_found"

    def test_get_account_private_key_watching_account(
            self, stdio, wallet_path, wallet_factory):
        wallet = wallet_factory()
        account_id = wallet.accounts[0].account_id

        wallet.accounts[0].private_key = None
        wallet.accounts[0].source = AccountSource.WATCHING
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "get-account-private-key",
            account_id
        ], success=False)

        assert result["data"]["error"] == "spendable_account_required"


@pytest.mark.add_encrypted_test
class TestListBlocks:
    @pytest.fixture(scope="function")
    def active_wallet(self, wallet_factory, account_factory):
        wallet = wallet_factory(balance=0)
        wallet.accounts = []
        wallet.add_account(
            account_factory(
                balance=500, block_count=50, complete=True, confirm=True
            )
        )

        return wallet

    def test_list_blocks(
            self, stdio, wallet_path, active_wallet):
        wallet = active_wallet
        account = wallet.accounts[0]
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "list-blocks", account.account_id,
            "--limit", "20"
        ])

        data = result["data"]
        assert data["count"] == 50
        assert len(data["blocks"]) == 20

        # By default, the blocks are returned in descending order
        # eg. starting from newest to oldest blocks
        assert data["blocks"][0]["hash"] == account.blocks[49].block_hash
        assert data["blocks"][1]["hash"] == account.blocks[48].block_hash

        assert data["blocks"][0]["balance"] == "500"
        assert data["blocks"][0]["amount"] == "10"

    def test_list_blocks_ascending(
            self, stdio, wallet_path, active_wallet):
        wallet = active_wallet
        account = wallet.accounts[0]
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "list-blocks", account.account_id,
            "--limit", "20", "--no-descending"
        ])

        data = result["data"]
        assert data["count"] == 50
        assert len(data["blocks"]) == 20

        assert data["blocks"][0]["hash"] == account.blocks[0].block_hash
        assert data["blocks"][1]["hash"] == account.blocks[1].block_hash

        assert data["blocks"][0]["balance"] == "10"
        assert data["blocks"][0]["amount"] == "10"

    def test_list_blocks_empty(
            self, stdio, zero_balance_wallet, wallet_path):
        # Empty accounts return an empty list
        wallet = zero_balance_wallet
        wallet.save(wallet_path)

        account_id = wallet.accounts[0].account_id

        result = stdio([
            "--wallet", wallet_path, "list-blocks", account_id
        ])

        assert result["data"]["count"] == 0
        assert len(result["data"]["blocks"]) == 0

    def test_list_blocks_offset(self, stdio, wallet_path, active_wallet):
        wallet = active_wallet
        account = wallet.accounts[0]
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "list-blocks", account.account_id,
            "--offset", "5", "--limit", "20"
        ])

        data = result["data"]
        assert len(data["blocks"]) == 20
        assert data["blocks"][0]["hash"] == account.blocks[44].block_hash
        assert data["blocks"][1]["hash"] == account.blocks[43].block_hash

    def test_list_blocks_ascending_offset(
            self, stdio, wallet_path, active_wallet):
        wallet = active_wallet
        account = wallet.accounts[0]
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "list-blocks", account.account_id,
            "--offset", "5", "--limit", "20", "--no-descending"
        ])

        data = result["data"]
        assert len(data["blocks"]) == 20
        assert data["blocks"][0]["hash"] == account.blocks[5].block_hash
        assert data["blocks"][1]["hash"] == account.blocks[6].block_hash

    def test_list_blocks_offset_empty(
            self, stdio, wallet_path, active_wallet):
        # If an offset higher than the amount of blocks is given,
        # return an empty list
        wallet = active_wallet
        account = wallet.accounts[0]
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "list-blocks", account.account_id,
            "--offset", "50"
        ])

        assert len(result["data"]["blocks"]) == 0

    def test_list_blocks_offset_ascending_empty(
            self, stdio, wallet_path, active_wallet):
        wallet = active_wallet
        account = wallet.accounts[0]
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "list-blocks", account.account_id,
            "--offset", "50", "--no-descending"
        ])

        assert len(result["data"]["blocks"]) == 0


@pytest.mark.add_encrypted_test
class TestGetBlock:
    def test_get_block(self, stdio, wallet_factory, wallet_path):
        wallet = wallet_factory(balance=10000, confirmed=True)
        block = wallet.accounts[0].blocks[0]
        block.description = "This is a test block"
        block_hash = block.block_hash
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "get-block", block_hash
        ])

        data = result["data"]
        assert data["hash"] == block_hash
        assert data["confirmed"]
        assert not data["is_link_block"]
        assert data["description"] == "This is a test block"
        assert data["amount"] == "10000"
        assert data["balance"] == "10000"
        assert data["timestamp"]["date"].isdigit()
        assert data["block_data"]["account"] == block.account

    def test_get_block_block_not_found(
            self, stdio, wallet_factory, wallet_path):
        wallet = wallet_factory(balance=10000, confirmed=True)
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "get-block", "A"*64
        ], success=False)

        assert result["data"]["error"] == "block_not_found"

    def test_get_block_link_block(self, stdio, wallet_factory, wallet_path):
        wallet = wallet_factory(balance=10000, confirmed=True)
        block = wallet.accounts[0].blocks[0]
        block_hash = block.link_block.block_hash
        wallet.save(wallet_path)

        result = stdio(["--wallet", wallet_path, "get-block", block_hash])

        data = result["data"]
        assert data["hash"] == block_hash
        assert data["confirmed"]
        assert data["is_link_block"]
        assert data["amount"] == "-10000"
        assert data["timestamp"]["date"].isdigit()
        assert data["block_data"]["account"] == block.link_block.account


@pytest.mark.add_encrypted_test
class TestSetAccountName:
    def test_set_account_name(
            self, stdio, wallet_factory, wallet_path, wallet_loader):
        wallet = wallet_factory()
        account_id = wallet.accounts[3].account_id
        wallet.save(str(wallet_path))

        result = stdio([
            "--wallet", str(wallet_path), "set-account-name",
            account_id, "Account number four"
        ])

        assert result["data"]["account_id"] == account_id
        assert result["data"]["name"] == "Account number four"

        wallet = wallet_loader(str(wallet_path))
        assert wallet.accounts[3].name == "Account number four"

    def test_set_account_name_account_not_found(
            self, stdio, wallet_factory, wallet_path):
        wallet = wallet_factory()
        wallet.save(str(wallet_path))

        result = stdio([
            "--wallet", str(wallet_path), "set-account-name",
            "xrb_1111111111111111111111111111111111111111111111111111hifc8npp",
            "Nonexistent account"
        ], success=False)

        assert result["data"]["error"] == "account_not_found"


@pytest.mark.add_encrypted_test
class TestClearAccountName:
    def test_clear_account_name(
            self, stdio, zero_balance_wallet, wallet_path, wallet_loader):
        wallet = zero_balance_wallet
        account_id = wallet.accounts[0].account_id

        wallet.save(wallet_path)

        stdio([
            "--wallet", str(wallet_path), "set-account-name",
            account_id, "Test name"
        ])

        # If 'name' is not provided, the name is removed
        result = stdio([
            "--wallet", str(wallet_path), "clear-account-name",
            account_id
        ])

        assert result["data"]["account_id"] == account_id

        wallet = wallet_loader(wallet_path)

        assert not wallet.accounts[0].name

    def test_clear_account_name_account_not_found(
            self, stdio, wallet_factory, wallet_path):
        wallet = wallet_factory()
        wallet.save(str(wallet_path))

        result = stdio([
            "--wallet", str(wallet_path), "clear-account-name",
            "xrb_1111111111111111111111111111111111111111111111111111hifc8npp",
        ], success=False)

        assert result["data"]["error"] == "account_not_found"


@pytest.mark.add_encrypted_test
class TestSetBlockDescription:
    def test_set_block_description(
            self, stdio, wallet_factory, wallet_loader, wallet_path):
        wallet = wallet_factory(balance=1000)
        account_id = wallet.accounts[0].account_id
        block_hash = wallet.accounts[0].blocks[0].block_hash

        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "set-block-description",
            block_hash, "Test description"
        ])

        data = result["data"]

        assert data["account_id"] == account_id
        assert data["hash"] == block_hash
        assert data["description"] == "Test description"

        wallet = wallet_loader(wallet_path)

        assert wallet.accounts[0].blocks[0].description == "Test description"

    def test_set_block_no_link_block(
            self, stdio, wallet_factory, wallet_loader, wallet_path):
        wallet = wallet_factory(balance=1000)
        block_hash = wallet.accounts[0].blocks[0].link_block.block_hash

        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "set-block-description",
            block_hash, "Test description"
        ], success=False)

        assert result["data"]["error"] == "link_block_not_allowed"

    def test_set_block_missing_block(
            self, stdio, wallet_factory, wallet_loader, wallet_path):
        wallet = wallet_factory(balance=1000)
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "set-block-description",
            "a"*64, "Test description"
        ], success=False)

        assert result["data"]["error"] == "block_not_found"


@pytest.mark.add_encrypted_test
class TestClearBlockDescription:
    def test_clear_block_description(
            self, stdio, wallet_factory, wallet_loader, wallet_path):
        wallet = wallet_factory(balance=1000)
        wallet.accounts[0].blocks[0].description = "Test description"
        block_hash = wallet.accounts[0].blocks[0].block_hash

        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "clear-block-description",
            block_hash
        ])
        assert result["data"]["hash"] == block_hash

        wallet = wallet_loader(wallet_path)

        assert not wallet.accounts[0].blocks[0].description

    def test_clear_block_description_no_link_block(
            self, stdio, wallet_factory, wallet_loader, wallet_path):
        wallet = wallet_factory(balance=1000)
        block_hash = wallet.accounts[0].blocks[0].link_block.block_hash

        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "clear-block-description",
            block_hash
        ], success=False)
        assert result["data"]["error"] == "link_block_not_allowed"

    def test_clear_block_description_missing_block(
            self, stdio, wallet_factory, wallet_loader, wallet_path):
        wallet = wallet_factory(balance=1000)
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "clear-block-description",
            "a"*64
        ], success=False)

        assert result["data"]["error"] == "block_not_found"


@pytest.mark.add_encrypted_test
class TestAddToAddressBook:
    def test_add_to_address_book(
            self, stdio, wallet_path, wallet_loader, empty_wallet):
        wallet = empty_wallet
        wallet.save(wallet_path)

        account_id = \
            "xrb_1osyg4d5oshdzbxsnshk6er6sfk7ufjjh645ecob7ydo3r4e4jqd5yucuyja"

        result = stdio([
            "--wallet", wallet_path, "add-to-address-book", account_id,
            "Test name"
        ])

        assert result["data"]["account_id"] == account_id
        assert result["data"]["name"] == "Test name"

        wallet = wallet_loader(wallet_path)
        assert wallet.address_book[account_id] == "Test name"


@pytest.mark.add_encrypted_test
class TestRemoveFromAddressBook:
    def test_remove_from_address_book(
            self, stdio, wallet_path, wallet_loader, empty_wallet):
        account_id = \
            "xrb_1osyg4d5oshdzbxsnshk6er6sfk7ufjjh645ecob7ydo3r4e4jqd5yucuyja"

        wallet = empty_wallet
        wallet.save(wallet_path)

        stdio([
            "--wallet", wallet_path, "add-to-address-book", account_id,
            "Test name"
        ])
        result = stdio([
            "--wallet", wallet_path, "remove-from-address-book", account_id
        ])

        assert result["data"]["account_id"] == account_id

        wallet = wallet_loader(wallet_path)
        assert account_id not in wallet.address_book

    def test_remove_from_address_book_account_not_found(
            self, stdio, wallet_path, wallet_loader, empty_wallet):
        account_id = \
            "xrb_1osyg4d5oshdzbxsnshk6er6sfk7ufjjh645ecob7ydo3r4e4jqd5yucuyja"

        wallet = empty_wallet
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "remove-from-address-book", account_id
        ], success=False)

        assert result["data"]["error"] == "account_not_found"


REPRESENTATIVE = \
    "xrb_3t5uq974om59rwcs7wij5kis5e15tbgxe6ip6nu77jzs1n8b65hobnqdede8"


@pytest.mark.add_encrypted_test
class TestChangeAccountRepresentative:
    def test_change_account_representative_empty_account(
            self, stdio, wallet_path, wallet_loader, wallet_factory):
        wallet = wallet_factory(balance=0)
        account_id = wallet.accounts[0].account_id
        wallet.save(wallet_path)
        result = stdio([
            "--wallet", wallet_path, "change-account-representative",
            account_id, REPRESENTATIVE
        ])

        assert result["data"]["account_id"] == account_id
        assert result["data"]["representative"] == REPRESENTATIVE

        wallet = wallet_loader(wallet_path)
        assert wallet.accounts[0].representative == REPRESENTATIVE
        assert not wallet.accounts[0].blocks

    def test_change_account_representative_with_confirmed_block(
            self, stdio, wallet_mock_node, wallet_path, wallet_loader,
            wallet_factory):
        wallet = wallet_factory(balance=1000, confirmed=True)
        account_id = wallet.accounts[0].account_id
        wallet.save(wallet_path)

        wallet_mock_node.start()

        result = stdio([
            "--wallet", wallet_path, "change-account-representative",
            account_id, REPRESENTATIVE, "--wait-until-confirmed"
        ])

        data = result["data"]
        assert data["account_id"] == account_id
        assert data["confirmed"]

        wallet = wallet_loader(wallet_path)

        assert wallet.accounts[0].representative == REPRESENTATIVE

        block = wallet.accounts[0].blocks[-1]

        assert block.tx_type == "change"
        assert data["hash"] == block.block_hash

    def test_change_account_representative_without_confirmed_block(
            self, stdio, wallet_path, wallet_loader, wallet_factory):
        wallet = wallet_factory(balance=1000, confirmed=True)
        account_id = wallet.accounts[0].account_id
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "change-account-representative",
            account_id, REPRESENTATIVE
        ])

        data = result["data"]
        assert data["account_id"] == account_id
        assert not data["confirmed"]

        wallet = wallet_loader(wallet_path)

        assert wallet.accounts[0].representative == REPRESENTATIVE

        block = wallet.accounts[0].blocks[-1]

        assert block.tx_type == "change"
        assert data["hash"] == block.block_hash

    def test_change_account_representative_with_failed_block(
            self, stdio, wallet_mock_node, wallet_path, wallet_loader,
            wallet_factory):
        wallet = wallet_factory(balance=1000, confirmed=True)
        account_id = wallet.accounts[0].account_id
        original_representative = wallet.accounts[0].representative
        wallet.save(wallet_path)

        wallet_mock_node.fail_broadcast_after(block_count=0)
        wallet_mock_node.start()

        result = stdio([
            "--wallet", wallet_path, "change-account-representative",
            account_id, REPRESENTATIVE, "--wait-until-confirmed"
        ], success=False)

        data = result["data"]
        assert data["block_error"] == "source_block_missing"
        assert data["error"] == "block_rejected"
        assert not data["confirmed"]
        assert "hash" not in data

        wallet = wallet_loader(wallet_path)

        assert len(wallet.accounts[0].blocks) == 1
        assert wallet.accounts[0].representative == original_representative

    def test_change_account_representative_with_timed_out_block(
            self, mock_node, stdio, wallet_path, wallet_factory,
            wallet_loader):
        wallet = wallet_factory(balance=1000, confirmed=True)
        account_id = wallet.accounts[0].account_id
        wallet.save(wallet_path)

        mock_node.add_replay_datasets(["active_difficulty", "version"]).start()

        result = stdio([
            "--wallet", wallet_path, "change-account-representative",
            account_id, REPRESENTATIVE, "--wait-until-confirmed",
            "--timeout", "1"
        ], success=False)

        data = result["data"]
        assert data["block_error"] == "timeout"
        assert data["error"] == "network_timeout"

        wallet = wallet_loader(wallet_path)

        # The timed out block is still saved
        assert len(wallet.accounts[0].blocks) == 2
        assert wallet.accounts[0].representative == REPRESENTATIVE

    def test_change_account_representative_account_not_found(
            self, stdio, empty_wallet, wallet_path):
        empty_wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "change-account-representative",
            "xrb_1111111111111111111111111111111111111111111111111111hifc8npp",
            REPRESENTATIVE
        ], success=False)

        assert result["data"]["error"] == "account_not_found"

    def test_change_account_representative_spendable_account_required(
            self, stdio, empty_wallet, wallet_path, watching_account_factory):
        wallet = empty_wallet
        wallet.add_account(watching_account_factory())

        account_id = wallet.accounts[0].account_id

        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "change-account-representative",
            account_id, REPRESENTATIVE
        ], success=False)

        assert result["data"]["error"] == "spendable_account_required"


@pytest.mark.add_encrypted_test
class TestListAddressBook:
    def test_list_address_book(
            self, stdio, wallet_factory, wallet_path, wallet_loader):
        wallet = wallet_factory()
        wallet.add_to_address_book(DESTINATION_A, "Destination 1")
        wallet.add_to_address_book(DESTINATION_B, "Destination 2")
        wallet.save(wallet_path)

        result = stdio([
            "--wallet", wallet_path, "list-address-book"
        ])

        data = result["data"]
        assert len(data["addresses"]) == 2
        assert data["count"] == 2
        assert data["addresses"][DESTINATION_A] == "Destination 1"
        assert data["addresses"][DESTINATION_B] == "Destination 2"
