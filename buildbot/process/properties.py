from zope.interface import implements
from buildbot import util
from twisted.python import log
from twisted.python.failure import Failure

class Properties:
    """
    I represent a set of properties that can be interpolated into various
    strings in buildsteps.

    @ivar properties: dictionary mapping property values to tuples 
        (value, source), where source is a string identifing the source
        of the property.

    Objects of this class can be read like a dictionary -- in this case,
    only the property value is returned.

    As a special case, a property value of None is returned as an empty 
    string when used as a mapping.
    """
    def __init__(self):
        self.properties = {}

    def __getitem__(self, name):
        """Just get the value for this property, special-casing None -> ''"""
        rv = self.properties[name][0]
        if rv is None: rv = ''
        return rv

    def has_key(self, name):
        return self.properties.has_key(name)

    def getProperty(self, name, default=(None,None)):
        """Get the (value, source) tuple for the given property"""
        return self.properties.get(name, default)

    def setProperty(self, name, value, source):
        self.properties[name] = (value, source)

    def update(self, dict, source):
        """Update this object from a dictionary, with an explicit source specified."""
        for k, v in dict.items():
            self.properties[k] = (v, source)

    def updateFromProperties(self, other):
        """Update this object based on another object; the other object's """
        self.properties.update(other.properties)

    def render(self, value):
        """
        Return a variant of value that has any WithProperties objects
        substituted.  This recurses into Python's compound data types.
        """
        if isinstance(value, (str, unicode)):
            return value
        elif isinstance(value, WithProperties):
            return value.render(self)
        elif isinstance(value, list):
            return [ self.render(e) for e in value ]
        elif isinstance(value, tuple):
            return tuple([ self.render(e) for e in value ])
        elif isinstance(value, dict):
            return dict([ (self.render(k), self.render(v)) for k,v in value.iteritems() ])
        else:
            return value

class WithProperties(util.ComparableMixin):
    """This is a marker class, used in ShellCommand's command= argument to
    indicate that we want to interpolate a build property.
    """

    compare_attrs = ('fmtstring', 'args')

    def __init__(self, fmtstring, *args):
        self.fmtstring = fmtstring
        self.args = args

    def render(self, properties):
        if self.args:
            strings = []
            for name in self.args:
                strings.append(properties[name])
            s = self.fmtstring % tuple(strings)
        else:
            s = self.fmtstring % properties
        return s