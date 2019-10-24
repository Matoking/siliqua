import time
import pytest
import threading
import multiprocessing
import random

from nanolib import get_account_id, generate_seed, get_work_value

from tests.util import wait_for, to_hex


ACCOUNT_ID = "xrb_3d78japo7ziqqcsptk47eonzwzwjyaydcywq5ebzowjpxgyehynnjc9pd5zj"

HEX_LETTERS = "1234567890ABCDEF"

TEST_DIFFICULTY = to_hex(9459044173002835106, 16)


def count_solved_units(work_units):
    return len([
        work_unit for work_unit in work_units.values()
        if work_unit.solved
    ])


def count_pending_units(work_units):
    return len([
        work_unit for work_unit in work_units.values()
        if not work_unit.solved
    ])


def test_work_local_start_twice(local_work_plugin):
    # The server can't be started twice
    assert local_work_plugin.started

    with pytest.raises(ValueError) as exc:
        local_work_plugin.start()

    assert "The work server is already running" in str(exc.value)


def test_work_local_stop_twice(local_work_plugin):
    # The server can't be started twice
    local_work_plugin.stop()

    assert not local_work_plugin.started

    with pytest.raises(ValueError) as exc:
        local_work_plugin.stop()

    assert "The work server is not running" in str(exc.value)


def test_work_local_reload(local_work_plugin):
    # Reloading only works when the server is started
    local_work_plugin.reload()

    local_work_plugin.stop()

    with pytest.raises(ValueError) as exc:
        local_work_plugin.reload()

    assert "The work server is not running" in str(exc.value)


def test_work_local_config_required(local_work_plugin):
    config = local_work_plugin.config
    local_work_plugin.stop()

    # 'threads' needs to be set in order to start the server
    del config["work"]["local"]["threads"]

    with pytest.raises(ValueError) as exc:
        local_work_plugin.start()

    assert "The work server hasn't been configured" in str(exc.value)


def test_work_local_single(local_work_plugin_factory, work_unit_factory):
    # Enqueue an easy PoW and make sure it is completed
    work_plugin = local_work_plugin_factory()
    work_plugin.add_work_units_to_solve(
        [work_unit_factory(account_id=ACCOUNT_ID)],
        network_difficulty=to_hex(10000, 16)
    )
    work_units = work_plugin.work_units

    wait_for(
        lambda: count_solved_units(work_units) == 1, timeout=1)

    assert count_pending_units(work_units) == 0

    # Worker thread should stop soon after the work is finished
    wait_for(
        lambda: len([thread.name for thread in threading.enumerate()
                     if thread.name.startswith("work_local_worker")]) == 0,
        timeout=1
    )

    # Get the completed work
    completed_work_unit = next(
        work_unit for work_unit in work_units.values() if work_unit.solved
    )

    assert completed_work_unit.account_id == ACCOUNT_ID
    assert completed_work_unit.difficulty == to_hex(10000, 16)
    assert get_work_value(
        block_hash=completed_work_unit.work_block_hash,
        work=completed_work_unit.work) > 10000


def test_work_local_impossible(local_work_plugin_factory, work_unit_factory):
    # Enqueue an impossible PoW and shutdown the work server while it is
    # running
    work_plugin = local_work_plugin_factory(threads=2)
    work_plugin.add_work_units_to_solve(
        [work_unit_factory()],
        network_difficulty=to_hex((2**64)-1, 16)
    )
    work_units = work_plugin.work_units

    with pytest.raises(TimeoutError):
        wait_for(
            lambda: count_solved_units(work_units) == 1,
            timeout=1
        )

    # Ensure that there are two active worker threads
    assert len([
        thread.name for thread in threading.enumerate()
        if thread.name.startswith("work_local_worker")
    ]) == 2

    assert count_solved_units(work_units) == 0

    # Shutdown the work server
    work_plugin.stop()

    # No threads should be left alive after stopping the work server
    assert len([
        thread.name for thread in threading.enumerate()
        if thread.name.startswith("work_local_worker")
    ]) == 0


def test_work_local_multiple(local_work_plugin_factory, work_unit_factory):
    # Enqueue multiple PoW jobs and ensure they're all completed
    account_ids = [
        get_account_id(private_key=generate_seed()) for _ in range(0, 100)
    ]
    work_plugin = local_work_plugin_factory(threads=8)
    work_plugin.add_work_units_to_solve([
        work_unit_factory(account_id=account_id) for account_id
        in account_ids
    ], network_difficulty=to_hex(10000, 16))
    work_units = work_plugin.work_units

    # The underlying queue is a set, so the exact amount of results
    # should be 100 even if more valid PoWs were found
    wait_for(
        lambda: count_solved_units(work_units) == 100,
        timeout=5)

    for work_unit in work_units.values():
        account_ids.remove(work_unit.account_id)
