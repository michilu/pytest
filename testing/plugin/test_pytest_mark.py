import py
from py.plugin.pytest_mark import MarkGenerator as Mark

class TestMark:
    def test_pytest_mark_notcallable(self):
        mark = Mark()
        py.test.raises((AttributeError, TypeError), "mark()")

    def test_pytest_mark_bare(self):
        mark = Mark()
        def f(): pass
        mark.hello(f)
        assert f.hello

    def test_pytest_mark_keywords(self):
        mark = Mark()
        def f(): pass
        mark.world(x=3, y=4)(f)
        assert f.world 
        assert f.world.x == 3
        assert f.world.y == 4

    def test_apply_multiple_and_merge(self):
        mark = Mark()
        def f(): pass
        marker = mark.world
        mark.world(x=3)(f)
        assert f.world.x == 3
        mark.world(y=4)(f)
        assert f.world.x == 3
        assert f.world.y == 4
        mark.world(y=1)(f)
        assert f.world.y == 1
        assert len(f.world.args) == 0

    def test_pytest_mark_positional(self):
        mark = Mark()
        def f(): pass
        mark.world("hello")(f)
        assert f.world.args[0] == "hello"
        mark.world("world")(f)

    def test_oldstyle_marker_access(self, recwarn):
        mark = Mark()
        def f(): pass
        mark.world(x=1)(f)
        assert f.world.x == 1
        assert recwarn.pop()

class TestFunctional:
    def test_mark_per_function(self, testdir):
        p = testdir.makepyfile("""
            import py
            @py.test.mark.hello
            def test_hello():
                assert hasattr(test_hello, 'hello')
        """)
        result = testdir.runpytest(p)
        assert result.stdout.fnmatch_lines(["*passed*"])

    def test_mark_per_module(self, testdir):
        item = testdir.getitem("""
            import py
            pytestmark = py.test.mark.hello
            def test_func():
                pass
        """)
        keywords = item.readkeywords()
        assert 'hello' in keywords

    def test_mark_per_class(self, testdir):
        modcol = testdir.getmodulecol("""
            import py
            class TestClass:
                pytestmark = py.test.mark.hello
                def test_func(self):
                    assert TestClass.test_func.hello  
        """)
        clscol = modcol.collect()[0]
        item = clscol.collect()[0].collect()[0]
        keywords = item.readkeywords()
        assert 'hello' in keywords

    def test_merging_markers(self, testdir):
        p = testdir.makepyfile("""
            import py
            pytestmark = py.test.mark.hello("pos1", x=1, y=2)
            class TestClass:
                # classlevel overrides module level
                pytestmark = py.test.mark.hello(x=3)
                @py.test.mark.hello("pos0", z=4)
                def test_func(self):
                    pass
        """)
        items, rec = testdir.inline_genitems(p)
        item, = items
        keywords = item.readkeywords()
        marker = keywords['hello']
        assert marker.args == ["pos0", "pos1"]
        assert marker.kwargs == {'x': 3, 'y': 2, 'z': 4}

    def test_mark_other(self, testdir):
        item = testdir.getitem("""
            import py
            class pytestmark:
                pass
            def test_func():
                pass
        """)
        keywords = item.readkeywords()
