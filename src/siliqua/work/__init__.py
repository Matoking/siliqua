"""
Work plugin to solve pending proof-of-work
"""
from siliqua import logger as root_logger  # isort:skip
logger = root_logger.getChild("work")

import copy
from collections import OrderedDict
from functools import total_ordering
from queue import Empty, Queue
from threading import Lock

from siliqua.exceptions import InsufficientConfiguration
from siliqua.plugins import BasePlugin, get_work_plugins
from nanolib import (WORK_DIFFICULTY, get_work_value, solve_work,
                     validate_account_id, validate_block_hash,
                     validate_difficulty, validate_work,
                     derive_work_difficulty, InvalidDifficulty)

__all__ = (
    "BaseWorkPlugin",
)


class WorkUnit:
    """
    Work unit is a proof-of-work consisting of a work block hash and a block
    hash.

    The work block hash is the block hash used in the PoW generation
    algorithm, while the block hash belongs to the actual block to which
    the complete PoW will be attached to.
    """
    __slots__ = (
        "account_id", "block_hash", "work_block_hash", "difficulty", "work"
    )

    def __init__(
            self, account_id, block_hash, work_block_hash, difficulty=None):
        self.account_id = account_id
        self.block_hash = (
            validate_block_hash(block_hash) if block_hash else None
        )
        self.work_block_hash = validate_block_hash(work_block_hash)

        if not difficulty:
            difficulty = WORK_DIFFICULTY
        self.difficulty = validate_difficulty(difficulty)

        self.work = None

    @property
    def solved(self):
        if not self.work:
            return False

        try:
            validate_work(
                block_hash=self.work_block_hash,
                work=self.work,
                difficulty=self.difficulty
            )
            return True
        except InvalidDifficulty:
            return False

    def solve_work(self, timeout=None):
        """
        Try to solve the work.

        :param float timeout: If timeout is provided, the amount of time
                              spent trying to generate the PoW.

        :return: Whether PoW was generated successfully
        :rtype: bool
        """
        work = solve_work(
            block_hash=self.work_block_hash,
            difficulty=self.difficulty,
            timeout=timeout
        )

        if work:
            self.work = work
            return True
        else:
            return False


class BaseWorkPlugin(BasePlugin):
    """
    Base work server plugin
    """
    PLUGIN_TYPE = "work"

    def __init__(self, **kwargs):
        super(BaseWorkPlugin, self).__init__(**kwargs)

        self.work_lock = Lock()
        self.work_units = {}

        self.started = False

    def add_work_units_to_solve(self, work_units, network_difficulty):
        precompute_multiplier = float(
            self.config.get("work.precompute_multiplier", 1.0)
        )

        with self.work_lock:
            for work_unit in work_units:
                work_unit.difficulty = network_difficulty

                if not work_unit.block_hash:
                    # Apply the precompute multiplier to precomputed work
                    work_unit.difficulty = derive_work_difficulty(
                        multiplier=precompute_multiplier,
                        base_difficulty=network_difficulty
                    )

                work_block_hash = work_unit.work_block_hash

                existing_work_unit = self.work_units.get(work_block_hash, None)
                if not existing_work_unit:
                    self.work_units[work_block_hash] = work_unit
                    existing_work_unit = work_unit

                if existing_work_unit.difficulty < work_unit.difficulty:
                    existing_work_unit.difficulty = work_unit.difficulty

        return True

    def get_solved_work_units(self):
        work_units = []
        with self.work_lock:
            for work_unit in self.work_units.values():
                if work_unit.solved:
                    work_units.append(work_unit)

        return work_units

    def clear_solved_work_units(self):
        with self.work_lock:
            work_block_hashes = list(self.work_units.keys())
            for work_block_hash in work_block_hashes:
                work_unit = self.work_units[work_block_hash]
                if work_unit.solved:
                    del self.work_units[work_block_hash]

    def stop(self):
        if not self.started:
            raise ValueError("The work server is not running")

        self._stop()

    def _stop(self):
        raise NotImplementedError

    def start(self):
        if not self.is_config_valid:
            raise ValueError("The work server hasn't been configured")

        if self.started:
            raise ValueError("The work server is already running")

        self._start()

    def _start(self):
        raise NotImplementedError

    def reload(self):
        self.stop()
        self.start()
