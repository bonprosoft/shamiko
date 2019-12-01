import sys
from typing import Any, List, Optional, Tuple, Union

import six

import gdb

python_dbg_module = sys.modules["__main__"]
PyFrame = python_dbg_module.Frame


def _gdb_execute(command):
    # type: (str) -> str
    # TODO: handling from_tty might be required
    result = gdb.execute(command, to_string=True)
    prefix = "+ {}\n".format(command)
    return result.lstrip(prefix)


def _get_frame_index(frame):
    # type: (Any) -> int
    index = 0
    while frame:
        frame = frame.newer()
        index += 1

    return index


def acquire_gil(func):  # type: ignore
    def impl(*args):
        # type: (Any) -> Any
        out = _gdb_execute("call (void*) PyGILState_Ensure()")
        gil_state = next((x for x in out.split() if x.startswith("$")), "$1")
        ret_value = func(*args)
        _gdb_execute("call (void) PyGILState_Release({})".format(gil_state))
        return ret_value

    return impl


class FrameWrapper:
    def __init__(self, pygdb_frame):
        # type: (Any) -> None
        self._frame = pygdb_frame

    def _key(self):
        # type: () -> int
        return id(self._frame)

    def _get_pyop(self):
        # type: () -> Any
        pyop = self._frame.get_pyop()
        if pyop:
            return pyop

        raise RuntimeError("Unable to read information on python frame")

    @acquire_gil  # type: ignore
    def run_simple_string(self, py_str):
        # type: (str) -> None
        self.check_selected()

        py_str = py_str.replace('"', '\\"')
        _gdb_execute('call (void) PyRun_SimpleString("{}")'.format(py_str))

    def run_file(self, file_path):
        # type: (str) -> None
        if '"' in file_path or "'" in file_path:
            raise RuntimeError("Invalid path")

        command = "with open('{}') as f: exec(f.read())".format(file_path)
        return self.run_simple_string(command)

    def is_evalframe(self):
        # type: () -> bool
        return self._frame.is_evalframe()

    def is_other_python_frame(self):
        # type: () -> Union[bool, str]
        return self._frame.is_other_python_frame()

    @property
    def is_optimized_out(self):
        # type: () -> bool
        return self._get_pyop().is_optimized_out()

    @property
    def filename(self):
        # type: () -> Optional[str]
        return self._get_pyop().filename()

    @property
    def current_line_num(self):
        # type: () -> Optional[int]
        return self._get_pyop().current_line_num()

    @property
    def current_line(self):
        # type: () -> Optional[str]
        return self._get_pyop().current_line()

    def get_index(self):
        # type: () -> int
        return _get_frame_index(self._frame)

    def check_selected(self):
        # type: () -> bool
        idx = self.get_index()
        selected_idx = _get_frame_index(gdb.selected_frame())

        return idx == selected_idx

    def select(self):
        # type: () -> bool
        return self._frame.select()

    def list_local_variables(self):
        # type: () -> List[str]
        variables = []
        for pyop_name, pyop_value in self._get_pyop().iter_locals():
            variables.append(pyop_name.proxyval(set()))

        return variables

    def list_global_variables(self):
        # type: () -> List[str]
        variables = []
        for pyop_name, pyop_value in self._get_pyop().iter_globals():
            variables.append(pyop_name.proxyval(set()))

        return variables

    def get_variable_repr(self, variable_name, repr_max_len=1024):
        # type: (str, Optional[int]) -> Optional[Tuple[str, str]]
        pyop_var, scope = self._get_pyop().get_var_by_name(variable_name)

        if pyop_var:
            return scope, pyop_var.get_truncated_repr(repr_max_len)
        else:
            return None


class ThreadWrapper:
    def __init__(self, gdb_thread):
        # type: (Any) -> None
        self._thread = gdb_thread

    def _key(self):
        # type: () -> int
        return self.global_num

    @property
    def global_num(self):
        # type: () -> int
        return self._thread.global_num

    @property
    def num(self):
        # type: () -> int
        return self._thread.num

    @property
    def ptid(self):
        # type: () -> Tuple[int, int, int]
        # NOTE: returns [PID, LWPID, TID]
        return self._thread.ptid

    @property
    def name(self):
        # type: () -> str
        return self._thread.name

    @property
    def is_exited(self):
        # type: () -> bool
        return self._thread.is_exited()

    @property
    def is_running(self):
        # type: () -> bool
        return self._thread.is_running()

    @property
    def is_stopped(self):
        # type: () -> bool
        return self._thread.is_stopped()

    @property
    def is_valid(self):
        # type: () -> bool
        return self._thread.is_valid()

    @property
    def inferior(self):
        # type: () -> InferiorWrapper
        return InferiorWrapper(self._thread.inferior)

    @property
    def is_selected(self):
        # type: () -> bool
        return gdb.selected_thread().global_num == self.global_num

    def switch(self):
        # type: () -> None
        return self._thread.switch()

    def get_python_frames(self):
        # type: () -> List[FrameWrapper]
        if not self.is_selected:
            raise RuntimeError("the thread is not active")

        result = []
        frame = PyFrame(gdb.newest_frame())
        while frame:
            try:
                if frame.is_python_frame():
                    result.append(FrameWrapper(frame))
            except Exception:
                pass  # NOQA
            frame = frame.older()

        return result


class InferiorWrapper:
    def __init__(self, gdb_inferior):
        # type: (Any) -> None
        self._inferior = gdb_inferior

    def _key(self):
        # type: () -> int
        return self.num

    @property
    def threads(self):
        # type: () -> List[ThreadWrapper]
        return list(six.moves.map(ThreadWrapper, self._inferior.threads()))

    @property
    def pid(self):
        # type: () -> int
        return self._inferior.pid

    @property
    def num(self):
        # type: () -> int
        return self._inferior.num

    @property
    def was_attached(self):
        # type: () -> bool
        return self._inferior.was_attached

    @property
    def is_valid(self):
        # type: () -> bool
        return self._inferior.is_valid()


class GdbWrapper:
    def _key(self):
        # type: () -> int
        return 1

    def get_inferior(self):
        # type: () -> List[InferiorWrapper]
        return list(six.moves.map(InferiorWrapper, gdb.inferiors()))

    def get_selected_inferior(self):
        # type: () -> InferiorWrapper
        return InferiorWrapper(gdb.selected_inferior())

    def get_selected_thread(self):
        # type: () -> ThreadWrapper
        return ThreadWrapper(gdb.selected_thread())

    def execute(self, cmd):
        # type: (str) -> str
        return _gdb_execute(cmd)
