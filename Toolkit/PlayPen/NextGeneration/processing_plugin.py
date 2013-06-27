# N.B. these would be handled through the plugin mechanism.

from mosflm import mosflm
from labelit import labelit

# from datamodels import stuff

class processing_plugin:

    def __init__(self):
        self._pp_mosflm = mosflm()
        self._pp_labelit = labelit()

        return

    def _preprocess(self):
        # FIXME I would unmarshall information here

        pass

    def _process(self):

        self._pp_mosflm.set_index_input()
        self._pp_mosflm.index()
        index_output = self._pp_mosflm.get_index_output()

        # check results, raise any errors

        # perhaps use labelit too?

        self._pp_labelit.set_index_input()
        self._pp_labelit.index()
        more_index_output = self._pp_labelit.get_index_output()

        print 'gathering results of indexing, creating integration input'

        # gather results of index into integrate method input

        self._pp_mosflm.set_integrate_input()
        self._pp_mosflm.integrate()
        integrate_output = self._pp_mosflm.get_integrate_output()

        # check results, raise any errors

        return

    def _postprocess(self):
        # FIXME gather results of plugin to xml

        pass

    def process(self):
        '''This would come from EDPlugin.'''

        self._preprocess()
        self._process()
        self._postprocess()

if __name__ == '__main__':

    pp = processing_plugin()

    pp.process()
