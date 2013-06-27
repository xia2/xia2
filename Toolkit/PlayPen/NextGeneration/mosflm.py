from dip import dip
from index import index
from integrate import integrate

class mosflm(dip, index, integrate):

    def __init__(self):
        dip.__init__(self)
        index.__init__(self)
        integrate.__init__(self)

        return

    def _index(self):
        '''Do a real indexing implementation here using the information from
        the index interface and dip.'''

        print 'really indexing'

        return

    def migrate_index_results_into_integrate_input(self):

        print 'migrating indexing results internally to integration input'

        return

    def _integrate(self):
        '''Do a real integration implementation here using the information from
        the integrate interface and dip.'''

        print 'really integrating'

        return

if __name__ == '__main__':

    m = mosflm()

    m.set_dip_template('foo_1_###.img')

    # etc.

    m.index()
    m.migrate_index_results_into_integrate_input()
    m.integrate()
