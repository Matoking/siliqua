import concurrent.futures
import os
import time
from collections import OrderedDict
from itertools import cycle
from multiprocessing import Manager, Pool
from queue import Empty
from threading import Event as ThreadEvent
from threading import Thread

import click

from . import BaseWorkPlugin
from . import logger as root_logger
from ..exceptions import ConfigurationError

logger = root_logger.getChild("local")


def process_work(work_unit, shutdown_flag):
    """
    Try generating PoW for a work unit until PoW is generated or
    work plugin shutdown is triggered.

    :param work_unit: Work unit to solve
    :param shutdown_flag: Shutdown flag
    """
    work_block_hash = work_unit.work_block_hash

    logger.debug(
        "Starting worker for %s (difficulty %s) with PID %s",
        work_block_hash, work_unit.difficulty, os.getpid()
    )

    while not shutdown_flag.is_set():
        if work_unit.solve_work(timeout=0.2):
            logger.debug(
                "Worker PID %s generated PoW for %s",
                os.getpid(), work_block_hash
            )
            return work_unit

    return None


class WorkProcessor:
    """
    Work processor responsible for starting PoW generation on different threads
    and processing the results. Runs on its own thread.
    """
    def __init__(
            self, process_count, work_lock, work_units):
        self.process_count = int(process_count)
        self.work_lock = work_lock
        self.work_units = work_units

        self.work_to_generate = OrderedDict()
        self.work_block_hash_pools = OrderedDict()

        self.manager = None
        self.pool = None

    def update(self):
        """
        Perform a single round of updates:

        * Check which work units need to be solved
        * Check which work units have been solved
        * Start generating PoW for pending work units
        """
        self.update_pending_blocks()
        self.update_completed_blocks()
        self.start_work()

    def shutdown(self):
        self.shutdown_pool()

    def create_pool(self):
        self.manager = Manager()
        self.pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.process_count,
            thread_name_prefix="work_local_worker"
        )

    def shutdown_pool(self):
        self.stop_all_workers()

        if not self.pool:
            # Pool might already be inactive because no PoW was being worked on
            return

        self.pool.shutdown()
        self.pool = None

        self.manager.shutdown()
        self.manager = None

    def update_pending_blocks(self):
        """
        Check the owork units for any unfinished blocks
        """
        # Collect pending blocks
        with self.work_lock:
            for work_unit in self.work_units.values():
                if not work_unit.solved:
                    work_block_hash = work_unit.work_block_hash
                    self.work_to_generate[work_block_hash] = work_unit

    def get_all_active_workers(self):
        workers = []
        for work_block_hash in self.work_block_hash_pools.keys():
            workers += self.get_active_workers(work_block_hash)

        return workers

    def get_active_workers(self, work_block_hash):
        if not self.work_block_hash_pools.get(work_block_hash, None):
            return []

        return [
            worker for worker
            in self.work_block_hash_pools[work_block_hash]["workers"]
            if not worker.done()
        ]

    def get_block_hash_workers(self, work_block_hash):
        if not self.work_block_hash_pools.get(work_block_hash, None):
            return []

        return [
            worker for worker
            in self.work_block_hash_pools[work_block_hash]["workers"]
        ]

    def start_worker(self, work_unit):
        """
        Start a single worker for a work unit

        :param work_unit: Pending work unit
        :type work_unit: siliqua.work.WorkUnit
        """
        work_block_hash = work_unit.work_block_hash

        if not self.work_block_hash_pools.get(work_block_hash, None):
            self.work_block_hash_pools[work_block_hash] = {
                "work_unit": work_unit,
                "shutdown_flag": self.manager.Event(),
                "workers": []
            }

        work_info = self.work_block_hash_pools[work_block_hash]

        if not self.pool:
            self.create_pool()

        work_info["workers"].append(
            self.pool.submit(
                process_work,
                work_unit=work_info["work_unit"],
                shutdown_flag=work_info["shutdown_flag"]
            )
        )

    def stop_all_workers(self):
        """
        Stop all running workers for all work units
        """
        # Handle all block hash workers simultaneously, since calling
        # 'stop_workers' individually could cause this method to block
        # for a long time before all workers finally exit
        active_workers = self.get_all_active_workers()
        for work_info in self.work_block_hash_pools.values():
            work_info["shutdown_flag"].set()

        for worker in active_workers:
            # Wait until all threads complete
            worker.result()

        return True

    def stop_workers(self, work_block_hash):
        """
        Stop all running workers for the given work block hash

        :param str work_block_hash: Work block hash
        """
        if not self.work_block_hash_pools.get(work_block_hash, None):
            return

        work_info = self.work_block_hash_pools[work_block_hash]
        work_info["shutdown_flag"].set()

        # Shutdown flag has been set; wait until all workers exit
        for worker in work_info["workers"]:
            worker.result()

        del self.work_block_hash_pools[work_block_hash]

    def update_completed_blocks(self):
        """
        Check if work has been completed. Push any completed work into the
        queue.
        """
        try:
            with self.work_lock:
                remaining_block_hashes = list(self.work_block_hash_pools.keys())
                for work_block_hash in remaining_block_hashes:
                    workers = self.get_block_hash_workers(work_block_hash)

                    found_work = False

                    done_workers, _ = concurrent.futures.wait(
                        workers, timeout=0,
                        return_when=concurrent.futures.FIRST_COMPLETED
                    )

                    for worker in done_workers:
                        workers.remove(worker)

                        exception = worker.exception(timeout=0)
                        if exception:
                            logger.warning("Work thread died unexpectedly.")
                        else:
                            completed_work_unit = worker.result(timeout=0)
                            try:
                                work_unit = self.work_units[work_block_hash]
                            except KeyError:
                                # If the work unit no longer exists, the main
                                # thread already picked up the finished work
                                # If so, clear the workers as normal
                                found_work = True
                                break

                            work_unit.work = completed_work_unit.work
                            logger.info(
                                "Generated PoW for block %s in account %s",
                                completed_work_unit.block_hash,
                                completed_work_unit.account_id
                            )
                            found_work = True

                    if found_work:
                        # If we found work, shutdown all workers for this block hash
                        del self.work_to_generate[work_block_hash]
                        self.stop_workers(work_block_hash)

                        logger.debug(
                            "%s PoW(s) left to generate", len(self.work_to_generate)
                        )
        except Exception as exc:
            logger.info("Error: {} {}".format(str(exc), type(exc)))

    def start_work(self):
        """
        Check the pending work units and either start worker threads if
        work is available, or shutdown the pool entirely if no
        work is available
        """
        if not self.work_to_generate:
            if self.pool:
                logger.info(
                    "No PoW to generate at this time, "
                    "shutting down worker pool."
                )
                self.shutdown_pool()
            return

        if not self.pool:
            logger.info(
                "Received %s PoW(s) to generate, starting worker pool",
                len(self.work_to_generate)
            )
            self.create_pool()

        active_worker_count = len(self.get_all_active_workers())
        available_worker_count = self.process_count - active_worker_count

        work_iter = cycle(self.work_to_generate.values())
        for _ in range(0, available_worker_count):
            work_unit = next(work_iter)
            self.start_worker(work_unit=work_unit)


