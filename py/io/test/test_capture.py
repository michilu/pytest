import os, sys
import py

class TestFDCapture: 
    def test_basic(self): 
        tmpfile = py.std.os.tmpfile() 
        fd = tmpfile.fileno()
        cap = py.io.FDCapture(fd)
        os.write(fd, "hello")
        f = cap.done()
        s = f.read()
        assert s == "hello"

    def test_stderr(self): 
        cap = py.io.FDCapture(2)
        cap.setasfile('stderr')
        print >>sys.stderr, "hello"
        f = cap.done()
        s = f.read()
        assert s == "hello\n"

    def test_stdin(self): 
        f = os.tmpfile()
        print >>f, "3"
        f.seek(0)
        cap = py.io.FDCapture(0, tmpfile=f)
        # check with os.read() directly instead of raw_input(), because
        # sys.stdin itself may be redirected (as py.test now does by default)
        x = os.read(0, 100).strip()
        f = cap.done()
        assert x == "3"

class TestCapturing: 
    def getcapture(self): 
        return py.io.OutErrCapture()

    def test_capturing_simple(self):
        cap = self.getcapture()
        print "hello world"
        print >>sys.stderr, "hello error"
        out, err = cap.reset()
        assert out == "hello world\n"
        assert err == "hello error\n"

    def test_capturing_twice_error(self):
        cap = self.getcapture() 
        print "hello"
        cap.reset()
        py.test.raises(EnvironmentError, "cap.reset()")

    def test_capturing_modify_sysouterr_in_between(self):
        oldout = sys.stdout 
        olderr = sys.stderr 
        cap = self.getcapture()
        print "hello",
        print >>sys.stderr, "world",
        sys.stdout = py.std.StringIO.StringIO() 
        sys.stderr = py.std.StringIO.StringIO() 
        print "not seen" 
        print >>sys.stderr, "not seen"
        out, err = cap.reset()
        assert out == "hello"
        assert err == "world"
        assert sys.stdout == oldout 
        assert sys.stderr == olderr 

    def test_capturing_error_recursive(self):
        cap1 = self.getcapture() 
        print "cap1"
        cap2 = self.getcapture() 
        print "cap2"
        out2, err2 = cap2.reset()
        py.test.raises(EnvironmentError, "cap2.reset()")
        out1, err1 = cap1.reset() 
        assert out1 == "cap1\n"
        assert out2 == "cap2\n"

    def test_intermingling(self): 
        cap = self.getcapture()
        os.write(1, "1")
        print >>sys.stdout, 2,
        os.write(1, "3")
        os.write(2, "a")
        print >>sys.stderr, "b",
        os.write(2, "c")
        out, err = cap.reset()
        assert out == "123" 
        assert err == "abc" 

def test_callcapture(): 
    def func(x, y): 
        print x
        print >>py.std.sys.stderr, y
        return 42
  
    res, out, err = py.io.callcapture(func, 3, y=4) 
    assert res == 42 
    assert out.startswith("3") 
    assert err.startswith("4") 
    
def test_just_out_capture(): 
    cap = py.io.OutErrCapture(out=True, err=False)
    print >>sys.stdout, "hello"
    print >>sys.stderr, "world"
    out, err = cap.reset()
    assert out == "hello\n"
    assert not err 

def test_just_err_capture(): 
    cap = py.io.OutErrCapture(out=False, err=True)
    print >>sys.stdout, "hello"
    print >>sys.stderr, "world"
    out, err = cap.reset()
    assert err == "world\n"
    assert not out 

def test_capture_no_sys(): 
    cap = py.io.OutErrCapture(patchsys=False)
    print >>sys.stdout, "hello"
    print >>sys.stderr, "world"
    os.write(1, "1")
    os.write(2, "2")
    out, err = cap.reset()
    assert out == "1"
    assert err == "2"

#class TestCapturingOnFDs(TestCapturingOnSys):
#    def getcapture(self): 
#        return Capture() 
