## shamiko.simple\_rpc

### NOTE

The gdb uses the system python.
Since we don't want users to install 3rd party libraries into system python, we should use 3rd party libraries as little as possible.
We know that we can link a library at runtime by `-ex py sys.path.append(...)`.
To use this hack, the library has to work correctly under the system python, both Python 2.x and Python 3.x.

We also found that the gdb prohibits access from a thread that is newly created by the thread the gdb provides.
In other words, only the thread gdb provides has permission to access memory.

You can check this fact by the following code:
```py
import threading

import gdb


def func():
    gdb.execute("py-bt-full")


print("In gdb thread")
func()

thread = threading.Thread(target=func)
print("In other thread")
thread.start()
thread.join()
```
with the following commands:
```sh
gdb -p [pid] -x poc.py
```
Results:
```
In gdb thread
#7 <built-in method acquire of _thread.lock object at remote 0x7f8ffde48af8>
...
In other thread
#7 <unknown at remote 0x7f8ffde70318>
Python Exception <class 'gdb.MemoryError'> Cannot access memory at address 0x565347501278:
Exception in thread Thread-1:
Traceback (most recent call last):
  File "/usr/lib/python3.6/threading.py", line 916, in _bootstrap_inner
    self.run()
  File "/usr/lib/python3.6/threading.py", line 864, in run
    self._target(*self._args, **self._kwargs)
  File "poc.py", line 7, in func
    gdb.execute("py-bt-full")
gdb.error: Error occurred in Python command: Cannot access memory at address 0x565347501278
```

Since it is bothersome to find a suitable RPC library, as a first PoC, we also developed a tiny RPC library that can work only with Python standard libraries.
But we don't want to maintain this RPC library, so we should find an awesome RPC library that meets our requirements as a next step.
