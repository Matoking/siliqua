import base64
import os
import secrets
from enum import Enum
from functools import wraps

import ijson
from nanolib import (WORK_DIFFICULTY, generate_account_id,
                     generate_account_key_pair, get_account_id,
                     get_account_key_pair, validate_account_id,
                     validate_block_hash, validate_private_key, validate_seed)
from siliqua.network import BlockProcessError
from siliqua.util import AccountIDDict

from ..util import Callbacks
from ..work import WorkUnit
from . import logger
from .accounts import Account, AccountSource, Block, PrecomputedWork
from .exceptions import (AccountAlreadyExists, InvalidEncryptionKey,
                         TransactionAlreadyExists, UnsupportedWalletVersion,
                         WalletDecryptionError, WalletFileInvalid,
                         WalletLocked, WalletMigrationRequired)
from .secret import (KeyType, Secret, SecretAlgorithm,
                     calculate_key_iteration_count, get_secret_key,
                     validate_encryption_key)
from .util import (HexDict, WalletSerializable, sort_blocks_for_broadcast,
                   wallet_parameter)
from siliqua.util import normalize_account_id

import rapidjson


__all__ = (
    "WalletSeedAlgorithm", "WalletProperties", "Transaction", "Wallet"
)

# 'Empty' representative used when the user hasn't defined a representative
EMPTY_REPRESENTATIVE = \
    "xrb_1111111111111111111111111111111111111111111111111111hifc8npp"

# The newest wallet version
# Older wallet versions will need to be migrated to newer versions.
# Newer wallet versions will cause an error to prevent misbehavior.
WALLET_VERSION = 1


class WalletSeedAlgorithm(Enum):
    """
    Algorithm used for generating accounts from a seed
    """
    # Algorithm used by reference NANO client and most third-party
    # wallets
    NANO = "nano"


class WalletProperties(WalletSerializable):
    """
    Contains miscellaneous properties related to the wallet,
    such as account generation seed, encryption status and such

    :ivar seed_algorithm: Algorithm used to derive accounts from the seed
    :type seed_algorithm: WalletSeedAlgorithm
    :ivar str seed: Wallet seed for generating accounts
    :ivar int gap_limit: Minimum amount of unused accounts to generate from the
                         seed
    :ivar str representative: Representative account ID used as a default
                              for new accounts
    """
    __slots__ = (
        "_gap_limit", "_seed_algorithm", "_seed", "_version"
    )

    SERIALIZE_PROPS = {
        "seed_algorithm": {"type": WalletSeedAlgorithm, "secret": False},
        "seed": {"type": str, "secret": True},
        "gap_limit": {"type": int},
        "representative": {"type": str},
        "version": {"type": int}
    }

    def __init__(self, *args, **kwargs):
        self.seed_algorithm = kwargs.get("seed_algorithm", None)
        self.seed = kwargs.get("seed", None)
        self.gap_limit = kwargs.get("gap_limit", None)
        self.representative = kwargs.get("representative", None)
        self.version = kwargs.get("version", WALLET_VERSION)

    @wallet_parameter
    def set_seed_algorithm(self, algorithm):
        if algorithm is not None:
            self._seed_algorithm = WalletSeedAlgorithm(algorithm)
        else:
            self._seed_algorithm = None

    @wallet_parameter
    def set_seed(self, seed, is_secret):
        if seed is not None:
            if not is_secret:
                validate_seed(seed)
            self._seed = seed
        else:
            self._seed = None

    @wallet_parameter
    def set_gap_limit(self, gap_limit):
        if gap_limit is not None:
            gap_limit = int(gap_limit)
            if gap_limit < 0:
                raise ValueError("Positive integer is required")

            self._gap_limit = gap_limit
        else:
            self._gap_limit = None

    @wallet_parameter
    def set_representative(self, representative):
        if representative:
            self._representative = normalize_account_id(
                validate_account_id(representative)
            )
        else:
            self._representative = None

    @wallet_parameter
    def set_version(self, version):
        if version is None:
            raise ValueError("Version is required")

        if not isinstance(version, int):
            raise TypeError("Only integers are accepted")

        self._version = version

    seed_algorithm = property(lambda x: x._seed_algorithm, set_seed_algorithm)
    seed = property(lambda x: x._seed, set_seed)
    gap_limit = property(lambda x: x._gap_limit, set_gap_limit)
    representative = property(lambda x: x._representative, set_representative)
    version = property(lambda x: x._version, set_version)


