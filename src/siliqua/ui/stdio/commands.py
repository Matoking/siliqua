import os.path
import time
from collections import OrderedDict, defaultdict

from siliqua.server import MultipleWaitResult, WalletServer, WaitResult
# Prevent collision with a command with the same name
from siliqua.wallet import (Account, AccountSource, Block, LinkBlock, Wallet,
                              WalletProperties, WalletSeedAlgorithm)
from siliqua.wallet import \
    calculate_key_iteration_count as calculate_key_iteration_count_
from siliqua.wallet.exceptions import (AccountAlreadyExists,
                                         InsufficientBalance)
from nanolib import generate_seed, get_account_id, validate_seed

from . import logger
from .exceptions import (AccountNotFound, BlockNotFound, BlockRejected,
                         LinkBlockNotAllowed, MissingPassphrase,
                         NetworkTimeout, SeedRequired,
                         SpendableAccountRequired, StdioError, WalletExists)
from .params import (AccountOption, AccountParam, AmountParam, BlockHashParam,
                     BoolOption, BoolParam, FilePathParam, FloatOption,
                     FloatParam, IntParam, IntRangeOption, PassphraseOption,
                     PrivateKeyOption, PublicKeyOption, RepeatParams,
                     SecureStrOption, StrOption, StrParam)
from .util import (StdioResult, cli_command, paginate_list,
                   truncate_ordered_dict, unlock_wallet)


def get_default_key_iteration_count():
    """
    Get default key iteration count. Used as a default value
    for options.
    """
    key_iteration_count = calculate_key_iteration_count_(seconds=1)
    logger.debug(
        "Calculated default key iteration count: %s", key_iteration_count
    )

    return key_iteration_count


def block_to_dict(block, include_block_data=False):
    """
    Convert a block into a dict that can be added into a result

    :param block: Block instance
    :type block: siliqua.wallet.accounts.Block
                 or siliqua.wallet.accounts.LinkBlock
    :param bool include_block_data: Whether to include the block fields
                                    in the result. Default is false.

    :returns: Block as a dict
    :rtype: dict
    """
    if isinstance(block, Block):
        entry = {
            "tx_type": block.tx_type,
            "amount": str(block.amount),
            "balance": str(block.balance),
            "hash": block.block_hash,
            "confirmed": block.confirmed,
            "is_link_block": False,
            "has_work": bool(block.work),
            "has_signature": bool(block.signature),
            "timestamp": block.timestamp.to_dict()
        }

        if block.description:
            entry["description"] = block.description
    else:
        entry = {
            "tx_type": "send",
            "amount": str(-block.amount),
            "hash": block.block_hash,
            "confirmed": True,
            "is_link_block": True,
            "has_work": True,
            "has_signature": True,
            "timestamp": block.timestamp.to_dict()
        }

    if include_block_data:
        entry["block_data"] = block.block.to_dict()

    return entry


def wait_result_to_dict_and_error(wait_result):
    """
    Convert a wait result into a dict that can be added into a result.

    :param wait_result: Wait result
    :type wait_result: siliqua.network.WaitResult

    :returns: Wait result as a dict
    :rtype: dict
    """
    result = {
        "hash": wait_result.block.block_hash,
        "confirmed": wait_result.confirmed,
        "rejected": wait_result.rejected,
    }

    error = None

    if wait_result.timeout:
        result["block_error"] = "timeout"
        error = NetworkTimeout
    elif wait_result.rejected:
        del result["hash"]
        result["block_error"] = wait_result.error.value
        error = BlockRejected

    return result, error


@cli_command(
    wallet_required=False, start_network=False, start_work=False,
    help_text="Create a new wallet")
