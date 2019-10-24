import json


class StdioError(Exception):
    """
    Error type with an error code and message that can be printed in
    a JSON format.
    """
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def show(self):
        print(
            json.dumps({
                "status": "error",
                "data": {"error": self.code},
                "message": self.message
            }, indent=4, sort_keys=True)
        )


def create_error(code, message):
    """
    Create a StdioError from given code and message

    :param str code: Short code name for error
    :param str message: Human readable error message
    """
    return StdioError(code=code, message=message)


WalletExists = create_error(
    "wallet_exists",
    "Wallet already exists at the given path"
)
SpendableAccountRequired = create_error(
    "spendable_account_required",
    "Account with a private key is required for this operation")
MissingPassphrase = create_error(
    "missing_passphrase",
    "'passphrase' is required when encrypting the wallet"
)
AccountNotFound = create_error(
    "account_not_found",
    "Account not found in the wallet"
)
SeedRequired = create_error(
    "seed_required",
    "The wallet does not have a seed required for this operation")
BlockNotFound = create_error(
    "block_not_found",
    "Block not found in the wallet"
)
LinkBlockNotAllowed = create_error(
    "link_block_not_allowed",
    "This operation cannot be performed on a link block"
)
BlockRejected = create_error(
    "block_rejected",
    "At least one block was rejected by the network."
)
NetworkTimeout = create_error(
    "network_timeout",
    "The operation could not be finished in the given time."
)
