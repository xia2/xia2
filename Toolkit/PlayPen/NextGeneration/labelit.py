from dip import dip
from index import index

class labelit(dip, index):

    def __init__(self):
        dip.__init__(self)
        index.__init__(self)

        return

    def _index(self):
        '''Do a real indexing implementation here using the information from
        the index interface and dip.'''

        print 'really indexing'

        return

if __name__ == '__main__':

    l = labelit()

    l.set_dip_template('foo_1_###.img')

    # etc.

    l.index()
