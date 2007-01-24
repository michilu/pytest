import py
from setupdata import setupdatadir

def setup_module(mod):
    mod.datadir = setupdatadir()
    mod.tmpdir = py.test.ensuretemp(mod.__name__) 

class TestDefaultSession: 
    def test_simple(self): 
        config = py.test.config._reparse([datadir/'filetest.py']) 
        session = config.getsessionclass()(config, py.std.sys.stdout)
        session.main()
        l = session.getitemoutcomepairs(py.test.Item.Failed)
        assert len(l) == 2 
        l = session.getitemoutcomepairs(py.test.Item.Passed)
        assert not l 

    def test_simple_verbose(self): 
        config = py.test.config._reparse([datadir/'filetest.py', 
                                                '--verbose']) 
        session = config.getsessionclass()(config, py.std.sys.stdout)
        session.main()
        l = session.getitemoutcomepairs(py.test.Item.Failed)
        assert len(l) == 2 
        l = session.getitemoutcomepairs(py.test.Item.Passed)
        assert not l 

    def test_simple_verbose_verbose(self): 
        config = py.test.config._reparse([datadir/'filetest.py', 
                                                '-v', '-v']) 
        session = config.getsessionclass()(config, py.std.sys.stdout)
        session.main()
        l = session.getitemoutcomepairs(py.test.Item.Failed)
        assert len(l) == 2 
        l = session.getitemoutcomepairs(py.test.Item.Passed)
        assert not l 

    def test_session_parsing(self):
        from py.__.test.terminal.terminal import TerminalSession
        from py.__.test.tkinter.reportsession import ReportSession
        config = py.test.config._reparse(['--session=terminal'])
        assert issubclass(config.getsessionclass(), TerminalSession)
        config = py.test.config._reparse(['--session=tkinter'])
        assert issubclass(config.getsessionclass(), ReportSession)
        config = py.test.config._reparse(['--tkinter'])
        assert issubclass(config.getsessionclass(), ReportSession)

class TestKeywordSelection: 
    def test_select_simple(self): 
        for keyword in ['test_one', 'est_on']:
            config = py.test.config._reparse([datadir/'filetest.py', 
                                                   '-k', keyword])
            session = config.getsessionclass()(config, py.std.sys.stdout)
            session.main()
            l = session.getitemoutcomepairs(py.test.Item.Failed)
            assert len(l) == 1 
            item = l[0][0]
            assert item.name == 'test_one'
            l = session.getitemoutcomepairs(py.test.Item.Skipped)
            assert len(l) == 1 

    def test_select_extra_keywords(self): 
        o = tmpdir.ensure('selecttest', dir=1)
        tfile = o.join('test_select.py').write(py.code.Source("""
            def test_1():
                pass 
            class TestClass: 
                def test_2(self): 
                    pass
        """))
        conftest = o.join('conftest.py').write(py.code.Source("""
            import py
            class Class(py.test.collect.Class): 
                def haskeyword(self, keyword): 
                    return keyword == 'xxx' or \
                           super(Class, self).haskeyword(keyword) 
        """))
        for keyword in ('xxx', 'xxx test_2', 'TestClass', 'xxx -test_1', 
                        'TestClass test_2', 'xxx TestClass test_2',): 
            f = py.std.StringIO.StringIO()
            config = py.test.config._reparse([o, '-k', keyword]) 
            session = config.getsessionclass()(config, f) 
            session.main()
            print "keyword", repr(keyword)
            l = session.getitemoutcomepairs(py.test.Item.Passed)
            assert len(l) == 1
            assert l[0][0].name == 'test_2'
            l = session.getitemoutcomepairs(py.test.Item.Skipped)
            assert l[0][0].name == 'test_1' 
   
