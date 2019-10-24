class InsufficientConfiguration(ValueError):
    """The action can't be performed due to missing configuration."""


class WalletFileLocked(ValueError):
    """The wallet file is locked by another process."""


class ConfigurationError(ValueError):
    """A configuration parameter is incorrect."""
    def __init__(self, field, error):
        self.field = field
        self.error = error

    def __str__(self):
        return "Error in '{}': {}".format(self.field, self.error)


