"""
:class:`siliqua.server.WalletServer` comprises
of a wallet, network provider and a work provider to provide a functional
wallet. It provides methods for common operations such as sending NANO
and adding new accounts to the wallet.

WalletServer is designed to be run in the same thread with the GUI thread,
with the instance responsible for launching new threads for network and
work threads and managing the communication between them. This is
done for the most part by calling the :meth:`siliqua.server.WalletServer.update`
in the GUI thread when the user is not using the wallet (eg. sending NANO).
"""
from siliqua import logger as root_logger  # isort:skip
logger = root_logger.getChild("server")

import json
import time
from collections import OrderedDict

import filelock
from siliqua.exceptions import WalletFileLocked
from siliqua.network import BlockProcessError
from siliqua.wallet import Wallet
from nanolib.work import derive_work_difficulty


class WaitResult:
    """
    Wait result for a single block

    A block may be either confirmed, rejected or timed out.

    A timed out block is neither confirmed or rejected.
    A timeout just means that Siliqua has stopped waiting for the block's
    resolution, and that the block might become confirmed or get rejected
    in the network later.
    """
    def __init__(
            self, block, confirmed=False, rejected=False, timeout=False,
            error=None):
        """
        :param block: Block instance
        :type block: siliqua.wallet.accounts.Block
        :param bool confirmed: Whether the block was confirmed
        :param bool rejected: Whether the block was rejected. If True,
                              `error` parameter should also be provided
        :param bool timeout: Whether the block timed out. If True,
                             `confirmed` and `rejected` should be False.
        :param error: BlockProcessError instance
        :type error: siliqua.network.BlockProcessError
        """
        self.block = block
        self.confirmed = confirmed
        self.rejected = rejected
        self.timeout = timeout
        self.error = error


class MultipleWaitResult:
    """
    A compilation of multiple WaitResult instances
    """
    def __init__(self, wait_results, complete):
        """
        :param wait_results: List of :class:`WaitResult` instances
        :param bool complete: Whether all wait results have either been
                              confirmed or rejected
        """
        self.complete = complete

        self.wait_results = []
        for wait_result in wait_results:
            self.wait_results.append(wait_result)

    @property
    def confirmed_results(self):
        """
        Returns all confirmed WaitResult instances

        :rtype: List[WaitResult]
        """
        return [
            wait_result for wait_result in self.wait_results
            if wait_result.confirmed
        ]

    @property
    def rejected_results(self):
        """
        Returns all rejected WaitResult instances

        :rtype: List[WaitResult]
        """
        return [
            wait_result for wait_result in self.wait_results
            if wait_result.rejected
        ]


