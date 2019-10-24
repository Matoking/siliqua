import pytest
from siliqua.work import BaseWorkPlugin

from tests.util import to_hex


def test_work_add_work_units_to_solve(config, work_unit_factory):
    config.set("work.precompute_multiplier", 1.5)
    work_plugin = BaseWorkPlugin(config=config)

    work_unit_a = work_unit_factory()
    work_unit_b = work_unit_factory()
    work_unit_c = work_unit_factory()

    # Make work unit B into a precomputed work by removing its block hash
    work_unit_b.block_hash = None

    work_plugin.add_work_units_to_solve(
        [work_unit_a, work_unit_b, work_unit_c],
        network_difficulty="ffffffc000000000"
    )

    work_unit_a = work_plugin.work_units[work_unit_a.work_block_hash]
    work_unit_b = work_plugin.work_units[work_unit_b.work_block_hash]
    work_unit_c = work_plugin.work_units[work_unit_c.work_block_hash]

    assert work_unit_a.difficulty == "ffffffc000000000"
    # The precomputed work unit has a higher difficulty target
    assert work_unit_b.difficulty == "ffffffd555555800"
    assert work_unit_c.difficulty == "ffffffc000000000"
