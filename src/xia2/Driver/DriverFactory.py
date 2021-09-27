from xia2.Driver.SimpleDriver import SimpleDriver


class _DriverFactory:
    def __init__(self):
        self._driver_type = "simple"

        self._implemented_types = [
            "simple",
        ]

    def set_driver_type(self, driver_type):
        """Set the kind of driver this factory should produce."""
        raise RuntimeError("setting driver_type now unsupported")

    def get_driver_type(self):
        return self._driver_type

    def Driver(self, driver_type=None):
        """Create a new Driver instance, optionally providing the
        type of Driver we want."""

        assert driver_type is None

        return SimpleDriver()


DriverFactory = _DriverFactory()
