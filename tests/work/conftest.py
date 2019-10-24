import pytest

from siliqua.work.local import WorkPlugin
from siliqua.work import WorkUnit
from nanolib import Block as RawBlock
from nanolib import get_account_id, generate_seed

from tests.util import to_hex


@pytest.fixture(scope="function")
def local_work_plugin_factory(config_factory):
    work_plugins = []

    def create_local_work_plugin(threads=1):
        config = config_factory()
        config["work"]["local"]["threads"] = threads

        work_plugin = WorkPlugin(config=config)
        work_plugin.start()

        work_plugins.append(work_plugin)

        return work_plugin

    yield create_local_work_plugin

    for work_plugin in work_plugins:
        if work_plugin.started:
            work_plugin.stop()


@pytest.fixture(scope="function")
def local_work_plugin(local_work_plugin_factory):
    return local_work_plugin_factory()


@pytest.fixture(scope="function")
def work_unit_factory():
    def create_work_unit(account_id=None, difficulty=None):
        if not difficulty:
            difficulty = to_hex(10000, 16)

        block = RawBlock(
            block_type="state",
            account=(
                account_id or get_account_id(public_key=generate_seed())
            ),
            previous=None,
            representative=get_account_id(public_key="0"*64),
            balance=0,
            link=generate_seed(),
            difficulty=difficulty,
            verify=False
        )

        work_unit = WorkUnit(
            account_id=block.account,
            block_hash=block.block_hash,
            work_block_hash=block.work_block_hash,
            difficulty=block.difficulty
        )

        return work_unit

    return create_work_unit