class WalletServer(object):
    """
    A server comprising a wallet, network provider and work provider
    to provide a functioning wallet
    """
    def __init__(self, config, work, network, wallet):
        """
        :param config: Config instance
        :type config: siliqua.config.Config
        :param work: Work provider subclassed from
                     :class:`siliqua.work.BaseWorkPlugin`
        :type work: siliqua.work.BaseWorkPlugin or None
        :param network: Network provider subclassed from
                     :class:`siliqua.network.BaseNetworkPlugin`
        :type network: siliqua.network.BaseNetworkPlugin or None
        :param wallet: Wallet instance
        :type wallet: siliqua.wallet.Wallet or None
        """
        self.config = config

        self.wallet = wallet
        self.work = work
        self.network = network

        self.work_finished = False
        self.network_finished = False

        self.wallet_path = None
        self.wallet_lock = None

    @property
    def ready(self):
        """
        Is the server fully usable (eg. work and network providers
        are up and running)

        :returns: True if the server is usable, False otherwise
        :rtype: bool
        """
        return bool(
            self.work and self.work.ready
            and self.network and self.network.ready
        )

    def start_work(self):
        """
        Start the work provider
        """
        self.work.start()

    def start_network(self):
        """
        Start the network provider
        """
        self.network.start()

    def stop(self):
        """
        Stop work and network providers and close the wallet
        """
        try:
            self.stop_work()
        except ValueError:
            pass

        try:
            self.stop_network()
        except ValueError:
            pass

        if self.wallet_lock:
            self.close_wallet()

    def stop_work(self):
        """
        Stop the work provider
        """
        self.work.stop()

    def stop_network(self):
        """
        Stop the network provider
        """
        self.network.stop()

    def load_wallet(self, path, passphrase=None):
        """
        Load a wallet from the given path

        :raises WalletFileLocked: If the wallet file is already in use by
                                  another app instance

        """
        if self.wallet_lock:
            self.wallet_lock.release()

        self.wallet_lock = filelock.FileLock("{}.lock".format(path), timeout=0)

        try:
            self.wallet_lock.acquire()
        except filelock.Timeout:
            raise WalletFileLocked(
                "The wallet file is in use by another Siliqua instance"
            )

        wallet = Wallet.load(path, passphrase=passphrase)

        self.wallet = wallet
        self.wallet_path = path

    def save_wallet(self):
        """
        Save the wallet data
        """
        self.wallet.save(self.wallet_path)

    def close_wallet(self):
        """
        Closes the wallet by unlocking the corresponding lock file
        """
        self.wallet_lock.release()
        self.wallet_lock = None

    def send_from(
            self, source, destination, amount,
            confirm=True, timeout=None, txid=None,
            description=None):
        """
        Send NANO from a source account to a destination account

        If `confirm` is True, command will block until the created block is
        confirmed or timeout is reached

        :param str source: Source account ID
        :param str destination: Destination account ID
        :param amount: Amount to send in raw
        :type amount: int or decimal.Decimal
        :param bool confirm: Whether to wait until the block is confirmed
        :param float timeout: Time to wait for confirmation if `confirm` is True
        :param str txid: Unique identifier used for the block
        :param str description: Optional description for the created block

        :raises TransactionAlreadyExists: If `txid` already exists in the
                                          wallet
        :raises InsufficientBalance: Source account balance too low to send
                                     the NANO
        :raises ValueError: Incorrect amount

        :returns: Created block
        :rtype: siliqua.wallet.accounts.Block
        """
        block = self.wallet.send(
            source=source,
            destination=destination,
            amount=amount,
            txid=txid,
            description=description)

        if confirm:
            wait_result = self.wait_for_block(block, timeout=timeout)
            block = wait_result.block

        return block

    def wait_for_blocks(self, blocks, timeout=None):
        """
        Wait until the given blocks have been confirmed, rejected or until
        the optional timeout is reached

        :param blocks: List of blocks that await confirmation
        :param float timeout: Maximum length of time to wait until all blocks
                              are confirmed and/or rejected

        :returns: MultipleWaitResult instance containing block results
        :rtype: MultipleWaitResult
        """
        block_hashes = [block.block_hash for block in blocks]
        wait_results = OrderedDict()

        def block_rejected(
                block, error, block_hashes, remaining_blocks, wait_results):
            if block.block_hash in block_hashes:
                wait_results[block.block_hash] = WaitResult(
                    block=block,
                    rejected=True,
                    error=error
                )
                del remaining_blocks[block.block_hash]

        def block_removed(
                block, block_hashes, remaining_blocks, wait_results):
            # Check if a block is removed as part of a cascading rejection;
            # eg. block is removed due to its parent getting rejected.
            if block.block_hash not in remaining_blocks:
                return

            if not block.previous:
                return

            try:
                previous_wait_result = wait_results[block.previous]
            except KeyError:
                return

            if previous_wait_result.rejected:
                wait_results[block.block_hash] = WaitResult(
                    block=block,
                    rejected=True,
                    error=BlockProcessError.PREVIOUS_BLOCK_REJECTED
                )

            del remaining_blocks[block.block_hash]

        def block_confirmed(
                block, block_hashes, remaining_blocks, wait_results):
            if block.block_hash in block_hashes:
                wait_results[block.block_hash] = WaitResult(
                    block=block,
                    confirmed=True
                )
                try:
                    del remaining_blocks[block.block_hash]
                except KeyError:
                    pass

        start = time.time()

        remaining_blocks = {block.block_hash: block for block in blocks}

        self.wallet.callbacks.block_rejected.add(
            lambda b, e: block_rejected(
                b, e, block_hashes, remaining_blocks, wait_results
            ),
            "wait_for_blocks"
        )
        self.wallet.callbacks.block_confirmed.add(
            lambda b: block_confirmed(
                b, block_hashes, remaining_blocks, wait_results
            ),
            "wait_for_blocks"
        )
        self.wallet.callbacks.block_removed.add(
            lambda b: block_removed(
                b, block_hashes, remaining_blocks, wait_results
            ),
            "wait_for_blocks"
        )

        try:
            while True:
                self.update()

                if not remaining_blocks:
                    logger.info(
                        "Finished waiting for %d block(s), took %.2f seconds",
                        len(wait_results), (time.time() - start)
                    )
                    break

                end = time.time()

                if timeout and (start + timeout) < end:
                    logger.info(
                        "Timeout reached but %d block(s) are still remaining",
                        len(remaining_blocks)
                    )
                    for block in remaining_blocks.values():
                        wait_results[block.block_hash] = WaitResult(
                            block=block, timeout=True
                        )
                    break

                time.sleep(0.2)

            return MultipleWaitResult(
                wait_results=list(wait_results.values()),
                complete=not remaining_blocks
            )
        finally:
            self.wallet.callbacks.block_rejected.remove("wait_for_blocks")
            self.wallet.callbacks.block_confirmed.remove("wait_for_blocks")
            self.wallet.callbacks.block_removed.remove("wait_for_blocks")

    def wait_for_block(self, block, timeout=None):
        """
        Wait until the given block has been confirmed, rejected or until
        the optional timeout is reached

        :param block: Block that awaits confirmation
        :type block: siliqua.wallet.accounts.Block
        :param float timeout: Maximum length of time to wait until the block
                              is confirmed or rejected

        :returns: WaitResult instance containing block result
        :rtype: WaitResult
        """
        return self.wait_for_blocks(
            blocks=[block], timeout=timeout
        ).wait_results[0]

    def update(self):
        """
        The main update loop.

        This should be called regularly (eg. once every second)
        in a wallet application when no other activity is happening (eg.
        NANO being sent).
        """
        self.network.update_accounts_to_sync(self.wallet)

        # Get new blocks from the network
        processed_blocks = self.network.get_processed_blocks()
        self.wallet.update_processed_blocks(processed_blocks)

        # Get pocketable blocks to receive from the network
        pocketable_blocks = self.network.get_pocketable_blocks()
        pocketed_blocks = self.wallet.update_pocketable_blocks(
            pocketable_blocks
        )

        # Update work processor with unsolved blocks
        work_units = self.wallet.get_work_units_to_solve(
            work_difficulty=self.network.work_difficulty,
            precompute_work=self.config.get("work.precompute_work", True)
        )
        self.work_finished = not work_units

        self.work.add_work_units_to_solve(
            work_units, network_difficulty=self.network.work_difficulty
        )

        solved_work_units = self.work.get_solved_work_units()
        self.wallet.update_solved_blocks(solved_work_units)

        self.work.clear_solved_work_units()

        # Get blocks to broadcast
        blocks_to_broadcast = self.wallet.get_blocks_to_broadcast()
        self.network.add_blocks_to_broadcast(blocks_to_broadcast)

        self.network_finished = (
            self.network.connection_status.sync_complete and
            not processed_blocks and
            not blocks_to_broadcast and
            not pocketed_blocks
        )

        # If wallet is unlocked,refill accounts and sign any unsigned blocks
        if self.wallet.secrets_unlocked:
            self.wallet.sign_blocks()
            self.wallet.refill_accounts()
