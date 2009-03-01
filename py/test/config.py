import py
from conftesthandle import Conftest

from py.__.test import parseopt
from py.__.misc.warn import APIWARN

# XXX move to Config class
basetemp = None
def ensuretemp(string, dir=1): 
    """ return temporary directory path with
        the given string as the trailing part. 
    """ 
    global basetemp
    if basetemp is None: 
        basetemp = py.path.local.make_numbered_dir(prefix='pytest-')
    return basetemp.ensure(string, dir=dir) 
  
class CmdOptions(object):
    """ pure container instance for holding cmdline options 
        as attributes. 
    """
    def __repr__(self):
        return "<CmdOptions %r>" %(self.__dict__,)

class Config(object): 
    """ central bus for dealing with configuration/initialization data. """ 
    Option = py.compat.optparse.Option # deprecated
    _initialized = False
    _sessionclass = None

    def __init__(self, pytestplugins=None, topdir=None): 
        self.option = CmdOptions()
        self.topdir = topdir
        self._parser = parseopt.Parser(
            usage="usage: %prog [options] [file_or_dir] [file_or_dir] [...]",
            processopt=self._processopt,
        )
        if pytestplugins is None:
            pytestplugins = py.test._PytestPlugins()
        assert isinstance(pytestplugins, py.test._PytestPlugins)
        self.bus = pytestplugins.pyplugins
        self.pytestplugins = pytestplugins
        self._conftest = Conftest(onimport=self.pytestplugins.consider_conftest)

    def _processopt(self, opt):
        if hasattr(opt, 'default') and opt.dest:
            if not hasattr(self.option, opt.dest):
                setattr(self.option, opt.dest, opt.default)

    def _preparse(self, args):
        self._conftest.setinitial(args) 
        self.pytestplugins.consider_env()
        self.pytestplugins.do_addoption(self._parser)

    def parse(self, args): 
        """ parse cmdline arguments into this config object. 
            Note that this can only be called once per testing process. 
        """ 
        assert not self._initialized, (
                "can only parse cmdline args at most once per Config object")
        self._initialized = True
        self._preparse(args)
        args = self._parser.parse_setoption(args, self.option)
        if not args:
            args.append(py.std.os.getcwd())
        self.topdir = gettopdir(args)
        self.args = [py.path.local(x) for x in args]

    # config objects are usually pickled across system
    # barriers but they contain filesystem paths. 
    # upon getstate/setstate we take care to do everything
    # relative to our "topdir". 
    def __getstate__(self):
        return self._makerepr()
    def __setstate__(self, repr):
        self._repr = repr

    def _initafterpickle(self, topdir):
        self.__init__(
            #issue1
            #pytestplugins=py.test._PytestPlugins(py._com.pyplugins),
            topdir=topdir,
        )
        self._mergerepr(self._repr)
        self._initialized = True
        del self._repr 

    def _makerepr(self):
        l = []
        for path in self.args:
            path = py.path.local(path)
            l.append(path.relto(self.topdir)) 
        return l, self.option

    def _mergerepr(self, repr): 
        # before any conftests are loaded we 
        # need to set the per-process singleton 
        # (also seens py.test.config) to have consistent
        # option handling 
        global config_per_process
        config_per_process = self  
        args, cmdlineopts = repr 
        self.args = [self.topdir.join(x) for x in args]
        self.option = cmdlineopts
        self._preparse(self.args)

    def getcolitems(self):
        return [self.getfsnode(arg) for arg in self.args]

    def getfsnode(self, path):
        path = py.path.local(path)
        assert path.check(), "%s: path does not exist" %(path,)
        # we want our possibly custom collection tree to start at pkgroot 
        pkgpath = path.pypkgpath()
        if pkgpath is None:
            pkgpath = path.check(file=1) and path.dirpath() or path
        Dir = self._conftest.rget("Directory", pkgpath)
        col = Dir(pkgpath, config=self)
        return col._getfsnode(path)

    def getvalue_pathlist(self, name, path=None):
        """ return a matching value, which needs to be sequence
            of filenames that will be returned as a list of Path
            objects (they can be relative to the location 
            where they were found).
        """
        try:
            return getattr(self.option, name)
        except AttributeError:
            try:
                mod, relroots = self._conftest.rget_with_confmod(name, path)
            except KeyError:
                return None
            modpath = py.path.local(mod.__file__).dirpath()
            return [modpath.join(x, abs=True) for x in relroots]
             
    def addoptions(self, groupname, *specs): 
        """ add a named group of options to the current testing session. 
            This function gets invoked during testing session initialization. 
        """ 
        APIWARN("1.0", "define plugins to add options", stacklevel=2)
        group = self._parser.addgroup(groupname)
        for opt in specs:
            group._addoption_instance(opt)
        return self.option 

    def addoption(self, *optnames, **attrs):
        return self._parser.addoption(*optnames, **attrs)

    def getvalue(self, name, path=None): 
        """ return 'name' value looked up from the 'options'
            and then from the first conftest file found up 
            the path (including the path itself). 
            if path is None, lookup the value in the initial
            conftest modules found during command line parsing. 
        """
        try:
            return getattr(self.option, name)
        except AttributeError:
            return self._conftest.rget(name, path)

    def setsessionclass(self, cls):
        if self._sessionclass is not None:
            raise ValueError("sessionclass already set to: %r" %(
                self._sessionclass))
        self._sessionclass = cls

    def initsession(self):
        """ return an initialized session object. """
        cls = self._sessionclass 
        if cls is None:
            from py.__.test.session import Session
            cls = Session
        return cls(self)

    def _reparse(self, args):
        """ this is used from tests that want to re-invoke parse(). """
        #assert args # XXX should not be empty
        global config_per_process
        oldconfig = py.test.config
        try:
            config_per_process = py.test.config = Config()
            config_per_process.parse(args) 
            return config_per_process
        finally: 
            config_per_process = py.test.config = oldconfig 

    def _getcapture(self, path=None):
        if self.option.nocapture:
            iocapture = "no" 
        else:
            iocapture = self.getvalue("conf_iocapture", path=path)
        if iocapture == "fd": 
            return py.io.StdCaptureFD()
        elif iocapture == "sys":
            return py.io.StdCapture()
        elif iocapture == "no": 
            return py.io.StdCapture(out=False, err=False, in_=False)
        else:
            raise ValueError("unknown io capturing: " + iocapture)

    
# this is the one per-process instance of py.test configuration 
config_per_process = Config(
    pytestplugins=py.test._PytestPlugins(py._com.pyplugins)
)

#
# helpers
#

def checkmarshal(name, value):
    try:
        py.std.marshal.dumps(value)
    except ValueError:
        raise ValueError("%s=%r is not marshallable" %(name, value))

def gettopdir(args): 
    """ return the top directory for the given paths.
        if the common base dir resides in a python package 
        parent directory of the root package is returned. 
    """
    args = [py.path.local(arg) for arg in args]
    p = reduce(py.path.local.common, args)
    assert p, "cannot determine common basedir of %s" %(args,)
    pkgdir = p.pypkgpath()
    if pkgdir is None:
        if p.check(file=1):
            p = p.dirpath()
        return p
    else:
        return pkgdir.dirpath()
