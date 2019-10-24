from datetime import datetime
from enum import Enum

from nanolib import Block as RawBlock
from nanolib import (InvalidWork, get_account_id, get_account_public_key,
                     parse_work, validate_account_id, validate_difficulty,
                     validate_private_key, validate_public_key, validate_work)
from siliqua.util import account_ids_equal, normalize_account_id

from ..util import BlockProxy
from . import logger
from .exceptions import InsufficientBalance, InvalidAccountBlock
from .secret import Secret
from .util import (HexDict, Timestamp, TimestampSource, WalletSerializable,
                   get_current_timestamp, wallet_parameter)

__all__ = (
    "AccountSource", "BlockProxy", "Account", "LinkBlock", "Block"
)

# Representative to use if no representative hasn't been assigned
EMPTY_REPRESENTATIVE = \
    "xrb_1111111111111111111111111111111111111111111111111111hifc8npp"


class AccountSource(Enum):
    SEED = "seed"
    PRIVATE_KEY = "private"
    WATCHING = "watching"


class LinkBlock(WalletSerializable, BlockProxy):
    """
    Link block is a pocketed block that's included with
    :attr:`Block.link_block` when applicable.

    This allows the pocketed block to be timestamped separately
    from the account block that pockets the block
    """
    __slots__ = (
        "_block", "_amount", "_account_id", "_timestamp"
    )

    SERIALIZE_PROPS = {
        "block_data": {"type": dict, "required": True},
        "amount": {
            "type": str, "required": True, "serialize": str
        },
        "timestamp": {"type": Timestamp},
    }

    def __init__(
            self, amount, block=None, block_data=None,
            timestamp=None, verify=False):
        """
        Either `block` or `block_data` keyword argument must be provided,
        but not both.

        :param int amount: Amount sent in this link block
        :param block: Block instance
        :type block: nanolib.Block
        :param dict block_data: Block data as a dict
        :param timestamp: Timestamp for the link block
        :type timestamp: siliqua.wallet.util.Timestamp
        :param bool verify: Whether to verify the link block's signature and
                            PoW
        """
        if block_data and block:
            raise ValueError("Only 'block_data' or 'block' is accepted")

        if block_data:
            self.block_data = block_data
        elif block:
            self.block_data = block.to_dict()
        else:
            raise ValueError("'block_data' or 'block' is required")

        if verify:
            if self.block.signature:
                self.block.verify_signature()
            if self.block.work:
                self.block.verify_work()

        self.amount = int(amount)
        self.timestamp = timestamp

    @property
    def recipient(self):
        """
        Recipient of NANO sent in this block

        :return: Account ID
        :rtype: str
        """
        if self.block_type == "send":
            return self.destination
        if self.block.tx_type == "send/receive":
            return self.link_as_account

        raise ValueError("Block is not send block")

    @property
    def block(self):
        """
        Underlying :class:`nanolib.Block` instance
        """
        return self._block

    @wallet_parameter
    def set_block_data(self, block_data):
        if not block_data:
            raise ValueError("Property is required")

        self._block = RawBlock.from_dict(block_data, verify=False)

    @wallet_parameter
    def set_amount(self, amount):
        self._amount = int(amount)

    @wallet_parameter
    def set_timestamp(self, timestamp):
        if timestamp:
            self._timestamp = timestamp
        else:
            self._timestamp = None

    block_data = property(lambda x: x._block.to_dict(), set_block_data)
    amount = property(lambda x: x._amount, set_amount)
    timestamp = property(lambda x: x._timestamp, set_timestamp)


