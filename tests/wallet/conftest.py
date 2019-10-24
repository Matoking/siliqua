import json
import random
import time

import pytest
from nanolib import Block as RawBlock
from nanolib import generate_seed, get_account_id, get_account_public_key
from siliqua.wallet import (Account, AccountSource, Block, LinkBlock,
                            Timestamp, TimestampSource, Wallet,
                            WalletProperties, WalletSeedAlgorithm, logger)
from siliqua.wallet.secret import calculate_key_iteration_count
from tests.util import to_hex

TEST_DIFFICULTY = to_hex(9459044173002835106, 16)


@pytest.fixture(scope="function")
def is_encrypted_test():
    """
    Returns a boolean depending on whether the test case involves
    an encrypted wallet.

    The value of this fixture can be changed by adding a
    @pytest.mark.with_encrypted_scenario marker, which will generate
    an alternate test scenario using an encrypted wallet.
    """
    return False


@pytest.fixture(scope="function")
def private_account_factory():
    def create_account(private_key=None):
        if not private_key:
            private_key = generate_seed()

        public_key = get_account_public_key(private_key=private_key)
        account_id = get_account_id(public_key=public_key)

        account = Account(
            account_id=account_id,
            public_key=public_key,
            private_key=private_key,
            source=AccountSource.PRIVATE_KEY)

        return account

    return create_account


@pytest.fixture(scope="function")
def watching_account_factory():
    def create_account(account_id=None):
        if not account_id:
            account_id = get_account_id(public_key=generate_seed())

        account = Account(
            account_id=account_id,
            source=AccountSource.WATCHING)

        return account

    return create_account


@pytest.fixture(scope="function")
def pocketable_block_factory():
    def create_link_block(account_id, amount):
        sending_private_key = generate_seed()
        sending_account_id = get_account_id(private_key=sending_private_key)

        block = RawBlock(
            block_type="state",
            account=sending_account_id,
            previous=generate_seed().upper(),
            representative=get_account_id(public_key=generate_seed()),
            balance=amount + random.randint(2**100, 2**110),
            link_as_account=account_id)
        block.sign(sending_private_key)
        block.solve_work(difficulty=TEST_DIFFICULTY)

        link_block = LinkBlock(
            block_data=block.to_dict(),
            amount=amount,
            timestamp=Timestamp(
                date=time.time(), source=TimestampSource.WALLET
            )
        )

        return link_block

    return create_link_block


@pytest.fixture(scope="function")
def legacy_pocketable_block_factory():
    def create_link_block(account_id, amount):
        sending_private_key = generate_seed()
        sending_account_id = get_account_id(private_key=sending_private_key)

        block = RawBlock(
            block_type="send",
            account=sending_account_id,
            previous=generate_seed().upper(),
            destination=account_id,
            balance=amount + random.randint(-amount, 2**110)
        )
        block.sign(sending_private_key)
        block.solve_work(difficulty=TEST_DIFFICULTY)

        link_block = LinkBlock(
            block_data=block.to_dict(),
            amount=amount,
            timestamp=Timestamp(
                date=time.time(), source=TimestampSource.WALLET
            )
        )

        return link_block

    return create_link_block


@pytest.fixture(scope="function")
def legacy_receive_block_factory(legacy_pocketable_block_factory):
    def create_block(prev_block, private_key, amount):
        account_id = get_account_id(private_key=private_key)
        link_block = legacy_pocketable_block_factory(
            account_id=account_id, amount=amount)

        raw_block = RawBlock(
            account=account_id,
            block_type="receive",
            previous=prev_block.block_hash,
            source=link_block.block_hash)
        raw_block.sign(private_key)
        raw_block.solve_work(difficulty=TEST_DIFFICULTY)

        block = Block(
            block_data=raw_block.to_dict(),
            link_block=link_block,
        )

        return block

    return create_block


