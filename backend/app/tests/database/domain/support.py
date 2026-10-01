class PrivateContext(dict):
    """Prevent pytest fixture repr from printing isolated test access credentials."""

    def __repr__(self):
        return "<isolated domain test context>"