def create_wallet(
        server,
        wallet_path: FilePathParam(exists=False),
        seed: SecureStrOption,
        encrypt_secrets: BoolOption,
        encrypt_wallet: BoolOption,
        passphrase: SecureStrOption,
        gap_limit: IntRangeOption(minimum=0, maximum=10000, default=20),
        key_iteration_count: IntRangeOption(
            default=get_default_key_iteration_count,
            minimum=1, maximum=2**32
        )):
    if os.path.exists(wallet_path):
        raise WalletExists

    if not seed:
        logger.info("Seed not provided, generating one automatically.")
        seed = generate_seed()

    validate_seed(seed)

    wallet = Wallet(
        properties=WalletProperties(
            seed_algorithm=WalletSeedAlgorithm.NANO,
            seed=seed,
            gap_limit=gap_limit
        )
    )
    wallet.refill_accounts()

    if encrypt_secrets or encrypt_wallet:
        if not passphrase:
            raise MissingPassphrase

        wallet.change_passphrase(
            passphrase=passphrase,
            encrypt_secrets=encrypt_secrets,
            encrypt_wallet=encrypt_wallet,
            key_iteration_count=key_iteration_count)

    wallet.save(wallet_path)

    return StdioResult(
        {
            "message": "Saved wallet to {}".format(wallet_path),
            "wallet_encrypted": wallet.encryption.wallet_encrypted,
            "secrets_encrypted": wallet.encryption.secrets_encrypted
        }
    )


@cli_command(
    short_help_text="Calculate key iteration count for encrypted wallets",
    help_text=(
        "Calculate key iteration count based on target time in seconds.\n\n"
        "Higher key iteration count increases wallet security but also "
        "increases the time it takes to decrypt a wallet or unlock wallet "
        "secrets."
    ),
    start_network=False, start_work=False, wallet_required=False)
def calculate_key_iteration_count(server, seconds: FloatParam):
    key_iteration_count = calculate_key_iteration_count_(seconds=seconds)

    return StdioResult({
        "key_iteration_count": key_iteration_count,
        "seconds": seconds
    })


@cli_command(
    help_text="Change encryption settings on a wallet",
    start_work=False, start_network=False)
def change_encryption(
        server,
        passphrase: PassphraseOption,
        new_passphrase: SecureStrOption,
        encrypt_secrets: BoolOption,
        encrypt_wallet: BoolOption,
        key_iteration_count: IntRangeOption(
            default=get_default_key_iteration_count,
            minimum=1, maximum=2**32
        )):
    if encrypt_secrets or encrypt_wallet:
        if not new_passphrase:
            raise MissingPassphrase

    with unlock_wallet(server=server, passphrase=passphrase):
        server.wallet.change_passphrase(
            passphrase=new_passphrase,
            encrypt_secrets=encrypt_secrets,
            encrypt_wallet=encrypt_wallet,
            key_iteration_count=key_iteration_count)

    server.save_wallet()

    return StdioResult(
        {
            "message": "Encryption changed on wallet {}".format(
                server.wallet_path
            ),
            "secrets_encrypted": server.wallet.encryption.secrets_encrypted,
            "wallet_encrypted": server.wallet.encryption.wallet_encrypted,
            "key_iteration_count": server.wallet.encryption.key_iteration_count
        }
    )


@cli_command(
    short_help_text="Get the seed in a wallet",
    help_text="Get the seed in a wallet",
    start_work=False, start_network=False
)
def get_wallet_seed(
        server,
        passphrase: PassphraseOption):
    if not server.wallet.properties.seed:
        raise SeedRequired

    with unlock_wallet(server=server, passphrase=passphrase) as peek:
        seed = peek(server.wallet.properties.seed)

    return StdioResult({"seed": seed})


@cli_command(
    short_help_text="Get the balance for each account in a wallet",
    help_text=(
        "Get the balance for each account in a wallet. Spendable "
        "and unspendable (account has no private key) are reported separately."
    ),
    start_work=False, start_network=False
)
def get_balance(
        server,
        passphrase: PassphraseOption):
    account_balances = {}

    spendable_balance = 0
    unspendable_balance = 0

    for account in server.wallet.accounts:
        spendable = bool(account.private_key)
        account_balances[account.account_id] = {
            "spendable": spendable,
            "balance": str(account.balance)
        }

        if account.name:
            account_balances[account.account_id]["name"] = account.name

        if spendable:
            spendable_balance += account.balance
        else:
            unspendable_balance += account.balance

    return StdioResult({
        "spendable_balance": str(spendable_balance),
        "unspendable_balance": str(unspendable_balance),
        "accounts": account_balances
    })


