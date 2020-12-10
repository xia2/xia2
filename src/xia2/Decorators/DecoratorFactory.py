from xia2.Decorators.CCP4Decorator import CCP4DecoratorFactory


class _DecoratorFactory:
    """A factory singleton to dress Driver instances with decoration
    for specific program suites, for instance CCP4."""

    def __init__(self):
        self._type = "ccp4"

    def Decorate(self, DriverInstance, decorator_type=None):
        """Decorate DriverInstance as type or self._type if not specified."""

        if not decorator_type:
            decorator_type = self._type

        if decorator_type == "ccp4":
            return CCP4DecoratorFactory(DriverInstance)

        raise RuntimeError('unknown decorator class "%s"' % decorator_type)


DecoratorFactory = _DecoratorFactory()
