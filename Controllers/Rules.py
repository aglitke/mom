import re
from Entity import *
import logging

debug = False

class RuleError(Exception):
    """
    Thrown to flag an error parsing or evaluating the rules.
    """
    def __init__(self, message):
        self.message = message

def evaluate_script(rules, entities):
    """
    Construct an environment for the rule script and evaluate it.
    Return: True if evaluation was successful, False otherwise.
    """
    global debug
    # Allow some basic Python concepts to be used in the rule script
    my_locals = { 'True': True, 'False': False, 'abs': abs}
    # Place input and output Entity objects into the script namespace
    entities['Output'] = Entity()
    for name in entities:
        my_locals[name] = entities[name]
    
    if debug:
        print "### DEBUG ### Input for rules processing:"
        for name in entities:
            entities[name]._disp(name)
        print "### DEBUG ###\n"

    # Evaluate script
    try:
        exec rules['data'] in my_locals
    except Exception as e:
        print "Exception %s occurred while parsing rules" % e
        return False
    return True
    
def evaluate(rules, entities):
    """
    Stub function to allow multiple rule formats to be evaluated.
    """
    if rules == None:
        return False
    elif rules['type'] == 'script':
        return evaluate_script(rules, entities)
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