@cli_command(
    short_help_text="Get the private key for an account in a wallet",
    help_text="Get the private key for an account in a wallet",
    start_work=False, start_network=False
)
def get_account_private_key(
        server,
        passphrase: PassphraseOption,
        account_id: AccountParam):
    try:
        account = server.wallet.account_map[account_id]
    except KeyError:
        raise AccountNotFound

    if not account.private_key:
        raise SpendableAccountRequired

    with unlock_wallet(server=server, passphrase=passphrase) as peek:
        private_key = peek(account.private_key)

    return StdioResult({
        "account_id": account_id,
        "private_key": private_key
    })


@cli_command(
    short_help_text="Add account into a wallet",
    help_text=(
        "Add account into a wallet using either an account ID, public key "
        "or a private key."
    ),
    start_work=False, start_network=False
)
def add_account(
        server,
        passphrase: PassphraseOption,
        account_id: AccountOption(group_name="account"),
        public_key: PublicKeyOption(group_name="account"),
        private_key: PrivateKeyOption(group_name="account")):
    if sum([bool(account_id), bool(public_key), bool(private_key)]) != 1:
        raise StdioError(
            "one_parameter_required",
            "Only one parameter from 'account_id', 'public_key' or "
            "'private_key' is required"
        )

    account = None
    if account_id:
        account = server.wallet.add_account_from_account_id(account_id)
    elif public_key:
        account = server.wallet.add_account_from_account_id(
            get_account_id(public_key=public_key)
        )
    elif private_key:
        with unlock_wallet(server=server, passphrase=passphrase):
            account = server.wallet.add_account_from_private_key(private_key)

    server.save_wallet()

    return StdioResult({"account_id": account.account_id})


@cli_command(
    short_help_text="Remove account from a wallet",
    help_text="Remove account from a wallet",
    start_work=False, start_network=False
)
def remove_account(
        server,
        passphrase: PassphraseOption,
        account_id: AccountParam):
    try:
        account = server.wallet.account_map[account_id]
    except KeyError:
        raise AccountNotFound

    server.wallet.remove_account(account)
    server.save_wallet()

    return StdioResult({"account_id": account.account_id})


@cli_command(
    short_help_text="Generate additional account(s) from a seed in a wallet",
    help_text=(
        "Generate additional account(s) from a seed in a wallet. "
        "Accounts are generated automatically according to the wallet's "
        "gap limit as needed. This command can be used to generate additional "
        "accounts regardless of the gap limit."
    ),
    start_work=False, start_network=False
)
def generate_account(
        server,
        passphrase: PassphraseOption,
        count: IntRangeOption(default=1, minimum=1, maximum=10000)):
    if not server.wallet.properties.seed:
        raise SeedRequired

    with unlock_wallet(server=server, passphrase=passphrase):
        new_accounts = [
            server.wallet.generate_seed_account() for _ in range(0, count)
        ]

    server.save_wallet()

    return StdioResult(
        {"new_accounts": [account.account_id for account in new_accounts]}
    )


