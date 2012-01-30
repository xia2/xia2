# abstract class integrate for things which integrate diffraction images
# requires: that any implementing class is also a dip.

from dip import dip

# FIXME this should also inherit from the input and output documents for the
# integrating process so that we can do the funky data copying in and out
# stuff.

class _integrate_implementation_manager:
    def __init__(self):
        self._implementations = []

        return

    def add(self, implementation):
        self._implementations.append(implementation)
        return

    def get(self):
        return tuple(self._implementations)

integrate_implementation_manager = _integrate_implementation_manager()

class integrate:
    '''A class to illustrate how interfaces may work for things which integrate
    diffraction images.'''

    def __init__(self):

        # FIXME somehow assert that this is also a dip implementation?

        assert(isinstance(self, dip))

        self._integrate_reflections = None

        # keep a note that this plugin class implements integrate

        global integrate_implementation_manager
        integrate_implementation_manager.add(self.__class__)

        return

    # FIXME take it as read that getters and setters will come from the
    # input and output document classes

    def integrate(self):
        '''Actually do the integrateing - this will be what is used from the
        OUTSIDE WORLD i.e. the calling plugin.'''

        self._unmarshalintegrate()
        self._preintegrate()
        self._integrate()
        self._postintegrate()
        self._marshalintegrate()

        return

    def integrate_synchronous(self):
        '''Actually do the integrateing - this will be what is used from the
        OUTSIDE WORLD i.e. the calling plugin. This one is done in the
        background.'''

        # FIXME create threads etc.

        self.integrate()

        # FIXME destroy threads etc.

        return

    def set_integrate_input(self):
        '''This is the local implementation of setDataInput()'''

        # FIXME in here check that this input data object is the correct type

        pass

    def get_integrate_output(self):
        '''This is the local implementation of getDataResult()'''
        pass

    def _unmarshalintegrate(self):
        # FIXME do the unrolling of the input XML document - set the values
        # using get, set below. This is a separate job for the code camp ;o)

        print 'unmarshalling integration input'

        return

    def _preintegrate(self):
        '''If you would like to do something preparatory, please overload
        this method.'''

        print 'preintegrating'

        pass

    def _integrate(self):
        '''Dreadfully sorry, you really have to overload this one - this is
        where the real work will be done.'''
        raise RuntimeError, 'I need to be implemented'

    def _postintegrate(self):
        '''And if you would like to gather your thoughts afterwards, overload
        this.'''

        print 'postintegrating'

        pass

    def _marshalintegrate(self):
        # FIXME roll up and XML document from the input which has been set.

        print 'marshalling integration output'

        return