def run_work_thread(process_count, work_lock, work_units, shutdown_flag):
    work_processor = WorkProcessor(
        process_count=process_count, work_lock=work_lock, work_units=work_units
    )

    while not shutdown_flag.is_set():
        work_processor.update()
        time.sleep(0.1)

    work_processor.shutdown()


class WorkPlugin(BaseWorkPlugin):
    PLUGIN_NAME = "local"

    def __init__(self, *args, **kwargs):
        super(WorkPlugin, self).__init__(*args, **kwargs)

        self.thread = None
        self.shutdown_flag = None

    def _get_cli_params(self):
        return [
            click.Option(
                ["--work-threads"], type=int,
                help=(
                    "Amount of threads to use for generating PoW. "
                    "Defaults to -1, which uses half of CPU cores."
                )
            ),
        ]

    def validate_config(self):
        # Validate thread count
        threads = self.config.get("work.local.threads", None)
        try:
            is_int = isinstance(threads, int) or threads.isdigit()
        except AttributeError:
            # If 'threads' is not set
            is_int = False

        is_valid = False

        if is_int:
            is_valid = int(threads) > 0 or int(threads) == -1

        if not is_int or not is_valid:
            raise ConfigurationError(
                "work.local.threads",
                "Thread count has to be a positive integer or -1"
            )

    def _stop(self):
        self.shutdown_flag.set()
        self.thread.join()

        logger.info("Stopped work thread")

        self.thread = None
        self.shutdown_flag = None
        self.started = False

    def _start(self):
        process_count = self.config.get("work.local.threads")

        if process_count == -1:
            process_count = max(int(os.cpu_count() / 2), 1)

        self.shutdown_flag = ThreadEvent()
        self.thread = Thread(
            target=run_work_thread,
            kwargs={
                "process_count": process_count,
                "work_units": self.work_units,
                "work_lock": self.work_lock,
                "shutdown_flag": self.shutdown_flag
            }
        )
        self.thread.start()

        logger.info("Started work thread")

        self.started = True
