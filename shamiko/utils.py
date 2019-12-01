import os
from typing import Optional

import psutil


def _get_proc(pid):
    # type: (int) -> Optional[psutil.Process]
    try:
        return psutil.Process(pid)
    except psutil.NoSuchProcess:
        return None


def pid_exists(pid):
    # type: (int) -> bool
    return psutil.pid_exists(pid)


def guess_executable(pid):
    # type: (int) -> Optional[str]
    proc = _get_proc(pid)
    if proc is None:
        return None
    return os.path.abspath(proc.exe())


def guess_context_dir(pid):
    # type: (int) -> Optional[str]
    proc = _get_proc(pid)
    if proc is None:
        return None
    return os.path.abspath(proc.cwd())
