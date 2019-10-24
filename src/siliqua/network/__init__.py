import copy
import time
from collections import OrderedDict
from enum import Enum
from multiprocessing import Manager
from queue import Empty, Queue
from threading import Lock

from nanolib import WORK_DIFFICULTY
from siliqua.exceptions import InsufficientConfiguration
from siliqua.plugins import BasePlugin, get_network_plugins
from siliqua.util import AccountIDDict, BlockProxy, normalize_account_id

from siliqua import logger as root_logger  # isort:skip
logger = root_logger.getChild("network")


__all__ = (
    "AccountSyncStatus", "ConnectionStatus", "BlockSyncResult",
    "BlockSetQueue", "BaseNetworkPlugin"
)


class AccountSyncStatus:
    """
    Account sync status.

    Sync status is tracked to determine when account has finished syncing and
    is therefore ready to pocket pending NANO.

    :ivar str account_id: Account ID being tracked
    :ivar str wallet_head: Block hash of latest block in the local wallet
    :ivar str network_head: Block hash of last block retrieved from the network
    :ivar bool sync_complete: Whether sync is complete.
                              This means that no new blocks were found during
                              the last round of updates.
    :ivar timestamp: Timestamp for the last check
    """
    def __init__(self, account_id, head_hash=None):
        self.account_id = normalize_account_id(account_id)

        self.wallet_head = head_hash
        self.network_head = head_hash
        self.sync_complete = False

        self.timestamp = None

    def update_timestamp(self):
        self.timestamp = time.time()

    @property
    def ready_to_pocket(self):
        """
        Whether this account is ready to pocket pending blocks.

        Network and wallet head must match and sync must be complete.
        """
        return self.wallet_head == self.network_head and self.sync_complete

    @property
    def seconds_since_timestamp(self):
        if self.timestamp:
            return time.time() - self.timestamp

        return time.time()


class ConnectionStatus:
    """
    Connection status to the NANO network

    :ivar bool connected: Whether connection has been established to the
                          network (this may mean a NANO node)
    :ivar bool aborted: If the connection was aborted due to a fatal error.
    :ivar timestamp: Timestamp of the last successful request to the network
    :ivar error: Exception that caused the connection to be aborted.
                 This is available if :attr:`aborted` is True
    :ivar int completed_rounds: How many rounds of updates have been completed
    :ivar bool sync_complete: Whether the network plugin has finished syncing
                              all accounts
    :ivar dict meta: Dictionary that can be used to hold arbitrary
                     connection-related information
    """
    def __init__(self):
        self.connected = False
        self.aborted = False
        self.timestamp = None
        self.error = None

        self.completed_rounds = 0
        self.sync_complete = False

        self.meta = {}

    def update(self, connected):
        """
        Update the connection status.

        This is called when any response has been completed, regardless
        of whether it succeeded or failed

        :param bool connected: Whether the connection has been established
        """
        if self.aborted:
            # If the connection has already been aborted, disregard
            # any lingering requests that pass
            return

        self.connected = connected
        self.aborted = False
        self.timestamp = time.time()

        self.error = None

    def abort(self, error=None):
        """
        Mark the connection as aborted.

        :param error: Exception that caused the connection to be aborted
        """
        self.connected = False
        self.aborted = True
        self.timestamp = time.time()

        self.error = error


class BlockProcessError(Enum):
    """
    Error that caused block broadcast to fail
    """
    SOURCE_BLOCK_MISSING = "source_block_missing"
    PREVIOUS_BLOCK_MISSING = "previous_block_missing"
    UNRECEIVABLE = "unreceivable"
    FORK = "fork"
    PREVIOUS_BLOCK_REJECTED = "previous_block_rejected"
    # The node already has the given block.
    # This doesn't mean the block is confirmed.
    BLOCK_ALREADY_PROCESSED = "block_already_processed"
    INSUFFICIENT_WORK = "insufficient_work"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


ERRORS_TO_ENUM = {
    "Gap source block": BlockProcessError.SOURCE_BLOCK_MISSING,
    "Gap previous": BlockProcessError.PREVIOUS_BLOCK_MISSING,
    "Unreceivable": BlockProcessError.UNRECEIVABLE,
    "Fork": BlockProcessError.FORK,
    "Block work is less than threshold": BlockProcessError.INSUFFICIENT_WORK,
    "Old block": BlockProcessError.BLOCK_ALREADY_PROCESSED
}


class BlockSyncResult(BlockProxy):
    """
    Result of a block that has been received from or broadcast on the network.

    Block can be confirmed or rejected; in latter case,
    :class:`BlockProcessError` is provided.

    :ivar bool confirmed: Is the block confirmed
    :ivar bool rejected: Is the block rejected
    :ivar block: Block instance
    :ivar error: :class:`BlockProcessError` instance, if the block was rejected
    """
    __slots__ = ("confirmed", "rejected", "block", "error")

    def __init__(self, block, confirmed=False, rejected=False, error=None):
        if sum([confirmed, rejected]) != 1:
            raise ValueError("'confirmed' or 'rejected' has to be True")

        self.confirmed = confirmed
        self.rejected = rejected

        self.error = None

        if error:
            try:
                self.error = ERRORS_TO_ENUM[error]
            except KeyError:
                try:
                    self.error = BlockProcessError(error)
                except KeyError:
                    self.error = BlockProcessError("unknown")

        self.block = block
        self.block.confirmed = confirmed


