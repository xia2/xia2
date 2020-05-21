class BadLatticeError(Exception):
    """An exception to be raised when a lattice is not right."""

    def __init__(self, value):
        self.parameter = value

    def __str__(self):
        return repr(self.parameter)