@cli_command(
    short_help_text="Sync the wallet with the network",
    help_text=(
        "Sync the wallet with the network.\n\n"
        "Pending blocks will be pocketed and any pending PoW will be worked "
        "on until the timeout in 'timeout' is reached.\n\n"
        "If 'finish-work' is selected, timeout will be postponed until all "
        "pending PoW has been processed.\n\n"
        "If 'finish-sync' is selected, timeout will be postponed until "
        "the wallet has finished synchronizing with the network "
        "(account histories are complete and all pocketed blocks have been "
        "received)."
    )
)
def sync(
        server,
        passphrase: PassphraseOption,
        finish_work: BoolOption(default=True),
        finish_sync: BoolOption(default=True),
        timeout: IntRangeOption(
            default=10,
            minimum=0, maximum=6000
        ),
        result_count: IntRangeOption(
            default=50,
            minimum=1, maximum=1000000
        )):
    new_blocks = OrderedDict()
    received_blocks = OrderedDict()
    rejected_blocks = OrderedDict()
    completed_work_units = OrderedDict()

    def remove_block(new_blocks, received_blocks, block):
        try:
            del new_blocks[block.block_hash]
        except KeyError:
            pass

        if block.link_block:
            try:
                del received_blocks[block.link_block.block_hash]
            except KeyError:
                pass

    def reject_block(rejected_blocks, new_blocks, block, error):
        try:
            del new_blocks[block.block_hash]
        except KeyError:
            pass

        rejected_blocks[block.block_hash] = (block, error)
        truncate_ordered_dict(rejected_blocks, result_count)

    def add_block(new_blocks, rejected_blocks, block):
        new_blocks[block.block_hash] = block
        truncate_ordered_dict(new_blocks, result_count)

        try:
            del rejected_blocks[block.block_hash]
        except KeyError:
            pass

    def receive_block(received_blocks, block):
        received_blocks[block.block_hash] = block
        truncate_ordered_dict(received_blocks, result_count)

    def complete_work_unit(completed_work_units, work_unit):
        completed_work_units[work_unit.work_block_hash] = work_unit

    # Register callbacks
    server.wallet.callbacks.block_removed.add(
        lambda b: remove_block(new_blocks, received_blocks, b)
    )
    server.wallet.callbacks.block_added.add(
        lambda b: add_block(new_blocks, rejected_blocks, b)
    )
    server.wallet.callbacks.block_received.add(
        lambda b: receive_block(received_blocks, b)
    )
    server.wallet.callbacks.block_rejected.add(
        lambda block, error: reject_block(
            rejected_blocks, new_blocks, block, error
        )
    )
    server.wallet.callbacks.work_unit_completed.add(
        lambda work_unit: complete_work_unit(
            completed_work_units, work_unit
        )
    )

    start = time.time()
    current = time.time()

    postpone_timeout = False

    with unlock_wallet(server=server, passphrase=passphrase):
        # Keep track if at least one round of updates has been finished.
        # This is necessary with a timeout value of 0 to ensure we know
        # whether the synchronization is complete or not
        network_warmup_complete = False
        network_round_count = server.network.connection_status.completed_rounds

        while current < (start + timeout) or postpone_timeout or \
                not network_warmup_complete:
            server.update()

            postpone_timeout = False

            time.sleep(0.1)
            current = time.time()

            # Postpone timeout if something needs to be done first
            if finish_work and not server.work_finished:
                postpone_timeout = True
            if finish_sync and not server.network_finished:
                postpone_timeout = True

            if postpone_timeout:
                start = time.time()

            network_warmup_complete = (
                server.network.connection_status.completed_rounds
                >= network_round_count + 2
            )

    new_block_entries = defaultdict(list)
    for block in new_blocks.values():
        entry = {
            "block_data": block.block.to_dict(),
            "hash": block.block_hash
        }
        if block.amount != 0:
            entry["amount"] = str(block.amount)
        entry["tx_type"] = block.tx_type

        new_block_entries[block.account].append(entry)

    received_block_entries = defaultdict(list)
    for link_block in received_blocks.values():
        destination = link_block.recipient
        received_block_entries[destination].append({
            "amount": str(link_block.amount),
            "source": link_block.account,
            "hash": link_block.block_hash
        })

    rejected_block_entries = defaultdict(list)
    for block, error in rejected_blocks.values():
        rejected_block_entries[block.account].append({
            "data": block.block.to_dict(),
            "hash": block.block_hash,
            "block_error": error.value
        })

    # If something changed, save the wallet
    wallet_changed = (
        new_blocks or received_blocks or rejected_blocks or
        completed_work_units
    )
    if wallet_changed:
        server.save_wallet()

    data = {
        "new_blocks": new_block_entries,
        "received_blocks": received_block_entries,
        "rejected_blocks": rejected_block_entries
    }
    error = BlockRejected if rejected_block_entries else None

    return StdioResult(data=data, error=error)


