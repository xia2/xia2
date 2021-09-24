from xia2.Driver.SimpleDriver import SimpleDriver


class _DriverFactory:
    def __init__(self):
        self._driver_type = "simple"

        self._implemented_types = [
            "simple",
        ]

    def set_driver_type(self, driver_type):
        """Set the kind of driver this factory should produce."""
        if driver_type not in self._implemented_types:
            raise RuntimeError("unimplemented driver class: %s" % driver_type)
        else:
            raise RuntimeError("setting driver_type now unsupported")

        self._driver_type = driver_type

    def get_driver_type(self):
        return self._driver_type

    def Driver(self, driver_type=None):
        """Create a new Driver instance, optionally providing the
        type of Driver we want."""

        assert driver_type is None

        if not driver_type:
            driver_type = self._driver_type

        driver_class = {
            "simple": SimpleDriver,
        }.get(driver_type)
        if driver_class:
            return driver_class()

        raise RuntimeError('Driver class "%s" unknown' % driver_type)


DriverFactory = _DriverFactory()
