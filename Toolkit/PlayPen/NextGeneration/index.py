# abstract class index for things which do indexing of diffraction images
# requires: that any implementing class is also a dip.

from dip import dip

# FIXME this should also inherit from the input and output documents for the
# indexing process so that we can do the funky data copying in and out
# stuff.

# some things to automatically register the classes as they are instantiated.
# N.B. I would recommend a cup of tea before starting on this.

class _index_implementation_manager:
    def __init__(self):
        self._implementations = []

        return

    def add(self, implementation):
        self._implementations.append(implementation)
        return

    def get(self):
        return tuple(self._implementations)

class _index_metaclass(type):

    def __init__(self, name, bases, attrs):
        super(_index_metaclass, self).__init__(name, bases, attrs)

        if name != 'index':
            index_implementation_manager.add(self)

index_implementation_manager = _index_implementation_manager()

# now the actual class definitions - the things above could be separated out
# to a different file

class index:
    '''A class to illustrate how interfaces may work for things which index
    diffraction images.'''

    __metaclass__ = _index_metaclass

    def __init__(self):

        # FIXME somehow assert that this is also a dip implementation?

        assert(isinstance(self, dip))

        self._index_matrix = None
        self._index_unit_cell = None
        self._index_lattice = None

        return

    # FIXME take it as read that getters and setters will come from the
    # input and output document classes

    def index(self):
        '''Actually do the indexing - this will be what is used from the
        OUTSIDE WORLD i.e. the calling plugin.'''

        self._unmarshalindex()
        self._preindex()
        self._index()
        self._postindex()
        self._marshalindex()

        return

    def index_synchronous(self):
        '''Actually do the indexing - this will be what is used from the
        OUTSIDE WORLD i.e. the calling plugin. This one is done in the
        background.'''

        # FIXME create threads etc.

        self.index()

        # FIXME destroy threads etc.

        return

    def set_index_input(self):
        '''This is the local implementation of setDataInput()'''

        # FIXME in here check that this input data object is the correct type

        pass

    def get_index_output(self):
        '''This is the local implementation of getDataResult()'''
        pass

    def _unmarshalindex(self):
        # FIXME do the unrolling of the input XML document - set the values
        # using get, set below. This is a separate job for the code camp ;o)

        print 'unmarshalling indexing input'

        return

    def _preindex(self):
        '''If you would like to do something preparatory, please overload
        this method.'''

        print 'preindexing'

        pass

    def _index(self):
        '''Dreadfully sorry, you really have to overload this one - this is
        where the real work will be done.'''
        raise RuntimeError, 'I need to be implemented'

    def _postindex(self):
        '''And if you would like to gather your thoughts afterwards, overload
        this.'''

        print 'postindexing'

        pass

    def _marshalindex(self):
        # FIXME roll up and XML document from the input which has been set.

        print 'marshalling indexing output'

        return