@cli_command(
    help_text="Send NANO from a single account to another account")
def send(
        server,
        passphrase: PassphraseOption,
        source: AccountParam,
        destination: AccountParam, amount: AmountParam,
        wait_until_confirmed: BoolOption(default=True),
        txid: StrOption,
        description: StrOption,
        timeout: IntRangeOption(
            default=0,
            minimum=0, maximum=6000
        )):
    try:
        account = server.wallet.account_map[source]
    except KeyError:
        raise AccountNotFound

    if not account.private_key:
        raise SpendableAccountRequired

    if account.balance < amount:
        raise InsufficientBalance

    with unlock_wallet(server=server, passphrase=passphrase):
        block = server.send_from(
            source=source, destination=destination, amount=amount,
            confirm=False, txid=txid, description=description
        )

    if wait_until_confirmed:
        wait_result = server.wait_for_block(block, timeout=timeout)
    else:
        wait_result = WaitResult(block=block)

    data, error = wait_result_to_dict_and_error(wait_result)
    data.update({
        "has_valid_work": wait_result.block.has_valid_work,
        "destination": block.link_as_account,
        "amount": str(-amount)
    })

    server.save_wallet()

    return StdioResult(data=data, error=error)


@cli_command(
    short_help_text=(
        "Send NANO from a single account to multiple accounts"
    ),
    help_text=(
        "Send NANO from a single account to multiple accounts.\n\n"
        "The command takes one source account followed by an arbitrary amount "
        "of transactions. Each transaction has the syntax DESTINATION,AMOUNT."
        "\n\n"
        "For example:\n\n"
        "$ send-many <SOURCE_ACCOUNT_ID> '<DESTINATION 1>,<AMOUNT 1>' "
        "'<DESTINATION 2>,<AMOUNT 2>'"
    )
)
def send_many(
        server,
        passphrase: PassphraseOption,
        source: AccountParam,
        transactions: RepeatParams(
            ["destination", "amount"],
            [AccountParam, AmountParam]
        ),
        wait_until_confirmed: BoolOption(default=True),
        timeout: IntRangeOption(
            default=0,
            minimum=0, maximum=6000
        ),
        description: StrOption):
    blocks = []

    total_to_send = sum([
        transaction["amount"] for transaction in transactions
    ])

    try:
        account = server.wallet.account_map[source]
    except KeyError:
        raise AccountNotFound

    if not account.private_key:
        raise SpendableAccountRequired

    if account.balance < total_to_send:
        raise InsufficientBalance

    # Since a linked list of blocks needs to exist to calculate per-block
    # amounts, use a block hash to amount dict in case a block is rejected and
    # removed from the linked list
    block_hash_to_amount = {}

    with unlock_wallet(server=server, passphrase=passphrase):
        for transaction in transactions:
            destination = transaction["destination"]
            amount = transaction["amount"]

            block = server.send_from(
                source=source, destination=destination, amount=amount,
                confirm=False, description=description
            )
            block_hash_to_amount[block.block_hash] = block.amount
            blocks.append(block)

    if wait_until_confirmed:
        multiwait_result = server.wait_for_blocks(blocks, timeout=timeout)
    else:
        multiwait_result = MultipleWaitResult(
            wait_results=[WaitResult(block=block) for block in blocks],
            complete=False
        )

    all_confirmed = bool(
        len(multiwait_result.confirmed_results) == len(transactions)
    )

    block_results = []
    broadcast_failed = False

    for wait_result in multiwait_result.wait_results:
        block_result, _ = wait_result_to_dict_and_error(wait_result)
        block_result.update({
            "has_valid_work": bool(wait_result.block.work),
            "destination": wait_result.block.link_as_account,
            "amount": str(block_hash_to_amount[wait_result.block.block_hash])
        })

        if wait_result.rejected:
            broadcast_failed = True

        block_results.append(block_result)

    server.save_wallet()

    data = {
        "blocks": block_results
    }
    error = None

    if not all_confirmed and wait_until_confirmed:
        if broadcast_failed:
            error = BlockRejected
        else:
            error = NetworkTimeout

    return StdioResult(data=data, error=error)