#f = open('/tmp/logfile', 'wa')  
class TestTerminalSession: 

    def setup_class(cls):
        (datadir / 'syntax_error.py').write("\nthis is really not python\n")

    def teardown_class(cls):
        (datadir / 'syntax_error.py').remove()

    def mainsession(self, *args): 
        from py.__.test.terminal.terminal import TerminalSession
        self.file = py.std.StringIO.StringIO() 
        config = py.test.config._reparse(list(args))
        session = TerminalSession(config, file=self.file) 
        session.main()
        return session

    def test_terminal(self): 
        session = self.mainsession(datadir / 'filetest.py')
        out = self.file.getvalue() 
        l = session.getitemoutcomepairs(py.test.Item.Failed)
        assert len(l) == 2
        assert out.find('2 failed') != -1 

    def test_syntax_error_module(self): 
        session = self.mainsession(datadir / 'syntax_error.py')
        l = session.getitemoutcomepairs(py.test.Item.Failed)
        assert len(l) == 1 
        out = self.file.getvalue() 
        assert out.find(str('syntax_error.py')) != -1
        assert out.find(str('not python')) != -1

    def test_exit_first_problem(self): 
        session = self.mainsession("--exitfirst", 
                                   datadir / 'filetest.py')
        assert session.config.option.exitfirst
        l = session.getitemoutcomepairs(py.test.Item.Failed)
        assert len(l) == 1 
        l = session.getitemoutcomepairs(py.test.Item.Passed)
        assert not l 

    def test_collectonly(self): 
        session = self.mainsession("--collectonly", 
                                   datadir / 'filetest.py')
        assert session.config.option.collectonly
        out = self.file.getvalue()
        #print out 
        l = session.getitemoutcomepairs(py.test.Item.Failed)
        #if l: 
        #    x = l[0][1].excinfo
        #    print x.exconly() 
        #    print x.traceback
        assert len(l) == 0 
        for line in ('filetest.py', 'test_one', 
                     'TestClass', 'test_method_one'): 
            assert out.find(line) 

    def test_recursion_detection(self): 
        o = tmpdir.ensure('recursiontest', dir=1)
        tfile = o.join('test_recursion.py')
        tfile.write(py.code.Source("""
            def test_1():
                def f(): 
                    g() 
                def g(): 
                    f() 
                f() 
        """))
        session = self.mainsession(o)
        print "back from main", o
        out = self.file.getvalue() 
        #print out
        i = out.find('Recursion detected') 
        assert i != -1 

    def test_generator_yields_None(self): 
        o = tmpdir.ensure('generatornonetest', dir=1)
        tfile = o.join('test_generatornone.py')
        tfile.write(py.code.Source("""
            def test_1():
                yield None 
        """))
        session = self.mainsession(o) 
        out = self.file.getvalue() 
        #print out
        i = out.find('TypeError') 
        assert i != -1 

    def test_capturing_hooks_simple(self): 
        o = tmpdir.ensure('capturing', dir=1)
        tfile = o.join('test_capturing.py').write(py.code.Source("""
            import py
            print "module level output"
            def test_capturing():
                print 42
                print >>py.std.sys.stderr, 23 
            def test_capturing_error():
                print 1
                print >>py.std.sys.stderr, 2
                raise ValueError
        """))
        conftest = o.join('conftest.py').write(py.code.Source("""
            import py
            class Function(py.test.Function): 
                def startcapture(self): 
                    self._mycapture = py.io.OutErrCapture() 
                    
                def finishcapture(self): 
                    self._testmycapture = self._mycapture.reset()
        """))
        session = self.mainsession(o) 
        l = session.getitemoutcomepairs(py.test.Item.Passed)
        assert len(l) == 1
        item = l[0][0]
        assert hasattr(item, '_testmycapture')
        print item._testmycapture
        out, err = item._testmycapture 
        assert int(out.strip()) == 42
        assert int(err.strip()) == 23 

        assert isinstance(item.parent, py.test.collect.Module)
        out, err = item.parent.getouterr()
        assert out.find('module level output') != -1 
        allout = self.file.getvalue()
        print "allout:", allout
        assert allout.find('module level output') != -1, (
                           "session didn't show module output")

    def test_raises_output(self): 
        o = tmpdir.ensure('raisestest', dir=1)
        tfile = o.join('test_raisesoutput.py')
        tfile.write(py.code.Source("""
            import py
            def test_raises_doesnt():
                py.test.raises(ValueError, int, "3")
        """))
        session = self.mainsession(o) 
        out = self.file.getvalue() 
        if not out.find("DID NOT RAISE") != -1: 
            print out
            py.test.fail("incorrect raises() output") 

    def test_order_of_execution(self): 
        o = tmpdir.ensure('ordertest', dir=1)
        tfile = o.join('test_orderofexecution.py')
        tfile.write(py.code.Source("""
            l = []
            def test_1():
                l.append(1)
            def test_2():
                l.append(2)
            def test_3():
                assert l == [1,2]
            class Testmygroup:
                reslist = l
                def test_1(self):
                    self.reslist.append(1)
                def test_2(self):
                    self.reslist.append(2)
                def test_3(self):
                    self.reslist.append(3)
                def test_4(self):
                    assert self.reslist == [1,2,1,2,3]
        """))

        session = self.mainsession(o) 
        l = session.getitemoutcomepairs(py.test.Item.Failed)
        assert len(l) == 0 
        l = session.getitemoutcomepairs(py.test.Item.Passed)
        assert len(l) == 7 
        # also test listnames() here ... 
        item, result = l[-1]
        assert item.name == 'test_4' 
        names = item.listnames()
        assert names == ['ordertest', 'test_orderofexecution.py', 'Testmygroup', '()', 'test_4']

    def test_nested_import_error(self): 
        o = tmpdir.ensure('Ians_importfailure', dir=1) 
        tfile = o.join('test_import_fail.py')
        tfile.write(py.code.Source("""
            import import_fails
            def test_this():
                assert import_fails.a == 1
        """))
        o.join('import_fails.py').write(py.code.Source("""
            import does_not_work 
            a = 1
        """))
        session = self.mainsession(o) 
        l = session.getitemoutcomepairs(py.test.Item.Failed)
        assert len(l) == 1 
        item, outcome = l[0]
        assert str(outcome.excinfo).find('does_not_work') != -1 

    def test_safe_repr(self):
        session = self.mainsession(datadir/'brokenrepr.py')
        out = self.file.getvalue()
        print 'Output of simulated "py.test brokenrepr.py":'
        print out
        
        l = session.getitemoutcomepairs(py.test.Item.Failed)
        assert len(l) == 2
        assert out.find("""[Exception("Ha Ha fooled you, I'm a broken repr().") raised in repr()]""") != -1 #'
        assert out.find("[unknown exception raised in repr()]") != -1

    def test_E_on_correct_line(self):
        o = tmpdir.ensure('E_on_correct_line', dir=1)
        tfile = o.join('test_correct_line.py')
        source = py.code.Source("""
            import py
            def test_hello():
                assert (None ==
                        ['a',
                         'b',
                         'c'])
        """)
        tfile.write(source)
        session = self.mainsession(o) 
        out = self.file.getvalue()
        print 'Output of simulated "py.test test_correct_line.py":'
        print out
        i = out.find('test_correct_line.py:')
        assert i >= 0
        linenum = int(out[i+len('test_correct_line.py:')])  # a single char
        line_to_report = source[linenum-1]
        expected_output = '\nE   ' + line_to_report + '\n'
        print 'Looking for:', expected_output
        assert expected_output in out


