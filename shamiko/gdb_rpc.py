import os
from typing import List, Optional, Tuple, Union

from shamiko.simple_rpc.client import RPCClient
from shamiko.simple_rpc.serializer import SerializationPromise


class FrameWrapper(SerializationPromise):
    def run_simple_string(self, py_str):
        # type: (str) -> None
        return self._call_rpc("run_simple_string", [py_str])

    def run_file(self, file_path):
        # type: (str) -> None

        # NOTE: In order to avoid confusion, we use an absolute path for file_path
        file_path = os.path.abspath(file_path)
        return self._call_rpc("run_file", [file_path])

    def is_evalframe(self):
        # type: () -> bool
        return self._call_rpc("is_evalframe")

    def is_other_python_frame(self):
        # type: () -> Union[bool, str]
        return self._call_rpc("is_other_python_frame")

    @property
    def is_optimized_out(self):
        # type: () -> bool
        return self._call_rpc("is_optimized_out")

    @property
    def filename(self):
        # type: () -> Optional[str]
        return self._call_rpc("filename")

    @property
    def current_line_num(self):
        # type: () -> Optional[int]
        return self._call_rpc("current_line_num")

    @property
    def current_line(self):
        # type: () -> Optional[str]
        return self._call_rpc("current_line")

    def get_index(self):
        # type: () -> int
        return self._call_rpc("get_index")

    def check_selected(self):
        # type: () -> bool
        return self._call_rpc("check_selected")

    def select(self):
        # type: () -> bool
        return self._call_rpc("select")

    def list_local_variables(self):
        # type: () -> List[str]
        return self._call_rpc("list_local_variables")

    def list_global_variables(self):
        # type: () -> List[str]
        return self._call_rpc("list_global_variables")

    def get_variable_repr(self, variable_name, repr_max_len=1024):
        # type: (str, Optional[int]) -> Optional[Tuple[str, str]]
        return self._call_rpc(
            "get_variable_repr", [variable_name, repr_max_len]
        )


class ThreadWrapper(SerializationPromise):
    @property
    def global_num(self):
        # type: () -> int
        return self._call_rpc("global_num")

    @property
    def num(self):
        # type: () -> int
        return self._call_rpc("num")

    @property
    def ptid(self):
        # type: () -> Tuple[int, int, int]
        return self._call_rpc("ptid")

    @property
    def name(self):
        # type: () -> str
        return self._call_rpc("name")

    @property
    def is_exited(self):
        # type: () -> bool
        return self._call_rpc("is_exited")

    @property
    def is_running(self):
        # type: () -> bool
        return self._call_rpc("is_running")

    @property
    def is_stopped(self):
        # type: () -> bool
        return self._call_rpc("is_stopped")

    @property
    def is_valid(self):
        # type: () -> bool
        return self._call_rpc("is_valid")

    @property
    def is_selected(self):
        # type: () -> bool
        return self._call_rpc("is_selected")

    def switch(self):
        # type: () -> None
        return self._call_rpc("switch")

    def get_python_frames(self):
        # type: () -> List[FrameWrapper]
        return self._call_rpc("get_python_frames")


class InferiorWrapper(SerializationPromise):
    @property
    def threads(self):
        # type: () -> List[ThreadWrapper]
        return self._call_rpc("threads")

    @property
    def pid(self):
        # type: () -> int
        return self._call_rpc("pid")

    @property
    def num(self):
        # type: () -> int
        return self._call_rpc("num")

    @property
    def was_attached(self):
        # type: () -> bool
        return self._call_rpc("was_attached")

    @property
    def is_valid(self):
        # type: () -> bool
        return self._call_rpc("is_valid")


class GdbWrapper(SerializationPromise):
    def get_inferior(self):
        # type: () -> List[InferiorWrapper]
        return self._call_rpc("get_inferior")

    def get_selected_inferior(self):
        # type: () -> InferiorWrapper
        return self._call_rpc("get_selected_inferior")

    def get_selected_thread(self):
        # type: () -> ThreadWrapper
        return self._call_rpc("get_selected_thread")

    def execute(self, cmd):
        # type: (str) -> str
        return self._call_rpc("execute", [cmd])


def create_rpc_client(socket_path):
    # type: (str) ->  RPCClient
    client = RPCClient(socket_path)
    client.register_promise_class(GdbWrapper)
    client.register_promise_class(InferiorWrapper)
    client.register_promise_class(ThreadWrapper)
    client.register_promise_class(FrameWrapper)

    return client
