class UnsupportedProtocolVersion(ValueError):
    """The protocol version supported by the NANO node is too old."""
    def __init__(self, required_version, current_version):
        self.required_version = required_version
        self.current_version = current_version
