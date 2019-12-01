import json
import logging
import os
import socket
import threading
from typing import Any, Dict, Optional

from shamiko.simple_rpc import reader, serializer

_logger = logging.getLogger(__name__)


class SocketServer:
    def __init__(self, socket_path):
        # type: (str) -> None
        self._socket_path = socket_path
        self._lock = threading.Lock()
        self._started = threading.Event()
        self._terminate_request = threading.Event()

    def _handle_connection(self, connection, addr):
        # type: (socket.socket, Any) -> None
        raise NotImplementedError

    def _socket_loop(self):
        # type: () -> None
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(self._socket_path)
        sock.listen(1)
        try:
            while not self._terminate_request.is_set():
                try:
                    connection, addr = sock.accept()
                    with connection:
                        self._handle_connection(connection, addr)
                except Exception:
                    pass  # NOQA
        finally:
            os.remove(self._socket_path)
            sock.close()

    def start(self):
        # type: () -> None
        with self._lock:
            if self._started.is_set():
                raise RuntimeError("Already started")

            self._started.set()

        self._terminate_request.clear()
        try:
            self._socket_loop()
        finally:
            self._started.clear()

    def terminate(self):
        # type: () -> None
        self._terminate_request.set()


class RPCServer(SocketServer):
    def __init__(self, socket_path):
        # type: (str) -> None
        super(RPCServer, self).__init__(socket_path)

        self._session = serializer.SerializeSession()
        self._dispatch_table = {}  # type: Dict[str, type]
        self._reader = reader.BufferedReader()

    def _handle_connection(self, connection, addr):
        # type: (socket.socket, Any) -> None
        while not self._terminate_request.is_set():
            line = connection.recv(4096).decode("utf-8")
            if not line:
                # connection was closed
                self._reader.clear()
                return

            self._reader.write(line)
            requests = self._reader.readlines()

            for request in requests:
                try:
                    _logger.debug("Received: {}".format(request))
                    resp = self._dispatch(line)
                    if resp is not None:
                        resp = "{}\n".format(resp.rstrip("\n"))
                        connection.send(resp.encode("utf-8"))
                except Exception as e:
                    _logger.warn("An unhandled exception occured: {}".format(e))
                    continue  # NOQA

    def register(self, klass):
        # type: (type) -> None
        class_name = klass.__name__
        if class_name in self._dispatch_table:
            raise RuntimeError("Already registered")

        self._dispatch_table[class_name] = klass

    def register_instance(self, instance):
        # type: (Any) -> None
        serializer.serialize(self._session, instance)

    def _create_response(self, ret_value):
        # type: (Any) -> str
        return json.dumps(
            {
                "s": "response",
                "r": serializer.serialize(self._session, ret_value),
            }
        )

    def _create_rpc_error(self, ret_msg):
        # type: (str) -> str
        return json.dumps({"s": "rpc-error", "r": ret_msg})

    def _create_exception(self, exception):
        # type: (Exception) -> str
        return json.dumps(
            {
                "s": "exception",
                "c": exception.__class__.__name__,
                "r": str(exception),
            }
        )

    def _dispatch(self, request_str):
        # type: (str) -> Optional[str]
        request = json.loads(request_str)
        assert isinstance(request, dict)
        if request["s"] == "halt":
            _logger.info("halt request received")
            self.terminate()
            return None
        elif request["s"] == "request":
            return self._dispatch_request(request)
        else:
            return self._create_rpc_error("invalid service type")

    def _dispatch_request(self, request):
        # type: (Dict[str, Any]) -> str
        assert request["s"] == "request"

        class_name = request["m"]
        func_name = request["f"]
        arg_serialized = request["a"]
        instance_id = request.get("i", None)
        instance = None

        klass = self._dispatch_table.get(class_name, None)
        if klass is None:
            return self._create_rpc_error(
                "class:{} not found".format(class_name)
            )

        func = getattr(klass, func_name, None)
        if func is None:
            return self._create_rpc_error(
                "func: {} not found in class:{}".format(func_name, class_name)
            )

        args = []
        for arg in arg_serialized:
            try:
                args.append(
                    serializer.deserialize(
                        self._session, arg, create_promise=False
                    )
                )
            except KeyError:
                return self._create_rpc_error("failed to deserialize argument")

        if instance_id is not None:
            try:
                instance = self._session.get(
                    class_name, instance_id, create_promise=False
                )
            except KeyError:
                return self._create_rpc_error("failed to deserialize instance")

            args = [instance] + args

        try:
            if isinstance(func, property):
                ret_value = func.fget(*args)
            else:
                ret_value = func(*args)
        except Exception as e:
            return self._create_exception(e)

        return self._create_response(ret_value)