from py.__.test.terminal.remote import getrootdir 
class TestRemote: 
    def test_rootdir_is_package(self): 
        d = tmpdir.ensure('rootdirtest1', dir=1) 
        d.ensure('__init__.py')
        x1 = d.ensure('subdir', '__init__.py')
        x2 = d.ensure('subdir2', '__init__.py')
        x3 = d.ensure('subdir3', 'noinit', '__init__.py')
        assert getrootdir([x1]) == d 
        assert getrootdir([x2]) == d 
        assert getrootdir([x1,x2]) == d 
        assert getrootdir([x3,x2]) == d 
        assert getrootdir([x2,x3]) == d 

    def test_rootdir_is_not_package(self): 
        one = tmpdir.ensure('rootdirtest1', 'hello') 
        rootdir = getrootdir([one]) 
        assert rootdir == one.dirpath() 

    def test_exec(self): 
        o = tmpdir.ensure('remote', dir=1) 
        tfile = o.join('test_exec.py')
        tfile.write(py.code.Source("""
            def test_1():
                assert 1 == 0 
        """))
        print py.std.sys.executable
        config = py.test.config._reparse(
                        ['--exec=' + py.std.sys.executable, 
                         o])
        assert config.option._remote 
        cls = config.getsessionclass() 
        out = []  # out = py.std.Queue.Queue() 
        session = cls(config, out.append) 
        session.main()
        for s in out: 
            if s.find('1 failed') != -1: 
                break 
        else: 
            py.test.fail("did not see test_1 failure") 

    def test_looponfailing(self): 
        o = tmpdir.ensure('looponfailing', dir=1) 
        tfile = o.join('test_looponfailing.py')
        tfile.write(py.code.Source("""
            def test_1():
                assert 1 == 0 
        """))
        print py.std.sys.executable
        config = py.test.config._reparse(['--looponfailing', str(o)])
        assert config.option._remote 
        cls = config.getsessionclass() 
        out = py.std.Queue.Queue() 
        session = cls(config, out.put) 
        pool = py._thread.WorkerPool() 
        reply = pool.dispatch(session.main)
        while 1: 
            s = out.get()
            if s.find('1 failed') != -1: 
                break 
        else: 
            py.test.fail("did not see test_1 failure") 
        # XXX we would like to have a cleaner way to finish 
        try: 
            reply.get(timeout=0.5) 
        except IOError, e: 
            assert str(e).lower().find('timeout') != -1 

        
