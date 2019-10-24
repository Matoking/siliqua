from queue import Empty

import pytest
from siliqua.network import BlockSetQueue


def test_block_set_queue(pocketable_block_factory):
    queue = BlockSetQueue()

    account_id = \
        "xrb_1111111111111111111111111111111111111111111111111111hifc8npp"

    block_a, block_b, block_c = [
        pocketable_block_factory(account_id=account_id, amount=1000)
        for _ in range(0, 3)
    ]

    queue.put(block_a)
    queue.put(block_b)
    queue.put(block_c)

    # The blocks are returned in FIFO order
    assert queue.get() == block_a
    assert queue.get() == block_b
    assert queue.get() == block_c

    with pytest.raises(Empty):
        queue.get(block=False)

    # Blocks in the middle can be removed directly
    queue.put(block_a)
    queue.put(block_b)
    queue.put(block_c)

    queue.remove(block_b)

    assert queue.get() == block_a
    assert queue.get() == block_c
