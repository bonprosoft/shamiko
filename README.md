# shamiko
[![PyPI](https://img.shields.io/pypi/v/shamiko.svg)](https://pypi.org/project/shamiko/)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/shamiko.svg)](https://pypi.org/project/shamiko/)
[![GitHub license](https://img.shields.io/github/license/bonprosoft/shamiko.svg)](https://github.com/bonprosoft/shamiko)

shamiko is a library for inspecting running Python processes.

It can
- inspect Python processes
  - obtain information about current frames and threads of the running process
- inject arbitrary code into specified frame and thread of the process
- attach the running process with pdb

## Install

```sh
pip install shamiko
```

## CLI

shamiko provides the command-line interface.

```sh
shamiko --help
```

```
Usage: shamiko [OPTIONS] PID COMMAND [ARGS]...

Arguments:
  PID (int): PID of target Python process

Options:
  -e, --executable (str):  executable path of given PID
  -c, --context (str):     context directory of given PID
  --help                   show help message

Commands:
  inspect     inspect the running process
  attach      attach a debugger to the running process
  run-file    inject a python script file into the running process
  run-script  inject a python code into the running process
  shell       launch an interactive shell
```

### inspect

inspect the running process

```
Usage: shamiko PID inspect
```

![](https://raw.githubusercontent.com/bonprosoft/shamiko/master/imgs/inspect.gif)

### attach

attach a debugger to the running process

```
Usage: shamiko PID attach [OPTIONS]

Options:
  --thread (int): thread id where you can obtain by `inspect` command
  --frame (int): frame id where you can obtain by `inspect` command
  --debugger (str): debugger type. available debuggers: [pdb]
```

![](https://raw.githubusercontent.com/bonprosoft/shamiko/master/imgs/attach.gif)

### run-file

inject a python script file into the running process

```
Usage: shamiko PID run-file [OPTIONS] FILE_PATH

Arguments:
  FILE_PATH (str): a path of the python script that you want to inject into given PID

Options:
  --thread (int): thread id where you can obtain by `inspect` command
  --frame (int): frame id where you can obtain by `inspect` command
```

![](https://raw.githubusercontent.com/bonprosoft/shamiko/master/imgs/runfile.gif)

### run-script

inject a python code into the running process

```
Usage: shamiko PID run-script [OPTIONS] SCRIPT

Arguments:
  SCRIPT (str): a python code that you want to inject into given PID

Options:
  --thread (int): thread id where you can obtain by `inspect` command
  --frame (int): frame id where you can obtain by `inspect` command
```

![](https://raw.githubusercontent.com/bonprosoft/shamiko/master/imgs/runscript.gif)

### shell

launch an interactive shell

```
Usage: shamiko PID shell
```

![](https://raw.githubusercontent.com/bonprosoft/shamiko/master/imgs/shell.gif)

## FAQ

### ptrace: Operation not permitted

```
Could not attach to process.  If your uid matches the uid of the target
process, check the setting of /proc/sys/kernel/yama/ptrace_scope, or try
again as the root user.  For more details, see /etc/sysctl.d/10-ptrace.conf
ptrace: Operation not permitted.
```

In most distributions, executing ptrace of non-child processes by a non-super user is disallowed.
You can disable this temporarily by
```sh
echo 0 > /proc/sys/kernel/yama/ptrace_scope
```

### auto-loading has been declined by your `auto-load safe-path' set to "$debugdir:$datadir/auto-load"

```
warning: File "/home/user/.pyenv/versions/3.6.9/bin/python3.6-gdb.py" auto-loading has been declined by your `auto-load safe
-path' set to "$debugdir:$datadir/auto-load".
```

shamiko uses the gdb Python extension script `python-gdb.py`.
To allow auto loading of this file, execute
```sh
echo "add-auto-load-safe-path [path to python-gdb.py]" >> ~/.gdbinit
```
To simply allow auto loading of all pathes, execute
```sh
echo "add-auto-load-safe-path /" >> ~/.gdbinit
```

#### Examples

- To allow Python 3.6 that you installed by pyenv
```sh
echo "add-auto-load-safe-path ~/.pyenv/shims/python3.6-gdb.py" >> ~/.gdbinit
```
