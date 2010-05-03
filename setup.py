#!/usr/bin/env python

from distutils.core import setup

setup(name='MOM',
      version='0.1',
      description='Memory Overcommitment Manager',
      author='Adam Litke',
      author_email='agl@us.ibm.com',
      url='https://w3.tap.ibm.com/w3ki08/display/KVMTB/Memory+Overcommit+Manager',
      packages=['mom', 'mom.Collectors', 'mom.Controllers'],
      keywords=['Requires: libvirt'],
      data_files=[('/usr/sbin', ['momd']),
                  ('/usr/share/doc/mom/examples',
                   ['doc/mom-balloon.conf', 'doc/balloon.rules',
                    'doc/mom-balloon+ksm.conf', 'doc/ksm.rules']
                  )],
     )