class Block(WalletSerializable, BlockProxy):
    """
    Block associated with wallet account.

    In addition to the block data itself, Block instances also contain
    a timestamp, the pocketed block (if applicable) and an optional
    description field
    """
    __slots__ = (
        "_block", "_description", "_timestamp", "_confirmed", "_balance",
        "prev", "next"
    )

    SERIALIZE_PROPS = {
        "block_data": {"type": dict, "required": True},
        "link_block": {"type": LinkBlock},
        "description": {"type": str},
        "timestamp": {"type": Timestamp},
        "confirmed": {"type": bool}
    }

    def __init__(
            self, block_data=None, block=None, link_block=None,
            description=None, timestamp=None, confirmed=True):
        """
        Either `block` or `block_data` has to be provided, but not both.

        :param dict block_data: Block data as a dict
        :param block: Block instance
        :type block: nanolib.Block
        :param link_block: Link block, if the block pocketed another block
        :type link_block: LinkBlock
        :param str description: Optional description
        :param timestamp: Timestamp of the block
        :type timestamp: siliqua.wallet.util.Timestamp
        :param bool confirmed: Is the block confirmed
        """
        if block_data and block:
            raise ValueError("Only 'block_data' or 'block' is accepted")

        if block_data:
            self.block_data = block_data
        elif block:
            self.block_data = block.to_dict()
        else:
            raise ValueError("'block_data' or 'block' is required")

        self.link_block = link_block
        self.description = description
        self.timestamp = timestamp
        self.confirmed = confirmed

        self._balance = None

        self.prev = None
        self.next = None

    @property
    def balance(self):
        """
        Account balance as of this block

        :return: Balance
        :rtype: int
        """
        if self.block.block_type in ("state", "send"):
            return self.block.balance
        if self.block.block_type == "open":
            return self.link_block.amount

        # Store balance in '_balance' attribute to prevent backtracking.
        # Otherwise, a long sequence of receive blocks would cause a
        # RecursionError due to the required backtracking.
        #
        # Each block's balance is retrieved when the block is added to the
        # account, so we can be sure the previous block's balance
        # returns the value in its '_balance' field immediately
        if self._balance is not None:
            return self._balance
        if self.block.block_type == "receive":
            self._balance = self.prev.balance + self.link_block.amount
            return self._balance

        self._balance = self.prev.balance
        return self._balance

    @property
    def amount(self):
        """
        The amount transacted in this block.

        :return: Amount transacted
        :rtype: int
        """
        if self.block.tx_type == "open":
            return self.balance
        if self.block_type == "send":
            # For legacy send blocks, use the 'balance' field in the underlying
            # block
            return self.block.balance - self.prev.balance

        return self.balance - self.prev.balance

    @property
    def tx_type(self):
        """
        The transaction type for this block.

        Possible values are identical as with
        :attr:`nanolib.blocks.Block.tx_type` except that
        `send` or `receive` is returned instead of `send/receive` when
        applicable.
        """
        if self.amount > 0:
            if self.block.tx_type == "open":
                return "open"
            return "receive"
        if self.amount < 0:
            return "send"

        return self.block.tx_type

    @property
    def block(self):
        """
        The underlying :class:`nanolib.Block` instance

        :return: Block
        :rtype: nanolib.Block
        """
        return self._block

    @wallet_parameter
    def set_block_data(self, block_data):
        if not block_data:
            raise ValueError("Property is required")

        self._block = RawBlock.from_dict(block_data, verify=False)

    @wallet_parameter
    def set_link_block(self, link_block):
        if link_block:
            self._link_block = link_block
        else:
            self._link_block = None

    @wallet_parameter
    def set_description(self, description):
        if description:
            self._description = description
        else:
            self._description = None

    @wallet_parameter
    def set_timestamp(self, timestamp):
        if timestamp:
            self._timestamp = timestamp
        else:
            self._timestamp = None

    @wallet_parameter
    def set_confirmed(self, confirmed):
        if confirmed in (True, False):
            self._confirmed = confirmed
        else:
            raise ValueError("Value has to be a boolean")

    def __deepcopy__(self, memodict):
        kwargs = {
            "block_data": self.block_data,
            "description": self.description,
            "confirmed": self.confirmed
        }

        if self.timestamp:
            kwargs["timestamp"] = Timestamp.from_dict(self.timestamp.to_dict())

        if self.link_block:
            kwargs["link_block"] = LinkBlock.from_dict(
                self.link_block.to_dict()
            )

        return Block(**kwargs)

    block_data = property(lambda x: x._block.to_dict(), set_block_data)
    link_block = property(lambda x: x._link_block, set_link_block)
    description = property(lambda x: x._description, set_description)
    timestamp = property(lambda x: x._timestamp, set_timestamp)
    confirmed = property(lambda x: x._confirmed, set_confirmed)


class PrecomputedWork(WalletSerializable):
    """
    Precomputed work object consisting of the work nonce and the difficulty
    it meets.
    """
    __slots__ = (
        "_work", "_difficulty"
    )

    SERIALIZE_PROPS = {
        "work": {"type": str},
        "difficulty": {"type": str}
    }

    def __init__(self, work=None, difficulty=None):
        self.work = work
        self.difficulty = difficulty

    @wallet_parameter
    def set_work(self, work):
        if work:
            self._work = parse_work(work)
        else:
            self._work = None

    @wallet_parameter
    def set_difficulty(self, difficulty):
        if difficulty:
            self._difficulty = validate_difficulty(difficulty)
        else:
            self._difficulty = None

    def __bool__(self):
        return bool(self.work and self.difficulty)

    work = property(lambda x: x._work, set_work)
    difficulty = property(lambda x: x._difficulty, set_difficulty)


