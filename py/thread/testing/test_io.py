
import py
import sys

WorkerPool = py._thread.WorkerPool
ThreadOut = py._thread.ThreadOut

def test_threadout_install_deinstall():
    old = sys.stdout
    out = ThreadOut(sys, 'stdout')
    out.deinstall()
    assert old == sys.stdout

class TestThreadOut:
    def test_threadout_one(self):
        out = ThreadOut(sys, 'stdout')
        try:
            l = []
            out.setwritefunc(l.append)
            py.builtin.print_(42,13)
            x = l.pop(0)
            assert x == '42'
            x = l.pop(0)
            assert x == ' '
            x = l.pop(0)
            assert x == '13'
        finally:
            out.deinstall()

    def test_threadout_multi_and_default(self):
        out = ThreadOut(sys, 'stdout')
        try:
            num = 3
            defaults = []
            def f(l):
                out.setwritefunc(l.append)
                sys.stdout.write(str(id(l)))
                out.delwritefunc()
                print(1)
            out.setdefaultwriter(defaults.append)
            pool = WorkerPool()
            listlist = []
            for x in range(num):
                l = []
                listlist.append(l)
                pool.dispatch(f, l)
            pool.shutdown()
            for name, value in out.__dict__.items():
                sys.stderr.write("%s: %s" %(name, value))
            pool.join(2.0)
            for i in range(num):
                item = listlist[i]
                assert item ==[str(id(item))]
            assert not out._tid2out
            assert defaults
            expect = ['1' for x in range(num)]
            defaults = [x for x in defaults if x.strip()]
            assert defaults == expect
        finally:
            out.deinstall()

    def test_threadout_nested(self):
        out1 = ThreadOut(sys, 'stdout')
        try:
            # we want ThreadOuts to coexist
            last = sys.stdout
            out = ThreadOut(sys, 'stdout')
            assert last == sys.stdout
            out.deinstall()
            assert last == sys.stdout
        finally:
            out1.deinstall()