def ensure_secrets_unlocked(func):
    """
    Decorator that ensures the wrapped method can only be called when
    the wallet secrets are already unlocked.

    :raises WalletLocked: Wallet is locked
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.secrets_unlocked:
            raise WalletLocked(
                "The wallet secrets have to be unlocked for this operation"
            )

        return func(self, *args, **kwargs)

    return wrapper


class WalletEncryption(WalletSerializable):
    """
    Contains settings related to the wallet's optional encryption

    :ivar bool secrets_encrypted: Whether secrets are encrypted
    :ivar str secret_checksum: Secret checksum that is used to test
                               the correct passphrase
    :ivar bool wallet_encrypted: Whether the wallet is encrypted
    :ivar algorithm: Algorithm used for encrypting the wallet data, if
                     applicable
    :type algorithm: siliqua.wallet.secret.SecretAlgorithm
    :ivar int key_iteration_count: Key iteration count used for deriving
                                   the secret key from a passphrase.
    """
    __slots__ = (
        "_secrets_encrypted", "_secret_checksum", "_wallet_encrypted",
        "_algorithm", "_key_iteration_count"
    )

    SERIALIZE_PROPS = {
        "secrets_encrypted": {"type": bool},
        "secret_checksum": {"type": str, "secret": True},
        "wallet_encrypted": {"type": bool},

        "algorithm": {"type": SecretAlgorithm},
        "key_iteration_count": {"type": int}
    }

    def __init__(self, *args, **kwargs):
        self.secrets_encrypted = kwargs.get("secrets_encrypted", False)
        self.secret_checksum = kwargs.get("secret_checksum", None)

        self.wallet_encrypted = kwargs.get("wallet_encrypted", False)

        self.algorithm = kwargs.get("algorithm", None)
        self.key_iteration_count = kwargs.get("key_iteration_count", None)

    @wallet_parameter
    def set_secrets_encrypted(self, encrypted):
        if encrypted in (True, False):
            self._secrets_encrypted = encrypted
        else:
            raise ValueError("Value has to be a boolean")

    @wallet_parameter
    def set_secret_checksum(self, checksum, is_secret):
        if is_secret:
            self._secret_checksum = checksum
        else:
            self._secret_checksum = None

    @wallet_parameter
    def set_wallet_encrypted(self, encrypted):
        if encrypted in (True, False):
            self._wallet_encrypted = encrypted
        else:
            raise ValueError("Value has to be a boolean")

    @wallet_parameter
    def set_algorithm(self, algorithm):
        if algorithm is not None:
            self._algorithm = SecretAlgorithm(algorithm)
        else:
            self._algorithm = None

    @wallet_parameter
    def set_key_iteration_count(self, count):
        if count is not None:
            count = int(count)
            if count < 0:
                raise ValueError("Positive integer is required")
            self._key_iteration_count = count
        else:
            self._key_iteration_count = None

    secrets_encrypted = property(
        lambda x: x._secrets_encrypted, set_secrets_encrypted)
    secret_checksum = property(
        lambda x: x._secret_checksum, set_secret_checksum)

    wallet_encrypted = property(
        lambda x: x._wallet_encrypted, set_wallet_encrypted)

    algorithm = property(lambda x: x._algorithm, set_algorithm)
    key_iteration_count = property(
        lambda x: x._key_iteration_count, set_key_iteration_count)


class Transaction(WalletSerializable):
    """
    Transaction object used internally by the wallet to track
    unique transactions.

    Only one transaction with the same txid can exist. Each transaction
    correponds to one block.

    :ivar str txid: User-defined transaction ID
    :ivar str account_id: Account ID of the block
    :ivar str block_hash: Block hash
    """
    __slots__ = ("_txid", "_account_id", "_block_hash")

    SERIALIZE_PROPS = {
        "txid": {"type": str, "required": True},
        "account_id": {"type": str, "required": True},
        "block_hash": {"type": str, "required": True}
    }

    def __init__(self, **kwargs):
        self.txid = kwargs.get("txid", None)
        self.account_id = kwargs.get("account_id", None)
        self.block_hash = kwargs.get("block_hash", None)

    @wallet_parameter
    def set_txid(self, txid):
        self._txid = txid

    @wallet_parameter
    def set_account_id(self, account_id):
        self._account_id = normalize_account_id(
            validate_account_id(account_id)
        )

    @wallet_parameter
    def set_block_hash(self, block_hash):
        self._block_hash = validate_block_hash(block_hash)

    txid = property(lambda x: x._txid, set_txid)
    account_id = property(lambda x: x._account_id, set_account_id)
    block_hash = property(lambda x: x._block_hash, set_block_hash)


class Wallet(WalletSerializable):
    """
    Main wallet instance that can contain secret fields and be serialized
    into JSON.

    A single wallet consists of wallet properties,
    accounts (spendable or watching-only), an address book and
    a transaction list.
    """
    __slots__ = (
        "secret_key", "wallet_key", "_properties", "_encryption", "_accounts",
        "_address_book", "account_map", "transaction_map", "callbacks"
    )

    SERIALIZE_PROPS = {
        "properties": {"type": WalletProperties},
        "encryption": {"type": WalletEncryption},
        "accounts": {"list": True, "type": Account},
        "address_book": {"type": dict, "serialize": lambda x: x.to_dict()},
        "transactions": {"list": True, "type": Transaction}
    }

    def __init__(self, *args, **kwargs):
        self.secret_key = None
        self.wallet_key = None
        self.properties = kwargs.get("properties", None)
        self.encryption = kwargs.get("encryption", None)

        self.account_map = AccountIDDict()
        self.accounts = kwargs.get("accounts", [])

        self.address_book = kwargs.get("address_book", None)

        self.transaction_map = {}
        self.transactions = kwargs.get("transactions", None)

        self.callbacks = Callbacks([
            "block_confirmed", "block_rejected", "block_removed",
            "block_received", "block_added", "work_unit_completed"
        ])

    @property
    def secrets_unlocked(self):
        """
        Return True if secrets are readable on this wallet
        """
        return bool(self.secret_key) or not self.encryption.secrets_encrypted

    def unlock(self, passphrase):
        """
        Unlock the wallet and allow access to secret properties
        until the wallet is locked again with :meth:`lock`
        """
        if not self.encryption.secrets_encrypted:
            return

        secret_key = get_secret_key(
            passphrase=passphrase,
            key_type=KeyType.SECRET,
            iterations=self.encryption.key_iteration_count)

        try:
            self.encryption.secret_checksum.get(secret_key=secret_key)
        except InvalidEncryptionKey:
            raise InvalidEncryptionKey("Incorrect passphrase")

        self.secret_key = secret_key

    def lock(self):
        """
        Lock the wallet and stop access to secret properties
        """
        self.secret_key = None

    def set_wallet_encryption(self, wallet_key):
        """
        Encrypt the wallet with the given key
        """
        if self.wallet_key == wallet_key:
            raise ValueError("The wallet is already encrypted")

        validate_encryption_key(wallet_key)

        self.wallet_key = wallet_key
        self.encryption.wallet_encrypted = True
        self.encryption.wallet_checksum = Secret(
            val="VALID", secret_key=wallet_key)

    def remove_wallet_encryption(self):
        """
        Remove encryption from the wallet
        """
        if not self.wallet_key:
            raise ValueError("The wallet doesn't have encryption")

        self.wallet_key = None
        self.encryption.wallet_encrypted = False
        self.encryption.wallet_checksum = None

    @ensure_secrets_unlocked
    def set_secret_encryption(self, secret_key):
        """
        Encrypt the secret values in the wallet

        :param str secret_key: Secret key for encryption
        """
        validate_encryption_key(secret_key)

        if self.encryption.secrets_encrypted:
            if self.secret_key == secret_key:
                raise ValueError(
                    "The wallet is already encrypted with this key"
                )

            # Encryption is already in use; decrypt all existing values first
            self.decrypt_secrets(secret_key=self.secret_key)

        self.secret_key = secret_key
        self.encryption.secrets_encrypted = True
        self.encryption.secret_checksum = Secret(
            val="VALID", secret_key=secret_key)

        self.encrypt_secrets(secret_key=secret_key)

    @ensure_secrets_unlocked
    def remove_secret_encryption(self):
        """
        Remove encryption from all secrets in the wallet
        """
        self.decrypt_secrets(secret_key=self.secret_key)

        self.secret_key = None
        self.encryption.secrets_encrypted = False
        self.encryption.secret_checksum = None

    @ensure_secrets_unlocked
    def change_passphrase(
            self, passphrase, encrypt_wallet, encrypt_secrets,
            key_iteration_count=None):
        """
        Change the wallet's passphrase or remove encryption.

        If passphrase is provided, all wallet secrets will be re-encrypted.
        If not, encryption is removed entirely.

        :param str passphrase: Passphrase to encrypt the wallet with
        """
        encrypt_any = encrypt_wallet or encrypt_secrets

        if encrypt_any and not key_iteration_count:
            key_iteration_count = calculate_key_iteration_count(seconds=1)

        if not encrypt_any:
            key_iteration_count = None

        empty_passphrase = passphrase is None or passphrase == ""

        if empty_passphrase and encrypt_any:
            raise ValueError("Passphrase has to be non-empty")

        if self.encryption.secrets_encrypted:
            logger.info("Removing encryption from secret values.")
            self.remove_secret_encryption()
        if self.encryption.wallet_encrypted:
            logger.info("Removing encryption from the wallet.")
            self.remove_wallet_encryption()

        if encrypt_any:
            self.encryption.key_iteration_count = key_iteration_count

            # Set the algorithm to the default algorithm;
            # this allows encryption algorithms to be upgraded transparently
            # in the future
            self.encryption.algorithm = SecretAlgorithm.DEFAULT
        else:
            self.encryption.key_iteration_count = None
            self.encryption.algorithm = None

        if encrypt_secrets:
            logger.info("Encrypting secret values.")
            secret_key = get_secret_key(
                passphrase, key_type=KeyType.SECRET,
                iterations=key_iteration_count)
            self.set_secret_encryption(secret_key)

        if encrypt_wallet:
            logger.info("Encrypting the wallet.")
            wallet_key = get_secret_key(
                passphrase, key_type=KeyType.WALLET,
                iterations=key_iteration_count)
            self.set_wallet_encryption(wallet_key)

        return True

    @ensure_secrets_unlocked
    def remove_encryption(self):
        """
        Remove all encryption from the wallet.
        Essentially an alias for `Wallet.change_passphrase(None, False, False)`
        """
        return self.change_passphrase(
            passphrase=None, encrypt_wallet=False, encrypt_secrets=False)

    @ensure_secrets_unlocked
    def refill_accounts(self):
        """
        If the wallet has a seed and a valid gap limit, ensure
        that a correct amount of free accounts exist

        :raises ValueError: If the wallet doesn't have a seed
        """
        if not self.properties.seed and not self.properties.seed_algorithm:
            return

        free_seed_account_count = len([
            account for account in self.accounts
            if account.source == AccountSource.SEED and not account.blocks
        ])

        accounts_to_generate = (
            self.properties.gap_limit - free_seed_account_count
        )

        if accounts_to_generate > 0:
            logger.info(
                "Generating %s more accounts from seed.",
                accounts_to_generate)
            for _ in range(0, accounts_to_generate):
                self.generate_seed_account()

    @ensure_secrets_unlocked
    def generate_seed_account(self):
        """
        Generate a new account from the wallet's seed

        :raises ValueError: If the wallet doesn't have a seed
        """
        if not self.properties.seed and not self.properties.seed_algorithm:
            raise ValueError("This wallet doesn't have a seed")

        # Get the current maximum seed
        seed_accounts = [
            account for account in self.accounts
            if account.source == AccountSource.SEED
        ]

        if seed_accounts:
            # Get a sequence of seed indexes and figure out if there
            # are missing indexes in the sequence
            existing_seed_indexes = [
                account.seed_index for account in self.accounts
                if account.source == AccountSource.SEED
            ]
            existing_seed_indexes.sort()
            existing_seed_indexes = set(existing_seed_indexes)

            required_seed_indexes = set(list(range(0, len(seed_accounts))))

            missing_seed_indexes = \
                required_seed_indexes - existing_seed_indexes

            if missing_seed_indexes:
                new_seed_index = list(missing_seed_indexes)[0]
            else:
                new_seed_index = len(required_seed_indexes)
        else:
            new_seed_index = 0

        seed = self.properties.get_secret("seed", secret_key=self.secret_key)

        key_pair = generate_account_key_pair(seed, new_seed_index)
        account_id = generate_account_id(seed, new_seed_index)
        account = Account(
            account_id=account_id,
            public_key=key_pair.public,
            private_key=key_pair.private,
            seed_index=new_seed_index,
            source=AccountSource.SEED
        )
        account.encrypt_secrets(self.secret_key)

        return self.add_account(account)

    @ensure_secrets_unlocked
    def add_account_from_private_key(self, private_key):
        """
        Add a new account from a private key. If the account already
        exists as a watching-only account, private key will only be added
        instead.

        :param str private_key: Private key to add

        :raises AccountAlreadyExists: Account already exists with this private
                                      key
        :raises nanolib.exceptions.InvalidPrivateKey: Private key is invalid

        :returns: Created account
        :rtype: siliqua.wallet.accounts.Account
        """
        validate_private_key(private_key)

        key_pair = get_account_key_pair(private_key=private_key)
        account_id = get_account_id(private_key=private_key)

        if account_id in self.account_map:
            # If the account is already added but only as a watching-only
            # address, update the Account entry
            account = self.account_map[account_id]
            if not account.private_key:
                account.private_key = private_key
                account.source = AccountSource.PRIVATE_KEY
                account.encrypt_secrets(secret_key=self.secret_key)
                return account

            raise AccountAlreadyExists("Account already in the wallet")

        account = Account(
            account_id=account_id,
            public_key=key_pair.public,
            private_key=private_key,
            source=AccountSource.PRIVATE_KEY
        )
        account.encrypt_secrets(secret_key=self.secret_key)

        return self.add_account(account)

    def add_account_from_account_id(self, account_id):
        """
        Add watching-only account with an account ID.

        :param str account_id: Account ID

        :raises AccountAlreadyExists: Account already exists

        :returns: Created account
        :rtype: siliqua.wallet.accounts.Acconut
        """
        validate_account_id(account_id)

        account = Account(
            account_id=account_id,
            source=AccountSource.WATCHING)

        return self.add_account(account)

    def add_account(self, account):
        """
        Add Account instance to the wallet.

        .. note::

            Instead of calling this method directly,
            :meth:`add_account_from_private_key` and
            :meth:`add_account_from_account_id` can be used for convenience.

        :param account: Account to add
        :type account: siliqua.wallet.accounts.Account

        :raises TypeError: If `account` is not an Account instance

        :returns: Account to add
        :rtype: siliqua.wallet.accounts.Account
        """
        if not isinstance(account, Account):
            raise TypeError("Parameter isn't an Account instance")

        try:
            self.account_map[account.account_id]
            raise AccountAlreadyExists("Account already added")
        except KeyError:
            pass

        # If account doesn't have a representative, add the wallet-wide
        # default representative
        if not account.representative:
            account.representative = self.properties.representative

        self.accounts.append(account)
        self.account_map[account.account_id] = account

        return account

    def remove_account(self, account):
        """
        Remove Account instance from a wallet

        :param account: Account to remove
        :type account: siliqua.wallet.accounts.Account

        :raises TypeError: If `account` is not a valid Account
        :raises KeyError: If account is not in the wallet

        :returns: True
        """
        if not isinstance(account, Account):
            raise TypeError("Parameter isn't an Account instance")

        try:
            account = self.account_map[account.account_id]
        except KeyError:
            raise KeyError("Account not in the wallet")

        self.accounts.remove(account)
        del self.account_map[account.account_id]

        return True

    def get_block(self, block_hash):
        """
        Get a block in the wallet by its block hash

        :param str block_hash: Block hash

        :returns: Block if found, None otherwise
        :type: siliqua.wallet.accounts.Block,
               siliqua.wallet.accounts.LinkBlock
               or None
        """
        for account in self.accounts:
            if block_hash in account.block_map:
                return account.block_map[block_hash]

        return None

    def update_processed_blocks(self, block_results):
        """
        Process received block results. This may involve adding
        new blocks into accounts' blockchains or removing rejected
        non-confirmed blocks.

        :param block_results: List of :class:`siliqua.network.BlockSyncResult`
                              instances
        """
        for block_result in block_results:
            account_id = block_result.account_id
            account = self.account_map[account_id]

            if block_result.rejected:
                if block_result.error == BlockProcessError.INSUFFICIENT_WORK:
                    # Don't reject block if it only had insufficient work
                    logger.debug(
                        "Regenerating proof-of-work for rejected block "
                        "%s in account %s",
                        block_result.block_hash, account_id)
                    account.block_map[block_result.block_hash].work = None
                else:
                    logger.debug(
                        "Rejecting block %s in account %s from network",
                        block_result.block_hash, account_id)

                    account.reject_block(
                        block=block_result.block, error=block_result.error,
                        callbacks=self.callbacks
                    )
            elif block_result.confirmed:
                if block_result.block_hash in account.block_map:
                    account.confirm_block(
                        block_result.block, callbacks=self.callbacks
                    )
                else:
                    logger.debug(
                        "Adding block %s in account %s from network",
                        block_result.block_hash, account_id)
                    account.add_block(
                        block_result.block,
                        callbacks=self.callbacks
                    )

        return True

    def get_work_units_to_solve(
            self, work_difficulty, precompute_work=True):
        """
        Return a list of blocks that need to be solved in this wallet
        """
        work_units = []

        for account in self.accounts:
            # Check if we have a private key; we don't want to solve
            # watching-only blocks UNLESS they have a signature but are
            # missing work.
            has_private_key = bool(account.private_key)

            if not account.blocks:
                continue

            if account.confirmed_head:
                block = account.confirmed_head.next
            else:
                block = account.blocks[0]

            while block:
                if not has_private_key and not block.signature:
                    continue

                block.difficulty = work_difficulty

                if not block.has_valid_work:
                    work_units.append(
                        WorkUnit(
                            account_id=account.account_id,
                            block_hash=block.block_hash,
                            work_block_hash=block.work_block_hash,
                            difficulty=work_difficulty
                        )
                    )

                block = block.next

            if not precompute_work:
                continue

            if account.blocks and not account.precomputed_work:
                work_units.append(
                    WorkUnit(
                        account_id=account.account_id,
                        block_hash=None,
                        work_block_hash=account.blocks[-1].block_hash,
                    )
                )

        return work_units

    @ensure_secrets_unlocked
    def send(self, source, destination, amount, txid=None, description=None):
        """
        Send NANO from a source account to a destination account

        :param str source: Source account ID
        :param str destination: Destination account ID
        :param int amount: Amount in raw
        :param str txid: Optional transaction ID. If the same transaction ID
                         already exists in the wallet, the operation will fail.
        :param str description: Optional description for the block

        :returns: Created block
        :rtype: siliqua.wallet.accounts.Block
        """
        if txid and txid in self.transaction_map:
            raise TransactionAlreadyExists()

        account = self.account_map[source]
        block = account.send(
            account_id=destination,
            amount=amount,
            callbacks=self.callbacks
        )

        if description:
            block.description = description

        private_key = account.get_secret(
            "private_key", secret_key=self.secret_key
        )
        block.sign(private_key)

        if txid:
            self.add_transaction(
                Transaction(
                    txid=txid,
                    account_id=source,
                    block_hash=block.block_hash
                )
            )

        return block

    @ensure_secrets_unlocked
    def sign_blocks(self):
        """
        Sign all blocks that haven't been signed yet.

        :returns: List of newly signed blocks
        """
        signed_blocks = []

        for account in self.accounts:
            if not account.private_key:
                continue

            if not account.blocks:
                continue

            block = account.confirmed_head or account.blocks[0]

            while block:
                if not block.signature:
                    block.sign(
                        private_key=account.get_secret(
                            "private_key", secret_key=self.secret_key
                        )
                    )
                    signed_blocks.append(block)

                block = block.next

        if signed_blocks:
            logger.debug("Found and signed %d block(s)", len(signed_blocks))

        return signed_blocks

    def update_solved_blocks(self, work_units):
        """
        Update solved blocks by adding work from received work units

        :param list work_units: List of :class:`siliqua.work.WorkUnit`
                                instances
        """
        for work_unit in work_units:
            account_id = work_unit.account_id

            if work_unit.block_hash:
                # Work is for a block: attach it to the block
                block_hash = work_unit.block_hash
                try:
                    account = self.account_map[account_id]
                except KeyError:
                    # User might have removed the account while the block was
                    # being solved
                    continue

                try:
                    block = account.block_map[block_hash]
                except KeyError:
                    # Block might have been rejected and removed
                    continue

                block.work = work_unit.work
                block.difficulty = work_unit.difficulty

                self.callbacks.work_unit_completed.invoke(work_unit)
            else:
                # Work unit is precomputed: add it into an account
                account = self.account_map[account_id]

                if account.precomputed_work:
                    continue

                if account.blocks[-1].block_hash == work_unit.work_block_hash:
                    account.precomputed_work = PrecomputedWork(
                        work=work_unit.work,
                        difficulty=work_unit.difficulty
                    )
                    self.callbacks.work_unit_completed.invoke(work_unit)

    def update_pocketable_blocks(self, blocks):
        """
        Create new receive blocks from a list of pocketable blocks.

        :param blocks: List of :class:`siliqua.wallet.accounts.LinkBlock`
                       instances

        :returns: List of received blocks, excluding those belonging to
                  watching-only accounts
        :rtype: List[siliqua.wallet.accounts.LinkBlock]
        """
        pocketed_blocks = []

        for block in blocks:
            destination = block.recipient

            account = self.account_map[destination]
            if account.private_key:
                account.receive_block(block, callbacks=self.callbacks)
                pocketed_blocks.append(block)

        return pocketed_blocks

    def get_blocks_to_broadcast(self):
        """
        Return a list of Block instances that haven't been confirmed yet

        :returns: Unconfirmed blocks
        """
        blocks = []

        for account in self.accounts:
            if not account.blocks:
                continue

            if account.confirmed_head:
                block = account.confirmed_head
            else:
                block = account.blocks[0]

            while block:
                if not block.complete:
                    break

                if not block.confirmed:
                    blocks.append(block)

                block = block.next

        # Sort blocks to correct order if they are dependent on each
        # other.
        # Eg. when sending NANO from one wallet account to another wallet
        # account
        sort_blocks_for_broadcast(blocks)

        return blocks

    def update_broadcast_blocks(self, blocks):
        """
        Update blocks that have been broadcast

        :param blocks: List of confirmed blocks
        """
        for block in blocks:
            try:
                account = self.account_map[block.account]
            except KeyError:
                continue

            account.confirm_block(
                block,
                callbacks=self.callbacks
            )

    @property
    def balance(self):
        """
        Get the total balance of all accounts in the wallet

        :returns: Balance
        :rtype: int
        """
        return sum([account.balance for account in self.accounts])

    @classmethod
    def is_wallet_data_valid(self, data):
        """
        Check if the given wallet data dictionary is valid

        :param dict data: Wallet data as a dict

        :returns: True if valid, False otherwise
        :rtype: bool
        """
        return (
            "properties" in data.keys()
            or "wallet_data" in data.keys()
        )

    @classmethod
    def is_wallet_file_valid(cls, path):
        """
        Check if the given wallet file is valid.

        .. note::

            This method only continues reading the file until its
            validity can be determined, and should be preferred instead
            of :meth:`is_wallet_data_valid` when checking a file.

        :param str path: Path to the wallet file

        :returns: True if valid, False otherwise
        :rtype: bool
        """
        with open(path, "rb") as f:
            try:
                for pfx, _, _ in ijson.parse(f):
                    if pfx == "properties.gap_limit":
                        return True
                    if pfx == "wallet_data":
                        return True
            except ijson.JSONError:
                return False

        return False

    @classmethod
    def is_wallet_file_encrypted(cls, path):
        """
        Check if the given wallet file either has encrypted secrets or is
        encrypted entirely
        """
        if not cls.is_wallet_file_valid(path):
            raise WalletFileInvalid("Wallet file is not valid")

        with open(path, "rb") as f:
            for pfx, event, value in ijson.parse(f):
                if pfx == "key_iteration_count":
                    return True
                if pfx == "encryption.wallet_encrypted":
                    return False

        raise WalletFileInvalid(
            "Didn't find encryption settings in the wallet")

    @classmethod
    def load(self, path, passphrase=None):
        """
        Load wallet from the given path. If the wallet file is encrypted,
        passphrase has to be provided.

        :param str path: Path to the wallet file
        :param str passphrase: Optional passphrase. If the wallet file itself
                               is encrypted, this is mandatory.

        :raises WalletFileInvalid: If the wallet file is invalid
        :raises WalletLocked: If wallet is encrypted and the wallet passphrase
                              was not provided
        :raises InvalidEncryptionKey: If the passphrase is invalid

        :returns: Wallet
        :rtype: siliqua.wallet.wallet.Wallet
        """
        if not Wallet.is_wallet_file_valid(path):
            raise WalletFileInvalid("Wallet file is invalid")

        is_encrypted = Wallet.is_wallet_file_encrypted(path)

        if not passphrase and is_encrypted:
            raise WalletLocked(
                "Wallet is encrypted but passphrase was not provided"
            )

        with open(path, "r") as f:
            data = rapidjson.load(f, number_mode=rapidjson.NM_NATIVE)

        if is_encrypted:
            key_iteration_count = data["key_iteration_count"]

            secret_key = get_secret_key(
                passphrase=passphrase,
                key_type=KeyType.WALLET,
                iterations=key_iteration_count
            )

            try:
                data = Secret(
                    enc_payload=data["wallet_data"]).get(
                        secret_key=secret_key
                    )
            except InvalidEncryptionKey:
                raise InvalidEncryptionKey("Incorrect passphrase")

            data = rapidjson.loads(data, number_mode=rapidjson.NM_NATIVE)

        Wallet.check_wallet_version(data)
        wallet = Wallet.from_dict(data)

        if is_encrypted:
            wallet.wallet_key = secret_key

        return wallet

    @classmethod
    def check_wallet_version(cls, data):
        """
        Check whether the wallet data has the correct version and
        can be loaded directly
        """
        version = data["properties"]["version"]

        if version > WALLET_VERSION:
            raise UnsupportedWalletVersion(
                required_version=WALLET_VERSION,
                wallet_version=version
            )
        if version < WALLET_VERSION:
            raise WalletMigrationRequired(
                required_version=WALLET_VERSION,
                wallet_version=version
            )

    def save(self, path):
        """
        Save wallet to the given path. The wallet will be saved
        with a temporary name, and that file is renamed to (potentially)
        replace the existing file.

        :param str path: Path to the wallet file
        """
        logger.info("Saving wallet to %s", path)

        algorithm = self.encryption.algorithm

        result = self.to_dict()

        if self.encryption.wallet_encrypted:
            # If we are encrypting the entire wallet, store everything in
            # encrypted format except the encryption settings
            wallet_key = self.wallet_key
            result_bytes = bytes(rapidjson.dumps(result), "utf-8")

            encrypted_wallet_secret = Secret(
                val=result_bytes, secret_key=wallet_key, algorithm=algorithm
            ).json()
            result = self.encryption.to_dict()

            # We don't need to store information about whether the secrets
            # are encrypted as well
            if self.encryption.secrets_encrypted:
                del result["secrets_encrypted"]
                del result["secret_checksum"]

            result["wallet_data"] = encrypted_wallet_secret

        path, file_name = os.path.split(path)

        tmp_name = "{}.tmp{}".format(file_name, secrets.token_hex(4))

        # To avoid data loss, save the wallet to a temporary file and
        # then rename that file to replace the original wallet
        tmp_path = os.path.join(path, tmp_name)
        final_path = os.path.join(path, file_name)

        logger.debug("Saving wallet to temp file %s", tmp_path)
        with open(tmp_path, "w") as f:
            rapidjson.dump(result, f, indent=2)

        logger.debug("Replacing wallet with new copy")
        os.rename(tmp_path, final_path)

        logger.info("Finished saving wallet to %s", path)
        return True

    def add_transaction(self, transaction):
        """
        Add transaction to the wallet

        :param transaction: Transaction to add
        :type: siliqua.wallet.wallet.Transaction

        :raises TypeError: If the parameter isn't a Transaction instance
        :raises TransactionAlreadyExists: If transaction with the same ID
                                          already exists

        :returns: Transaction
        :rtype: siliqua.wallet.wallet.Transaction
        """
        if not isinstance(transaction, Transaction):
            raise TypeError("Parameter isn't a Transaction instance")

        if transaction.txid in self.transaction_map:
            raise TransactionAlreadyExists("Transaction already added")

        self.transactions.append(transaction)
        self.transaction_map[transaction.txid] = transaction

        return transaction

    def remove_transaction(self, transaction):
        """
        Remove a transaction from the wallet

        :param transaction: Transaction to remove
        :type transaction: siliqua.wallet.wallet.Transaction

        :raises TypeError: If the parameter isn't a Transaction
        :raises KeyError: If the transactoin doesn't exist
        """
        if not isinstance(transaction, Transaction):
            raise TypeError("Parameter isn't a Transaction instance")

        try:
            transaction = self.transaction_map[transaction.txid]
            self.transactions.remove(transaction)
            del self.transaction_map[transaction.txid]
        except KeyError:
            raise KeyError("Transaction not in the wallet")

        return True

    def add_to_address_book(self, account_id, name):
        """
        Add an account ID to the address book

        :param str account_id: Account ID
        :param str name: Name for the account ID in the address book

        :raises nanolib.InvalidAccount: If the account ID is invalid
        """
        validate_account_id(account_id)

        self.address_book[account_id] = name

    def remove_from_address_book(self, account_id):
        """
        Remove an account ID from the address book

        :param str account_id: Account ID

        :raises nanolib.InvalidAccount: If the account ID is invalid
        :raises KeyError: If the account ID is not in the address book
        """
        validate_account_id(account_id)

        if account_id not in self.address_book:
            raise KeyError("Account ID not in the address book")

        del self.address_book[account_id]

    @wallet_parameter
    def set_properties(self, properties):
        if properties is not None:
            self._properties = properties
        else:
            self._properties = WalletProperties()

    @wallet_parameter
    def set_encryption(self, encryption):
        if encryption is not None:
            self._encryption = encryption
        else:
            self._encryption = WalletEncryption()

    @wallet_parameter
    def set_accounts(self, accounts):
        if accounts is not None:
            self._accounts = []

            for account in accounts:
                self.add_account(account)
        else:
            self._accounts = []

    @wallet_parameter
    def set_address_book(self, address_book):
        if address_book is None:
            address_book = {}

        self._address_book = AccountIDDict()

        for account_id, name in address_book.items():
            self.add_to_address_book(account_id=account_id, name=name)

    @wallet_parameter
    def set_transactions(self, transactions):
        if transactions is None:
            transactions = []

        self._transactions = []

        for transaction in transactions:
            self.add_transaction(transaction)

    properties = property(lambda x: x._properties, set_properties)
    encryption = property(lambda x: x._encryption, set_encryption)
    accounts = property(lambda x: x._accounts, set_accounts)
    address_book = property(lambda x: x._address_book, set_address_book)
    transactions = property(lambda x: x._transactions, set_transactions)