@pytest.fixture(scope="function")
def account_factory(pocketable_block_factory):
    def create_account(balance, block_count=1, complete=False, confirm=False):
        private_key = generate_seed()
        account_id = get_account_id(private_key=private_key)

        account = Account(
            account_id=account_id,
            public_key=get_account_public_key(private_key=private_key),
            private_key=private_key,
            source=AccountSource.PRIVATE_KEY,
            representative=get_account_id(public_key=generate_seed())
        )

        block_amount = int(balance / block_count)

        for _ in range(0, block_count):
            account.receive_block(
                pocketable_block_factory(
                    account_id=account_id, amount=block_amount
                )
            )

            if complete:
                block = account.blocks[-1]
                block.sign(private_key=account.private_key)
                block.solve_work(difficulty=TEST_DIFFICULTY)

            if confirm:
                block.confirmed = True
                account.update_confirmed_head()

        return account

    return create_account


@pytest.fixture(scope="function")
@pytest.mark.usefixtures("fast_key_derivation")
def wallet_factory(pocketable_block_factory, is_encrypted_test):
    def create_wallet(balance=0, seed=None, confirmed=False):
        if not seed:
            seed = generate_seed()

        wallet = Wallet(
            properties=WalletProperties(
                seed=seed,
                seed_algorithm=WalletSeedAlgorithm.NANO,
                gap_limit=20
            )
        )
        wallet.refill_accounts()

        if balance > 0:
            account = wallet.accounts[0]
            block = account.receive_block(
                pocketable_block_factory(
                    account_id=account.account_id,
                    amount=balance
                )
            )

            if confirmed:
                block.sign(account.get_secret("private_key"))
                block.solve_work(difficulty=TEST_DIFFICULTY)
                block.confirmed = True
                account.update_confirmed_head()

        if is_encrypted_test:
            key_iteration_count = 200

            wallet.change_passphrase(
                passphrase="password", encrypt_wallet=True,
                encrypt_secrets=True, key_iteration_count=key_iteration_count
            )

            wallet.lock()

            assert not wallet.secrets_unlocked
            assert not wallet.secret_key
            assert wallet.encryption.secrets_encrypted

        return wallet

    return create_wallet


@pytest.fixture(scope="function")
def wallet(wallet_factory):
    return wallet_factory()


@pytest.fixture(scope="function")
def wallet_path(tmp_path):
    return tmp_path / "test.wallet"


@pytest.fixture(scope="function")
def encrypted_wallet_factory(wallet_factory):
    def create_encrypted_wallet(**kwargs):
        wallet = wallet_factory(**kwargs)

        key_iteration_count = calculate_key_iteration_count(seconds=0.05)

        wallet.change_passphrase(
            passphrase="password", encrypt_wallet=True, encrypt_secrets=True,
            key_iteration_count=key_iteration_count
        )

        return wallet

    return create_encrypted_wallet


@pytest.fixture(scope="function")
def wallet_loader(is_encrypted_test):
    def load_wallet(path, passphrase=None):
        if is_encrypted_test:
            passphrase = "password"

        return Wallet.load(path, passphrase=passphrase)

    return load_wallet


@pytest.fixture(scope="function")
def encrypted_wallet_loader(wallet_loader):
    def load_wallet(path):
        return wallet_loader(path, passphrase="password")

    return load_wallet


@pytest.fixture(scope="function")
def encrypted_wallet(wallet_factory):
    wallet = wallet_factory()
    wallet.change_passphrase(
        "password", encrypt_secrets=True, encrypt_wallet=True)

    return wallet


@pytest.fixture(scope="function")
def zero_balance_wallet(wallet_factory):
    return wallet_factory(balance=0)


@pytest.fixture(scope="function")
def empty_wallet(wallet_factory):
    wallet = wallet_factory(balance=0)
    wallet.accounts = []
    wallet.properties.seed = None
    wallet.properties.seed_algorithm = None

    return wallet


@pytest.fixture(scope="function")
def wallet_properties_factory():
    def create_wallet_properties():
        return WalletProperties(
            seed=generate_seed(),
            seed_algorithm=WalletSeedAlgorithm.NANO,
            gap_limit=20
        )

    return create_wallet_properties


@pytest.fixture(scope="function")
def wallet_properties(wallet_properties_factory):
    return wallet_properties_factory()
