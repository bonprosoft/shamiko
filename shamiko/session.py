from __future__ import absolute_import

import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import typing
from typing import Any, Optional

import shamiko
import shamiko.gdb_rpc

if typing.TYPE_CHECKING:
    import shamiko.simple_rpc.client

_logger = logging.getLogger(__name__)


class Session:
    def __init__(self, root_dir, pid, executable, context_directory):
        # type: (str, int, str, str) -> None
        self._pid = pid
        self._executable = executable

        self._context_directory = os.path.abspath(context_directory)
        self._session_directory = os.path.join(root_dir, "sessions", str(pid))
        self._bootstrap_path = os.path.join(self._session_directory, "run.py")
        self._socket_path = os.path.join(
            self._session_directory, "session.sock"
        )

        self._client = (
            None
        )  # type: Optional[shamiko.simple_rpc.client.RPCClient]
        self._gdb_thread = None  # type: Optional[threading.Thread]
        self._available = threading.Event()
        self._terminate_requested = threading.Event()
        self._lock = threading.Lock()

    def _initialize_session_dir(self):
        # type: () -> None
        os.makedirs(self._session_directory, exist_ok=False)
        shutil.copyfile(
            os.path.join(shamiko._get_template_dir(), "bootstrap.py.template"),
            self._bootstrap_path,
        )

    def _remove_session_dir(self):
        # type: () -> None
        shutil.rmtree(self._session_directory)

    def _wait_for_socket(self):
        # type: () -> bool
        dt = 0.1
        wait_sec = 10.0
        max_counter = int(wait_sec / dt)

        for i in range(max_counter):
            if os.path.exists(self._socket_path):
                break

            if i % 10 == 0:
                _logger.info("Waiting for the session to get ready...")

            time.sleep(dt)
        else:
            _logger.warn("Failed to communicate with bootstrap script")
            return False

        return True

    def _gdb_loop(self):
        # type: () -> None
        package_dir_parent = os.path.dirname(shamiko._get_package_root())
        command = [
            "gdb",
            "-q",
            self._executable,
            "-p",
            str(self._pid),
            "-batch",
            "-ex",
            "set trace-commands on",
            "-ex",
            "set directories {}".format(self._context_directory),
            "-ex",
            "py sys.path.append('{}')".format(package_dir_parent),
            "-x",
            self._bootstrap_path,
        ]
        try:
            self._initialize_session_dir()
            proc = subprocess.Popen(command, stderr=sys.stderr)

            try:
                if not self._wait_for_socket():
                    return

                self._client = shamiko.gdb_rpc.create_rpc_client(
                    self._socket_path
                )
                try:
                    self._available.set()
                    while (
                        proc.poll() is None
                        and not self._terminate_requested.is_set()
                    ):
                        time.sleep(0.1)

                    if self._terminate_requested.is_set():
                        _logger.info("Sending terminate server request")
                        self._client.terminate_server()
                        try:
                            proc.wait(10.0)
                        except subprocess.TimeoutExpired:
                            pass  # NOQA
                    else:
                        _logger.warn("Process exited with unexpected reason")
                finally:
                    self._client.close()
            finally:
                if proc.poll() is None:
                    _logger.warn("killing process")
                    proc.kill()
        finally:
            self._client = None
            self._gdb_thread = None
            self._available.set()
            self._remove_session_dir()

    def start(self):
        # type: () -> None
        with self._lock:
            if self._gdb_thread is not None:
                raise RuntimeError("Already started")

            self._gdb_thread = threading.Thread(target=self._gdb_loop)

        self._available.clear()
        self._terminate_requested.clear()
        self._gdb_thread.start()

    def wait_for_available(self, timeout):
        # type: (float) -> bool
        self._available.wait(timeout)

        return self._client is not None

    def terminate(self, join=True):
        # type: (bool) -> None
        self._terminate_requested.set()
        if join:
            thread = self._gdb_thread
            if thread is not None:
                thread.join()

    def __enter__(self):
        # type: () -> Session
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: (Any, Any, Any) -> None
        self.terminate(join=True)

    @property
    def session(self):
        # type: () -> shamiko.gdb_rpc.GdbWrapper

        with self._lock:
            if self._client is None:
                raise RuntimeError("Session not started")

            entry_point = self._client.get_promise(
                shamiko.gdb_rpc.GdbWrapper, 1
            )

        return entry_point
