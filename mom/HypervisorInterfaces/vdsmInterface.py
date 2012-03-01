# Memory Overcommitment Manager
# Copyright (C) 2012 Mark Wu, IBM Corporation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

import sys
sys.path.append('/usr/share/vdsm')
import API
import supervdsm
import logging
import traceback
from mom.HypervisorInterfaces.HypervisorInterface import *

class vdsmInterface(HypervisorInterface):
    """
    vdsmInterface provides a wrapper for the VDSM API so that VDSM-
    related error handling can be consolidated in one place.  An instance of
    this class provides a single VDSM connection that can be shared by all
    threads.
    """
    vdsm_cif = None

    def __init__(self):
        self.logger = logging.getLogger('mom.vdsmInterface')
        try:
            self._check_conn()
            self.vdsm_api = API.Global(self.vdsm_cif)
            response = self.vdsm_api.ping()
            self._check_status(response)
        except vdsmException,e:
            e.handle_exception()

    @classmethod
    def setConnection(self, conn):
        self.vdsm_cif = conn

    def _check_status(self, response):
        if response['status']['code']:
            raise statusException(response, self.logger)

    def _check_conn(self):
        if self.vdsm_cif == None:
            msg = "VDSM client interface is not initialized yet"
            self.logger.error(msg)
            raise connectionException(msg, self.logger)

    def _vmIsRunning(self, vm):
        if vm['status'] == 'Up':
            return True
        else:
            return False

    def getVmName(self, uuid):
        try:
            self._check_conn()
	    response = self.vdsm_api.getVMList(True, [uuid])
            self._check_status(response)
            return response['vmList'][0]['vmName']
        except vdsmException,e:
            e.handle_exception()
            return None

    def getVmPid(self, uuid):
        try:
            self._check_conn()
            response = self.vdsm_api.getVMList(True, [uuid])
            self._check_status(response)
            return response['vmList'][0]['pid']
        except vdsmException,e:
            e.handle_exception()
            return None

    def getVmList(self):
        vmIds = []
        try:
            self._check_conn()
            response = self.vdsm_api.getVMList()
            self._check_status(response)
            vm_list = response['vmList']
            for vm in vm_list:
                if self._vmIsRunning(vm):
                    vmIds.append(vm['vmId'])
            self.logger.info(vmIds)
            return vmIds
        except vdsmException,e:
            e.handle_exception()
            return None


    def getVmMemoryStats(self, uuid):
        ret = {}
        try:
            self._check_conn()
            vm = API.VM(self.vdsm_cif, uuid)
            response = vm.getStats()
            self._check_status(response)
            ret['memUsage'] = response['statsList'][0]['memUsage']
            self.logger.info(ret)
            return ret
        except vdsmException,e:
            e.handle_exception()
            return None

    def vmSetBalloonTarget(self, vm, target):
        pass

    def getVmInfo(self, id):
        data = {}
        data['uuid'] = id
        data['pid'] = self.getVmPid(id)
        data['name'] = self.getVmName(id)
        if None in data.values():
            return None
        return data

    def getStatsFields(self=None):
        agent_stats = ['memUsage']
        return set(agent_stats)

    def getVmBalloonInfo(self, uuid):
        balloon_stats = ['balloon_cur', 'balloon_max']

    def ksmTune(self, tuningParams):
        # When MOM is lauched by vdsm, it's running without root privileges.
        # So we need resort to supervdsm to set the KSM parameters.
        superVdsm = supervdsm.getProxy()
        superVdsm.ksmTune(tuningParams)

class vdsmException(Exception):
    def __init__(self, msg, logger):
        self.msg = msg
        self.logger = logger
    def handle_exception(self):
        self.logger.error(self.msg)
        self.logger.error(traceback.format_exc())

class statusException(vdsmException):
      pass

class connectionException(vdsmException):
    def handle_exception(self):
        vdsmException.handle_exception(self)
        raise

def instance(config):
    return vdsmInterface()
