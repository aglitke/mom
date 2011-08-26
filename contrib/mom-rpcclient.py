#!/usr/bin/env python
# Memory Overcommitment Manager
# Copyright (C) 2011 Adam Litke, IBM Corporation
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

import xmlrpclib
from optparse import *
import sys

default_port = 8989

def ping(mom):
    if mom.ping():
        print "OK"

def getPolicy(mom):
    print mom.getPolicy()
    
def setPolicy(mom, fname):
    f = open(fname, 'r')
    policy = f.read()
    f.close()
    if not mom.setPolicy(policy):
        print "Failed to set policy! Check the syntax."

def setVerbosity(mom, verbosity):
    valid_levels = ('1','2','3','4','5','debug','info','warn','error','critical')
    if verbosity not in valid_levels:
        print "Invalid level specified!"
        return False
    mom.setVerbosity(verbosity)

def _print_stats(stats):
    f_max = reduce(lambda x, y: max(x, len(y)), stats.keys(), 0)
    for (key, val) in stats.items():
        pad = f_max - len(key)
        print "%s:%s %s" % (key, ' '*pad, val)

def getStatistics(mom):
    stats = mom.getStatistics()
    
    print "Host:\n====="
    _print_stats(stats['host'])
    for (key, val) in stats['guests'].items():
        print "\nGuest %s:\n=======%s" % (key, len(key)*'=')
        _print_stats(val)

def getActiveGuests(mom):
    guests = mom.getActiveGuests()
    for guest in guests:
        print guest

def usage(parser):
    parser.usageExit()

def main():
    global default_port
    usage = "usage: %prog [options] <command> [command_options]"
    parser = OptionParser(usage)
    parser.add_option('-p', '--port', dest='port', type='int',
                      default=default_port, metavar='PORT',
                      help='Connect using specified port number [%default]')
    cmds = OptionGroup(parser, "Commands",
                       "Select one of these commands to execute")
    cmds.add_option('--ping', dest='cmd', action='append_const', const='ping',
                    help='(No arguments) Ping the MOM RPC Server')
    cmds.add_option('--get-policy', dest='cmd', action='append_const',
                    const='get_policy', help='(No arguments) Print the currently active MOM policy')
    cmds.add_option('--set-policy', dest='cmd', action='append_const',
                    const='set_policy', help='(FILE) Set new MOM policy from FILE')
    cmds.add_option('--set-verbosity', dest='cmd', action='append_const',
                    const='set_verbosity', help='(LEVEL) Set verbosity to LEVEL')
    cmds.add_option('--get-statistics', dest='cmd', action='append_const',
                    const='get_statistics', help='(No arguments) Get the latest host and guest statistics')
    cmds.add_option('--get-active-guests', dest='cmd', action='append_const',
                    const='get_active_guests', help='(No arguments) Get a list of guests that are being actively managed')
    parser.add_option_group(cmds)
    (options, args) = parser.parse_args()

    if options.cmd is None or len(options.cmd) != 1:
        parser.error("Exactly one command argument is required")

    mom = xmlrpclib.ServerProxy('http://localhost:%i' % options.port)
    try:
        if options.cmd[0] == 'ping':
            ping(mom)
        elif options.cmd[0] == 'get_policy':
            getPolicy(mom)
        elif options.cmd[0] == 'set_policy':
            if len(args) != 1:
                parser.error("A filename must follow --set-policy")
            setPolicy(mom, args[0])
        elif options.cmd[0] == 'set_verbosity':
            if len(args) != 1:
                parser.error("A level must follow --set-verbosity")
            setVerbosity(mom, args[0])
        elif options.cmd[0] == 'get_statistics':
            getStatistics(mom)
        elif options.cmd[0] == 'get_active_guests':
            getActiveGuests(mom)
    except Exception, e:
        print "Command '%s' failed: %s" % (options.cmd[0], e)
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
