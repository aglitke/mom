class EntityError(Exception):
    def __init__(self, message):
        self.message = message

class Entity:
    """
    An entity is an object that is designed to be inserted into the rule-
    processing namespace.  The properties and statistics elements allow it to
    contain a snapshot of Monitor data that can be used as inputs to rules.  The
    rule-accessible methods provide a simple syntax for referencing data.
    """
    def __init__(self, monitor=None):
        self.properties = {}
        self.variables = {}
        self.statistics = []
        self.monitor = monitor

    def _set_property(self, name, val):
        self.properties[name] = val

    def _set_variable(self, name, val):
        self.variables[name] = val

    def _set_statistics(self, stats):
        for row in stats:
            self.statistics.append(row)

    def _store_variables(self):
        """
        Pass rule-defined variables back to the Monitor for storage
        """
        if self.monitor is not None:
            self.monitor.update_variables(self.variables)
            
    def _finalize(self):
        """
        Once all data has been added to the Entity, perform any extra processing
        """
        # Add the most-recent stats to the top-level namespace for easy access
        # from within rules scripts.
        if len(self.statistics) > 0:
            for stat in self.statistics[-1].keys():
                setattr(self, stat, self.statistics[-1][stat])

    def _disp(self, name=''):
        """
        Debugging function to display the structure of an Entity.
        """
        prop_str = ""
        stat_str = ""
        for i in self.properties.keys():
            prop_str = prop_str + " " + i

        if len(self.statistics) > 0:
            for i in self.statistics[0].keys():
                stat_str = stat_str + " " + i
        else:
            stat_str = ""
        print "Entity: %s {" % name
        print "    properties = { %s }" % prop_str
        print "    statistics = { %s }" % stat_str
        print "}"

    ### Rule-accesible Methods 
    def Prop(self, name):
        """
        Get the value of a single property
        """
        return self.properties[name]

    def Stat(self, name):
        """
        Get the most-recently recorded value of a statistic
        Returns None if no statistics are available
        """
        if len(self.statistics) > 0:
            return self.statistics[-1][name]
        else:
            return None

    def StatAvg(self, name):
        """
        Calculate the average value of a statistic using all recent values.
        """
        if (len(self.statistics) == 0):
            raise EntityError("Statistic '%s' not available" % name)
        total = 0
        for row in self.statistics:
            total = total + row[name]
        return float(total / len(self.statistics))

    def SetVar(self, name, val):
        """
        Store a named value in this Entity.
        """
        self.variables[name] = val

    def GetVar(self, name):
        """
        Get the value of a potential variable in this instance.
        Returns None if the variable has not been defined.
        """
        if name in self.variables:
            return self.variables[name]
        else:
            return None