class BlockSetQueue(Queue):
    """
    FIFO queue that accepts Block instances
    """
    def _init(self, maxsize=None):
        self.queue = OrderedDict()

    def _put(self, block):
        block_hash = block.block_hash

        self.queue[block_hash] = block

    def _get(self):
        return self.queue.popitem(False)[1]

    def remove(self, block):
        """
        Remove specific block from the queue

        :returns: Returned block or None if no block was removed
        """
        return self.queue.pop(block.block_hash, None)


class BaseNetworkPlugin(BasePlugin):
    """
    Base class used for network plugins.

    Each network plugin has three queues to transmit blocks between the
    :class:`siliqua.server.WalletServer` instance and the network:

    - :attr:`processed_block_queue`

      - confirmed blocks that have been retrieved from the network

    - :attr:`siliqua.network.BaseNetworkPlugin.pocketable_block_queue`

      - blocks that can be pocketed by accounts currently in the wallet

    - :attr:`siliqua.network.BaseNetworkPlugin.broadcast_block_queue`

      - blocks that currently only exist in the wallet and can be confirmed by
        broadcasting them into the network

    :attr:`siliqua.network.BaseNetworkPlugin.account_sync_statuses`
    is a mapping of account IDs to :class:`siliqua.network.AccountSyncStatus`
    instances to keep track of accounts that belong to the wallet
    and which may need syncing.
    """
    PLUGIN_TYPE = "network"

    def __init__(self, **kwargs):
        super(BaseNetworkPlugin, self).__init__(**kwargs)

        self.processed_block_queue = BlockSetQueue()
        self.pocketable_block_queue = BlockSetQueue()
        self.broadcast_block_queue = BlockSetQueue()
        self.broadcast_queue_lock = Lock()

        self.connection_status = ConnectionStatus()

        self.account_sync_statuses = AccountIDDict()

        self.manager = None

    work_difficulty = WORK_DIFFICULTY

    @property
    def started(self):
        """
        :return: Is the network plugin started
        :rtype: bool
        """
        raise NotImplementedError

    @property
    def connected(self):
        """
        :return: Is the network plugin connected to the NANO network
        :rtype: bool
        """
        return self.connection_status.connected

    def _stop(self):
        """
        Stop the network server.

        .. note::

            Override this method to implement the actual stop process.
            :meth:`BaseNetworkPlugin.stop` can then be used to stop the plugin
            in actual code.

        """
        raise NotImplementedError

    def stop(self):
        """
        Stop the network server.
        """
        if not self.started:
            raise ValueError("The network server is not running")

        self._stop()

    def _start(self):
        """
        Start the network plugin.

        .. note::

            Override this method to implement the actual stop process.
            :meth:`BaseNetworkPlugin.stop` can then be used to stop the plugin
            in actual code.
        """
        raise NotImplementedError

    def start(self):
        """
        Start the network plugin
        """
        if not self.is_config_valid:
            raise ValueError("The network server hasn't been configured")

        if self.started:
            raise ValueError("The network server is already running")

        self._start()

    def reload(self):
        """
        Reload the network plugin
        """
        self.stop()
        self.start()

    def _get_from_queue(self, queue):
        """
        Get all the values in a queue
        """
        items = []

        while True:
            try:
                items.append(queue.get_nowait())
            except Empty:
                break

        return items

    def wait_for_connection(self, timeout=5):
        """
        Wait until the running node has made a successful request

        :raises ValueError: If the network plugin is stopped
        :raises TimeoutError: If connection can't be established in given time
        """
        if not self.started:
            raise ValueError("The network server is not running")

        start = time.time()
        current = time.time()

        while current < (start + timeout):
            if self.connection_status.error:
                raise self.connection_status.error

            if self.connection_status.connected:
                return True

            current = time.time()
            time.sleep(0.1)

        raise TimeoutError()

    def get_processed_blocks(self):
        """
        Get all the processed blocks from the queue

        :return: List of processed blocks
        """
        return self._get_from_queue(self.processed_block_queue)

    def get_pocketable_blocks(self):
        """
        Get all the pocketable blocks from the queue

        :return: List of pocketable blocks
        """
        return self._get_from_queue(self.pocketable_block_queue)

    def add_blocks_to_broadcast(self, blocks):
        """
        Add blocks into the broadcast queue to be eventually broadcast
        into the network

        :param blocks: List of blocks to broadcast
        :type blocks: List[siliqua.wallet.accounts.Block]
        """
        with self.broadcast_queue_lock:
            for block in blocks:
                self.broadcast_block_queue.put(copy.deepcopy(block))

        return True

    def update_accounts_to_sync(self, wallet):
        """
        Update the list of account IDs to sync from the wallet

        :param wallet: Wallet containing accounts to sync
        :type wallet: siliqua.wallet.Wallet
        """
        # Add accounts that don't exist
        for account in wallet.accounts:
            if account.account_id not in self.account_sync_statuses:
                self.account_sync_statuses[account.account_id] = \
                    AccountSyncStatus(
                        account_id=account.account_id,
                        head_hash=(
                            account.confirmed_head.block_hash
                            if account.confirmed_head else None
                        )
                    )

        # Remove accounts no longer in the wallet
        for account_id in self.account_sync_statuses.keys():
            try:
                wallet.account_map[account_id]
            except KeyError:
                del self.account_sync_statuses[account_id]


# TODO: We could scan the directories for built-in GUI plugins, but for now
# just import them directly
from .nano_node import *  # isort:skip
from .nanovault import *  # isort:skip