class Account(WalletSerializable):
    """
    Wallet account that can be spendable or reading-only. The account
    object also contains the entire account blockchain.
    """
    __slots__ = (
        "_account_id", "_private_key", "_representative",
        "_name", "_seed_index", "_source", "_blocks", "_precomputed_work",
        "balance", "confirmed_head", "received_block_hashes", "block_map"
    )

    SERIALIZE_PROPS = {
        "account_id": {"type": str, "required": True, "secret": False},
        "private_key": {"type": str, "required": False, "secret": True},
        "representative": {"type": str},
        "name": {"type": str},
        "seed_index": {"type": int},
        "source": {"type": AccountSource, "required": True, "secret": False},
        "blocks": {"list": True, "type": Block, "secret": False},
        "precomputed_work": {"type": PrecomputedWork}
    }

    def __init__(self, *args, **kwargs):
        self.account_id = kwargs.get("account_id", None)
        self.private_key = kwargs.get("private_key", None)
        self.name = kwargs.get("name", None)
        self.source = kwargs.get("source", None)
        self.representative = kwargs.get("representative", None)
        self.seed_index = kwargs.get("seed_index", None)

        self.received = {}

        # The latest confirmed block that has been stored in the block
        # lattice
        self.confirmed_head = None
        self.balance = 0
        self.received_block_hashes = set()
        self.precomputed_work = None
        self.block_map = HexDict()

        self.blocks = kwargs.get("blocks", None)
        self.precomputed_work = kwargs.get("precomputed_work", None)

    @property
    def public_key(self):
        return get_account_public_key(account_id=self.account_id)

    @property
    def representative_to_add(self):
        """
        Return the account representative, representative of the newest
        block or the fallback representative (burn account),
        whichever is available first

        This ensures that some representative can be used for new blocks
        """
        if self.representative:
            return self.representative

        if self.blocks:
            return self.blocks[-1].representative

        return EMPTY_REPRESENTATIVE

    def add_block(self, block, callbacks=None):
        if not isinstance(block, Block):
            raise TypeError("Argument has to be a Block instance")

        if not account_ids_equal(block.account, self.account_id):
            raise InvalidAccountBlock(
                "The block doesn't belong to this account's blockchain"
            )

        if not self.blocks:
            # The first block has to be an open block
            if block.tx_type != "open":
                raise InvalidAccountBlock(
                    "First block for an account has to be an 'open' block"
                )

            if block.confirmed:
                self.confirmed_head = block
        else:
            # Attach the block to the previous block
            prev_block = self.blocks[-1]

            if block.previous != prev_block.block_hash:
                raise InvalidAccountBlock(
                    "Block isn't a successor to the current head."
                )

            if prev_block.block_type == "state" \
                    and block.block_type != "state":
                raise InvalidAccountBlock(
                    "State block can't be followed by a legacy block"
                )

            block.prev = prev_block
            prev_block.next = block

            if prev_block.confirmed and block.confirmed:
                self.confirmed_head = block

        # Update balance
        if block.block_type == "state":
            self.balance = block.balance
        else:
            self.balance += block.amount

        if block.link_block:
            self.received_block_hashes.add(block.link_block.block_hash)
            self.block_map[block.link_block.block_hash] = block.link_block

        self.blocks.append(block)
        self.block_map[block.block_hash] = block

        if callbacks:
            callbacks.block_added.invoke(block)

    def attach_precomputed_work(self, block):
        """
        Add the precomputed work to a new block if it is available
        and valid. In either case, discard the precomputed work afterwards.
        """
        if self.precomputed_work:
            try:
                validate_work(
                    block_hash=block.work_block_hash,
                    work=self.precomputed_work.work,
                    difficulty=self.precomputed_work.difficulty
                )
                is_valid_work = True
            except InvalidWork:
                is_valid_work = False

            if is_valid_work:
                block.difficulty = self.precomputed_work.difficulty
                block.work = self.precomputed_work.work
            else:
                logger.warning("Invalid precomputed work found, discarding.")

            self.precomputed_work = None

    def receive_block(self, link_block, callbacks=None):
        """
        Pocket a link block by creating a new block in the blockchain
        """
        if link_block.block_hash in self.received_block_hashes:
            # If the block is already pocketed, return None.
            # This can happen during network sync and is safe to ignore
            return None

        if not self.blocks:
            # Open the account
            raw_block = RawBlock(
                block_type="state",
                account=self.account_id,
                previous=None,
                representative=self.representative_to_add,
                balance=link_block.amount,
                link=link_block.block_hash
            )
        else:
            prev_block = self.blocks[-1]

            raw_block = RawBlock(
                block_type="state",
                account=self.account_id,
                previous=prev_block.block_hash,
                representative=self.representative_to_add,
                balance=self.balance + link_block.amount,
                link=link_block.block_hash
            )

        block = Block(
            block=raw_block,
            link_block=link_block,
            confirmed=False,
            timestamp=get_current_timestamp()
        )

        self.attach_precomputed_work(block)
        self.add_block(block, callbacks=callbacks)

        if callbacks:
            callbacks.block_received.invoke(block.link_block)

        return block

    def reject_block(self, block, error, callbacks=None):
        """
        Remove a rejected non-confirmed block from the account blockchain.

        This can happen if we're trying to pocket a block before the node
        we're connected to has finished syncing the account blockchain.
        In this case, remove the generated receive block and try
        pocketing the pending block later.
        """
        block_hash = block.block_hash
        logger.warning(
            "Rejecting block %s for account %s", block_hash, self.account_id)

        # Get the account-specific block instance
        try:
            block = self.block_map[block.block_hash]
        except KeyError:
            # Block was probably already rejected
            return

        if block.confirmed:
            logger.error("Trying to reject confirmed block %s", block_hash)
            raise ValueError("Can't reject a confirmed block")

        if callbacks:
            callbacks.block_rejected.invoke(block, error)

        self.remove_block(block, callbacks=callbacks)

    def remove_block(self, block, callbacks=None):
        """
        Remove a block from the account blockchain including any of its
        successors.

        Most of the time this shouldn't be called directly.
        Instead, :meth:`Block.reject_block` can be used to
        remove non-confirmed blocks that were not accepted by the network.
        """
        orig_block_hash = block.block_hash
        block = self.block_map[orig_block_hash]
        if block.confirmed and block.prev:
            self.confirmed_head = block.prev

        # Truncate the list of blocks
        self.blocks = self.blocks[0:self.blocks.index(block)]

        block_count = 0
        while block:
            block_hash = block.block_hash

            if callbacks:
                callbacks.block_removed.invoke(block)

            if block.prev:
                block.prev.next = None
            block.prev = None
            del self.block_map[block_hash]

            if block.link_block:
                del self.block_map[block.link_block.block_hash]
                self.received_block_hashes.remove(block.link_block.block_hash)

            block = block.next
            block_count += 1

        logger.warning(
            "Removed block %s from account %s, including %s block(s) after it",
            orig_block_hash, self.account_id, block_count-1
        )

        return True

    def send(self, account_id, amount, callbacks=None):
        """
        Create a send block and add it to the blockchain

        :param str account_id: Destination account ID
        :param amount: Amount to send
        :type amount: int or str
        :param callbacks: Optional set of callbacks
        :type callbacks: siliqua.util.Callbacks

        :returns: Created block
        :rtype: siliqua.wallet.accounts.Block
        """
        if not self.private_key:
            raise ValueError("Private key required to send")

        # TODO: Decimals are also accepted implicitly here.
        if isinstance(amount, float):
            raise TypeError("Floating numbers are not allowed")

        if isinstance(amount, str) and not amount.isdigit():
            raise ValueError("Strings can only contain an integer")

        validate_account_id(account_id)

        amount = int(amount)

        if amount < 1:
            raise ValueError("Value must be at least 1 raw")

        if self.balance < amount:
            raise InsufficientBalance(
                "Insufficient balance to perform transaction")

        head_block = self.blocks[-1]

        raw_block = RawBlock(
            block_type="state",
            account=self.account_id,
            previous=head_block.block_hash,
            representative=self.representative_to_add,
            balance=self.balance - amount,
            link_as_account=account_id
        )
        block = Block(
            block=raw_block,
            confirmed=False,
            timestamp=get_current_timestamp()
        )

        self.attach_precomputed_work(block)
        self.add_block(block, callbacks=callbacks)

        return block

    def change_representative(self, representative, callbacks=None):
        """
        Change the account representative. A new block is also appended
        to the blockchain unless the account is empty.

        :param str representative: Representative account ID
        :param callbacks: Optional set of callbacks to run
        :type callbacks: siliqua.util.Callbacks

        :return: Block instance if block was created, otherwise True
        :rtype: siliqua.wallet.accounts.Block or None
        """
        if account_ids_equal(self.representative_to_add, representative):
            raise ValueError(
                "The representative is already assigned for this account"
            )

        validate_account_id(representative)

        if self.blocks:
            # If we have opened this account already,
            # create a change block and add the representative
            # If not, store the representative
            # and use it later when this account is opened
            representative_to_add = (
                representative if representative else
                EMPTY_REPRESENTATIVE
            )
            head_block = self.blocks[-1]

            raw_block = RawBlock(
                block_type="state",
                account=self.account_id,
                previous=head_block.block_hash,
                representative=representative_to_add,
                balance=head_block.balance,
                link=None)
            block = Block(
                block=raw_block,
                confirmed=False,
                timestamp=get_current_timestamp()
            )

            self.attach_precomputed_work(block)
            self.add_block(block, callbacks=None)

            self.representative = representative
            return block
        else:
            self.representative = representative
            return True

    def update_confirmed_head(self):
        """
        Check if the latest confirmed block has changed and update
        the `confirmed_head` property accordingly
        """
        if not self.blocks:
            return

        block = self.confirmed_head or self.blocks[0]

        while block:
            if block.confirmed:
                self.confirmed_head = block
            else:
                break

            block = block.next

    def confirm_block(self, block, callbacks=None):
        """
        Confirm the given block. Confirmed blocks cannot be rejected
        anymore.

        :param block: Block to confirm
        :type block: siliqua.wallet.accounts.Block
        """
        block_hash = block.block_hash

        account_block = self.block_map[block_hash]

        if not account_block.complete:
            raise ValueError("Block to confirm isn't complete")

        if account_block.prev and not account_block.prev.confirmed:
            raise ValueError("Previous block is not confirmed")

        if account_block.confirmed:
            # Block was already confirmed
            return

        logger.debug(
            "Confirmed block %s for account %s, height %d",
            block.block_hash, self.account_id, self.blocks.index(account_block)
        )
        account_block.confirmed = True
        self.update_confirmed_head()

        if callbacks:
            callbacks.block_confirmed.invoke(block)

    @wallet_parameter
    def set_account_id(self, account_id):
        self._account_id = normalize_account_id(
            validate_account_id(account_id)
        )

    @wallet_parameter
    def set_private_key(self, private_key, is_secret):
        if private_key:
            if not is_secret:
                validate_private_key(private_key)

            self._private_key = private_key
        else:
            self._private_key = None

    @wallet_parameter
    def set_representative(self, representative):
        if representative:
            self._representative = normalize_account_id(
                validate_account_id(representative)
            )
        else:
            self._representative = None

    @wallet_parameter
    def set_name(self, name):
        if name:
            self._name = str(name)
        else:
            self._name = None

    @wallet_parameter
    def set_seed_index(self, seed_index):
        if seed_index is not None:
            seed_index = int(seed_index)

            if seed_index < 0:
                raise ValueError("Positive integer is required")
            self._seed_index = seed_index
        else:
            self._seed_index = None

    @wallet_parameter
    def set_source(self, source):
        self._source = AccountSource(source)

    @wallet_parameter
    def set_blocks(self, blocks):
        if blocks is None:
            blocks = []

        self._blocks = []

        for block in blocks:
            # Add each block in order so we can perform other operations at
            # the same time (eg. calculating balance,
            # check if the blockchain is valid...)
            self.add_block(block)

    @wallet_parameter
    def set_precomputed_work(self, precomputed_work):
        if precomputed_work:
            self._precomputed_work = precomputed_work
        else:
            self._precomputed_work = PrecomputedWork()

    account_id = property(lambda x: x._account_id, set_account_id)
    private_key = property(lambda x: x._private_key, set_private_key)
    representative = property(lambda x: x._representative, set_representative)
    name = property(lambda x: x._name, set_name)
    seed_index = property(lambda x: x._seed_index, set_seed_index)
    source = property(lambda x: x._source, set_source)
    blocks = property(lambda x: x._blocks, set_blocks)
    precomputed_work = property(
        lambda x: x._precomputed_work, set_precomputed_work)
