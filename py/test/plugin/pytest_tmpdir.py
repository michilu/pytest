"""
example:

    pytest_plugins = "pytest_tmpdir" 

    def test_plugin(tmpdir):
        tmpdir.join("hello").write("hello")

"""
import py

class TmpdirPlugin:
    """ provide temporary directories to test functions and methods. 
    """ 

    def pytest_funcarg__tmpdir(self, request):
        name = request.function.__name__ 
        return request.config.mktemp(name, numbered=True)

# ===============================================================================
#
# plugin tests 
#
# ===============================================================================
#
def test_generic(plugintester):
    plugintester.hookcheck(TmpdirPlugin)

def test_funcarg(testdir):
    from py.__.test.funcargs import FuncargRequest
    item = testdir.getitem("def test_func(tmpdir): pass")
    plugin = TmpdirPlugin()
    p = plugin.pytest_funcarg__tmpdir(FuncargRequest(item, "tmpdir"))
    assert p.check()
    bn = p.basename.strip("0123456789-")
    assert bn.endswith("test_func")
