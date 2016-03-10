Decorators
----------

If we presume that the Drivers we have are adequate for the job of running
programs, we may still want to customise them for use with particular
families of programs, for example those within the CCP4 suite which have
common command syntax.

The idea here is that this can build on the Driver interface to provide more
helpful functionality c/f the Decorator pattern in "Design Patterns".

Usage
-----

in __init__ method of my class:

drf = DriverFactory("cluster")
drf.instance().__init__(self)

dcf = DecoratorFactory("CCP4")
dcf.decorate().__init__(self)

e.g. instantiate a Driver class implementation, then decorate it with
additional methods from the "CCP4" decorator, which could for instance
add methods for addHklin(), setHklout() etc. Since this relies on the
interface of Driver rather than inheriting from it, it will be far more
efficient.
