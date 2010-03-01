class Collector:
    """
    Collectors are plugins that return a specific set of data items pertinent to
    a given Monitor object every time their collect() method is called.  Context
    is given by the Monitor properties that are used to init the Collector.
    """
    def __init__(self, properties):
        """
        The Collector constructor should use the passed-in properties to
        establish context from its owning Monitor.
        Override this method when creating new collectors.
        """
        pass
        
    def collect():
        """
        The principle interface for every Collector.  This method is called by a
        monitor to initiate data collection.
        Override this method when creating new collectors.
        Return: A dictionary of statistics.
        """
        return {}
        
    def instance(properties):
        """
        Override this method when creating new collectors.
        This function is called by Monitor objects to dynamically instantiate a
        set of Collector plugins.
        Return: An instance of this collector initialized with 'properties'
        """
        return Collector(properties)

def get_collectors(config_str, properties):
    """
    Initialize a set of new Collector instances for a Monitor.
    Return: A list of initialized Collectors
    """
    collectors = []
    for name in config_str.split(','):
        name = name.lstrip()
        if name == '':
            continue
        try:
            module = __import__('Collectors.' + name, None, None, name)
        except ImportError:
            logger(LOG_WARN, "Unable to import collector: %s", name)
            continue
        collectors.append(module.instance(properties))
    return collectors
