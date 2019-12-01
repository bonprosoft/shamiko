import json
import logging
import socket
import threading
from typing import Any, List, Optional

from shamiko.simple_rpc import serializer, reader

_logger = logging.getLogger(__name__)


class SocketClient:
    def __init__(self, socket_path):
        # type: (str) -> None
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.connect(socket_path)
        self._closed = threading.Event()
        self._reader = reader.BufferedReader()

    def close(self):
        # type: () -> None
        self._closed.set()
        self._socket.close()

    def communicate(self, request, noresponse=False):
        # type: (str, bool) -> Optional[str]
        if self._closed.is_set():
            raise RuntimeError("Already closed")

        request = request.rstrip("\n")
        request = "{}\n".format(request)
        self._socket.send(request.encode("utf-8"))
        if noresponse:
            return None

        while True:
            data = self._socket.recv(4096).decode("utf-8")
            _logger.debug("Response: %s", data)
            self._reader.write(data)
            response = self._reader.readlines()
            if len(response) > 0:
                assert len(response) == 1
                return response[0]


class RPCClient(SocketClient):
    def __init__(self, socket_path):
        # type: (str) -> None
        super(RPCClient, self).__init__(socket_path)

        self._session = serializer.SerializeSession(self)

    def terminate_server(self):
        # type: () -> None
        try:
            terminate = {
                "s": "halt",
            }
            request = json.dumps(terminate)
            self.communicate(request, noresponse=True)
        finally:
            self.close()

    def register_promise_class(self, klass):
        # type: (type) -> None
        self._session.register_promise_class(klass)

    def get_promise(self, klass, instance_id):
        # type: (type, Any) -> Any
        return self._session.get(
            klass.__name__, instance_id, create_promise=True
        )

    def call(self, class_name, func_name, args, instance_id):
        # type: (str, str, Optional[List[Any]], Optional[Any]) -> Any
        arg_serialized = []
        if args is not None:
            for arg in args:
                arg_serialized.append(serializer.serialize(self._session, arg))

        body = {
            "s": "request",
            "m": class_name,
            "f": func_name,
            "a": arg_serialized,
        }
        if instance_id is not None:
            # check if instance is exists
            self._session.get(class_name, instance_id, create_promise=False)
            body["i"] = instance_id

        request = json.dumps(body)
        response = self.communicate(request)
        if response is None:
            raise RuntimeError("RPCCall failed")

        response_dict = json.loads(response)
        if response_dict["s"] == "response":
            return serializer.deserialize(
                self._session, response_dict["r"], create_promise=True
            )
        elif response_dict["s"] == "exception":
            raise RuntimeError(
                "An exception occured in remote server:\n"
                + "Exception class: {}\n".format(response_dict["c"])
                + "Exception message: {}\n".format(response_dict["r"])
            )
        elif response_dict["s"] == "rpc-error":
            raise RuntimeError(
                "An RPC exception occured:\n"
                + "message: {}\n".format(response_dict["r"])
            )
        else:
            raise RuntimeError("Unknown response")