@cli_command(
    short_help_text=(
        "Change account representative"
    ),
    help_text=(
        "Change account representative. If the account has received NANO, "
        "a new block will be created. If not, the representative will be "
        "stored and will become active once the account has received NANO."
    ),
    start_network=False, start_work=False
)
def change_account_representative(
        server,
        passphrase: PassphraseOption,
        account_id: AccountParam,
        representative: AccountParam,
        wait_until_confirmed: BoolOption(default=False),
        timeout: IntRangeOption(
            default=0,
            minimum=0, maximum=6000
        )):
    try:
        account = server.wallet.account_map[account_id]
    except KeyError:
        raise AccountNotFound

    if not account.private_key:
        raise SpendableAccountRequired

    original_representative = account.representative

    block = None
    if account.blocks:
        block = account.change_representative(representative)
    else:
        account.change_representative(representative)

    data = {
        "account_id": account_id,
        "representative": representative
    }
    error = None
    wait_result = None

    if block:
        wait_result = WaitResult(block=block)

    if wait_until_confirmed and block:
        server.start_network()
        server.start_work()

        with unlock_wallet(server=server, passphrase=passphrase):
            wait_result = server.wait_for_block(block, timeout=timeout)

        result, error = wait_result_to_dict_and_error(wait_result)
        data.update(result)

        if wait_result.rejected:
            # Restore the original representative if the block was rejected
            account.representative = original_representative

    if wait_result:
        data.update(wait_result_to_dict_and_error(wait_result)[0])

    server.save_wallet()

    return StdioResult(data=data, error=error)


@cli_command(
    help_text="List accounts in a wallet",
    start_work=False, start_network=False)
def list_accounts(
        server,
        passphrase: PassphraseOption,
        limit: IntRangeOption(default=20, minimum=1, maximum=50000),
        offset: IntRangeOption(default=0, minimum=0, maximum=10000000),
        descending: BoolOption(default=False)):
    result = paginate_list(
        server.wallet.accounts, limit=limit, offset=offset,
        descending=descending
    )

    account_entries = []

    for account in result:
        account_result = {
            "account_id": account.account_id,
            "balance": str(account.balance),
            "head": (
                account.confirmed_head.block_hash
                if account.confirmed_head
                else None
            )
        }

        if account.name:
            account_result["name"] = account.name

        account_entries.append(account_result)

    return StdioResult({
        "accounts": account_entries,
        "count": result.total_count
    })


@cli_command(
    help_text="List blocks for an account in a wallet",
    start_work=False, start_network=False)
def list_blocks(
        server,
        passphrase: PassphraseOption,
        account_id: AccountParam,
        limit: IntRangeOption(default=20, minimum=1, maximum=50000),
        # Ten million blocks ought to be enough for anyone
        offset: IntRangeOption(default=0, minimum=0, maximum=10000000),
        descending: BoolOption(default=True)):
    blocks = server.wallet.account_map[account_id].blocks
    result = paginate_list(
        blocks, limit=limit, offset=offset, descending=descending
    )

    block_entries = []

    for block in result:
        block_entries.append(block_to_dict(block))

    return StdioResult({
        "account_id": account_id,
        "blocks": block_entries,
        "count": result.total_count
    })


@cli_command(
    help_text="List account IDs in the address book",
    start_network=False, start_work=False)
