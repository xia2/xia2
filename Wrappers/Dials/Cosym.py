from __future__ import absolute_import, division, print_function

import os

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Streams import Chatter, Debug

def DialsCosym(DriverType=None,
               decay_correction=None):
  '''A factory for DialsScaleWrapper classes.'''

  DriverInstance = DriverFactory.Driver(DriverType)

  class DialsCosymWrapper(DriverInstance.__class__):
    '''A wrapper for dials.cosym'''

    def __init__(self):
      # generic things
      super(DialsCosymWrapper, self).__init__()

      self.set_executable('dials.cosym')

      # clear all the header junk
      self.reset()

      # input and output files
      self._experiments_json = []
      self._reflections_pickle = []

    # getter and setter methods

    def add_experiments_json(self, experiments_json):
      self._experiments_json.append(experiments_json)

    def add_reflections_pickle(self, reflections_pickle):
      self._reflections_pickle.append(reflections_pickle)

    def get_reindexed_experiments(self):
      return self._reindexed_experiments

    def get_reindexed_reflections(self):
      return self._reindexed_reflections

    def run(self):
      assert len(self._experiments_json)
      assert len(self._reflections_pickle)
      assert len(self._experiments_json) == len(self._reflections_pickle)

      for f in self._experiments_json + self._reflections_pickle:
        assert os.path.isfile(f)
        self.add_command_line(f)

      nproc = PhilIndex.params.xia2.settings.multiprocessing.nproc
      if isinstance(nproc, int) and nproc > 1:
        self.add_command_line('nproc=%i' % nproc)

      self._reindexed_experiments = os.path.join(
        self.get_working_directory(),
        '%i_reindexed_experiments.json' % self.get_xpid())
      self._reindexed_reflections = os.path.join(
        self.get_working_directory(),
        '%i_reindexed_reflections.pickle' % self.get_xpid())

      self.add_command_line("output.experiments='%s'" % self._reindexed_experiments)
      self.add_command_line("output.reflections='%s'" % self._reindexed_reflections)
      self.add_command_line('plot_prefix=%s_' % self.get_xpid())

      self.start()
      self.close_wait()

      # check for errors

      try:
        self.check_for_errors()
      except Exception:
        Chatter.write(
          "dials.cosym failed, see log file for more details:\n  %s" %self.get_log_file())
        raise

      Debug.write('dials.cosym status: OK')

      return 'OK'

    def get_unmerged_reflection_file(self):
      return self._unmerged_reflections

  return DialsCosymWrapper()
