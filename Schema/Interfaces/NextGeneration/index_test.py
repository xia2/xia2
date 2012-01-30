# these would be handled by the plugin mechanism - so the classes would have
# been imported somewhere

from labelit import labelit
from mosflm import mosflm

# this should be all we really need

from index import index_implementation_manager

# perform the same test on all implementations of index

for index_implementation in index_implementation_manager.get():

    print "Testing ==== %s ====" % str(index_implementation.__name__)

    ii = index_implementation()

    ii.set_dip_template('foo_1_###.img')

    # etc.

    ii.index()