def list_address_book(
        server,
        passphrase: PassphraseOption,
        limit: IntRangeOption(default=20, minimum=1, maximum=50000),
        offset: IntRangeOption(default=0, minimum=0, maximum=10000000),
        descending: BoolOption(default=False)):
    address_items = list(server.wallet.address_book.to_dict().items())
    result = paginate_list(
        address_items, limit=limit, offset=offset, descending=descending
    )

    address_entries = {}

    for address, name in result:
        address_entries[address] = name

    return StdioResult({
        "addresses": address_entries,
        "count": result.total_count
    })


@cli_command(
    short_help_text="Get a block in the wallet",
    help_text="Get a block in the wallet",
    start_work=False, start_network=False
)
def get_block(
        server,
        passphrase: PassphraseOption,
        block_hash: BlockHashParam):
    block = server.wallet.get_block(block_hash)

    if not block:
        raise BlockNotFound

    data = block_to_dict(block, include_block_data=True)

    return StdioResult(data)


@cli_command(
    help_text="Set name for account in a wallet",
    start_network=False, start_work=False)
def set_account_name(
        server,
        passphrase: PassphraseOption,
        account_id: AccountParam,
        name: StrParam):
    try:
        account = server.wallet.account_map[account_id]
    except KeyError:
        raise AccountNotFound

    account.name = name

    server.save_wallet()

    return StdioResult({
        "account_id": account_id,
        "name": name
    })


@cli_command(
    help_text="Remove name for account in a wallet",
    start_network=False, start_work=False)
def clear_account_name(
        server,
        passphrase: PassphraseOption,
        account_id: AccountParam):
    try:
        account = server.wallet.account_map[account_id]
    except KeyError:
        raise AccountNotFound

    account.name = None

    server.save_wallet()

    return StdioResult({"account_id": account_id})


def get_wallet_block(wallet, block_hash):
    for account in wallet.accounts:
        if block_hash not in account.block_map:
            continue

        block = account.block_map[block_hash]

        try:
            # Link blocks not allowed
            block.link_block
            return block
        except AttributeError:
            raise LinkBlockNotAllowed

    raise BlockNotFound


@cli_command(
    help_text="Set description for a block in a wallet",
    start_network=False, start_work=False)
def set_block_description(
        server,
        passphrase: PassphraseOption,
        block_hash: BlockHashParam,
        description: StrParam):
    block = get_wallet_block(server.wallet, block_hash)
    block.description = description
    server.save_wallet()

    return StdioResult({
        "account_id": block.account_id,
        "hash": block.block_hash,
        "description": block.description
    })


@cli_command(
    help_text="Clear description for a block in a wallet",
    start_network=False, start_work=False)
def clear_block_description(
        server,
        passphrase: PassphraseOption,
        block_hash: BlockHashParam):
    block = get_wallet_block(server.wallet, block_hash)

    block.description = None
    server.save_wallet()

    return StdioResult({
        "account_id": block.account_id,
        "hash": block.block_hash
    })


@cli_command(
    help_text="Set name for account in address book",
    start_network=False, start_work=False)
def add_to_address_book(
        server,
        passphrase: PassphraseOption,
        account_id: AccountParam,
        name: StrParam):
    server.wallet.add_to_address_book(account_id=account_id, name=name)

    server.save_wallet()

    return StdioResult({
        "account_id": account_id,
        "name": name
    })


@cli_command(
    help_text="Remove account from the wallet's address book",
    start_network=False, start_work=False)
def remove_from_address_book(
        server,
        passphrase: PassphraseOption,
        account_id: AccountParam):
    try:
        server.wallet.address_book[account_id]
    except KeyError:
        raise AccountNotFound

    server.wallet.remove_from_address_book(account_id)
    server.save_wallet()

    return StdioResult({
        "account_id": account_id
    })


COMMANDS = [
    create_wallet, calculate_key_iteration_count, change_encryption,
    get_wallet_seed, get_balance, add_account, remove_account,
    generate_account, sync, send, send_many, change_account_representative,
    list_address_book, list_accounts, get_account_private_key, list_blocks,
    get_block, set_account_name, clear_account_name,
    set_block_description, clear_block_description, add_to_address_book,
    remove_from_address_book
]
