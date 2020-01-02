from __future__ import absolute_import

import os
import logging
import tempfile
import threading
from typing import Any, Dict, Optional

import shamiko.session
import shamiko.proc_utils

_logger = logging.getLogger(__name__)


class Shamiko:
    def __init__(self):
        # type: () -> None
        self._root_dir = tempfile.TemporaryDirectory(prefix="shamiko_")
        self._sessions = {}  # type: Dict[int, shamiko.session.Session]
        self._lock = threading.RLock()

    def dispose(self):
        # type: () -> None
        with self._lock:
            sessions = self._sessions.copy()
            for pid in sessions.keys():
                self.remove(pid)

            self._root_dir.cleanup()

    def __enter__(self):
        # type: () -> Shamiko
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: (Any, Any, Any) -> None
        self.dispose()

    def attach(self, pid, executable=None, context_directory=None):
        # type: (int, Optional[str], Optional[str]) -> shamiko.session.Session
        if executable is None:
            executable = shamiko.proc_utils.guess_executable(pid)
            _logger.info("Guessing executable of PID=%d: %s", pid, executable)
            if executable is None:
                raise RuntimeError("Failed to guess executable")

        if context_directory is None:
            context_directory = shamiko.proc_utils.guess_context_dir(pid)
            _logger.info("Guessing context dir of PID=%d: %s", pid, context_directory)
            if context_directory is None:
                context_directory = os.getcwd()

        with self._lock:
            if pid in self._sessions:
                return self._sessions[pid]

            session = shamiko.session.Session(
                self._root_dir.name, pid, executable, context_directory
            )
            self._sessions[pid] = session

        session.start()
        started = session.wait_for_available(timeout=10.0)
        if started:
            return session
        else:
            with self._lock:
                if pid in self._sessions:
                    self._sessions.pop(pid)

            raise RuntimeError("Couldn't launch session")

    def remove(self, pid):
        # type: (int) -> None
        session = self._sessions.get(pid, None)
        if session is None:
            return

        session.terminate()
        with self._lock:
            if pid in self._sessions:
                self._sessions.pop(pid)
