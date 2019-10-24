class AccountAlreadyExists(ValueError):
    """Account already exists."""


class TransactionAlreadyExists(ValueError):
    """Wallet transaction already exists."""


class InsufficientBalance(ValueError):
    """Insufficient balance to send the block."""


class InvalidAccountBlock(ValueError):
    """The account-specific block is invalid."""


class WalletDecryptionError(ValueError):
    """Wallet couldn't be decrypted."""


class WalletLocked(Exception):
    """The wallet is locked."""


class WalletFileInvalid(Exception):
    """The wallet file is invalid."""


class ValueEncrypted(Exception):
    """The value to read is encrypted."""


class InvalidEncryptionKey(ValueError):
    """The encryption key is invalid."""


class AccountNotSpendable(ValueError):
    """
    Account is watching-only when an account with a private key is
    required
    """


class WalletMigrationRequired(ValueError):
    """
    Wallet has older version and will need to be migrated first
    before use
    """
    def __init__(self, wallet_version, required_version):
        self.wallet_version = int(wallet_version)
        self.required_version = int(required_version)


class UnsupportedWalletVersion(ValueError):
    """
    Wallet has a newer version than what is supported by the current
    installation
    """
    def __init__(self, wallet_version, required_version):
        self.wallet_version = int(wallet_version)
        self.required_version = int(required_version)
