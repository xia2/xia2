#!/usr/bin/env python
# BioXHitDBInterface.py
#
#   Copyright (C) 2007 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# An interface to the CCP4i / BioXHit database handler, to allow recording
# of progress during data reduction.
#

import os
import sys
import exceptions

class _BioXHitDBInterfaceReal:
    '''A class to mediate transactions with the CCP4i database.'''

    def __init__(self):

        self._user = ccp4i.GetUserId()
        if not self._user:
            self._user = 'unknown'

        dbClientAPI.DbStartHandler()
        self._connection = dbClientAPI.handlerconnection()
        self._connection.DbRegister(self._user, 'dummy', True)

        self._project = None

        return

    def create_project(self, project, directory):
        '''Create a new CCP4i project in directory.'''

        result = self._connection.CreateDatabase(
            project, directory)

        status = result[0]
        result = result[1:]

        if not status == 'OK':
            raise RuntimeError, 'failed to create project %s' % project

        self._project = project


    def create_job(self, job,
                   input_files = [],
                   output_files = [],
                   log_file = None):
        '''Create a job within this project.'''

        if not self._project:
            raise RuntimeError, 'no current project'

        result = self._connection.NewRecord(self._project)

        status = result[0]
        result = result[1:]

        if not status == 'OK':
            raise RuntimeError, 'error creating job in project %s' % \
                  self._project

        job_id = result[0]

        for f in input_files:
            self._connection.AddInputFile(project, job_id, f)

        for f in output_files:
            self._connection.AddOutputFile(project, job_id, f)

        if log_file:
            self._connection.SetLogfile(project, job_id, log_file)

        # set the job name in here...
        # want to set TITLE, TASKNAME, STATUS

        self._connection.SetData(self._project, job_id, 'TASKNAME', job)

        return

    def __del__(self):
        self._connection.HandlerDisconnect()


class _BioXHitDBInterfaceFake:
    '''A class to do nothing if ccp4i db handler not available.'''

    def __init__(self):
        pass

    def create_project(self, project, directory):
        pass

    def create_job(self, job,
                   input_files = [],
                   output_files = [],
                   log_file = None):
        pass


try:

    sys.path.append('/home/graeme/bioxhit/dbccp4i-0.1/dbccp4i')
    sys.path.append('/home/graeme/bioxhit/dbccp4i-0.1/ClientAPI')

    import ccp4i
    import dbClientAPI

    BioXHitDBInterface = _BioXHitDBInterfaceReal()

except exceptions.Exception, e:

    print '%s' % str(e)

    BioXHitDBInterface = _BioXHitDBInterfaceFake()

if __name__ == '__main__':

    import time

    project = 'demo%d' % int(time.time())

    BioXHitDBInterface.create_project(project, os.getcwd())
    BioXHitDBInterface.create_job('foo', log_file = 'arse.log')
