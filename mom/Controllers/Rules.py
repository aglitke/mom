import re
import logging
from mom.Entity import *

debug = False

class RuleError(Exception):
    """
    Thrown to flag an error parsing or evaluating the rules.
    """
    def __init__(self, message):
        self.message = message

def evaluate_script(rules, host, guests):
    """
    Construct an environment for the rule script and evaluate it.
    Return: True if evaluation was successful, False otherwise.
    """
    global debug
    # Allow some basic Python concepts to be used in the rule script
    my_locals = { 'True': True, 'False': False, 'abs': abs }
    my_locals['Host'] = host
    my_locals['Guests'] = guests
    
    if debug:
        print "### DEBUG ### Input for rules processing:"
        host._disp('Host')
        for (id, guest) in guests.items():
            guest._disp("Guest:%i" % id)
        print "### DEBUG ###\n"

    # This function is callable from within the rules script.  It will call the
    # given function for each guest with the given optional arguments.
    def for_each_guest(func, args={}, guests=guests):
        for (id, guest) in guests.items():
            func(guest, args)
    my_locals['for_each_guest'] = for_each_guest

    # Evaluate script
    try:
        exec rules['data'] in my_locals
    except Exception, e:
        print "Exception %s occurred while parsing rules" % e
        return False

    # Store any variables back to the persistent entities
    host._store_variables()
    for (id, guest) in guests.items():
        guest._store_variables()

    return True
    
def evaluate(rules, host, guests):
    """
    Stub function to allow multiple rule formats to be evaluated.
    """
    if rules == None:
        return False
    elif rules['type'] == 'script':
        return evaluate_script(rules, host, guests)
    else:
        return False

def read_rules(fname):
    """
    Read a file containing rules definitions.  For now this is a simple
    Python script with a special comment header but eventually this will be
    a new grammar.
    """
    logger = logging.getLogger('mom.Rules')
    if fname == '':
        return None
    f = open(fname, 'r')
    line = f.readline()
    matches = re.match('^#.*Mom Rules.*type=(\S+)', line)
    if matches is None:
        logger.warn("%s is not a valid rules file", fname)
        return None
    if matches.group(1) == 'script':
        return read_rules_script(f)
    else:
        logger.warn("Unsupported rules format: %s", matches.group(1))
        return None

def read_rules_script(fd):
    rules = { 'type': 'script' }
    rules['data'] = fd.read()
    return rules

