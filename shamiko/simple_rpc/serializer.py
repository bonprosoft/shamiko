import collections
from typing import Any, DefaultDict, Dict, List, Optional, Type

from shamiko.simple_rpc import client


class SerializationPromise(object):
    def __init__(self, instance_id, rpc_client):
        # type: (Any, client.RPCClient) -> None
        self._instance_id = instance_id
        self._rpc_client = rpc_client

    @classmethod
    def _create_promise(cls, instance_id, rpc_client):
        # type: (Any, client.RPCClient) -> Any
        return cls(instance_id, rpc_client)

    def _call_rpc(self, func_name, arguments=None):
        # type: (str, Optional[List[Any]]) -> Any
        if arguments is None:
            arguments = []
        return self._rpc_client.call(
            self.__class__.__name__, func_name, arguments, self._instance_id
        )


class SerializeSession:
    def __init__(self, rpc_client=None):
        # type: (Optional[client.RPCClient]) -> None
        self._instances = collections.defaultdict(
            dict
        )  # type: DefaultDict[str, Any]  # NOQA
        self._promise_class_table = (
            {}
        )  # type: Dict[str, Type[SerializationPromise]]  # NOQA
        self._rpc_client = rpc_client

    def register_promise_class(self, klass):
        # type: (Type[SerializationPromise]) -> None
        self._promise_class_table[klass.__name__] = klass

    def put(self, class_name, instance_id, value):
        # type: (str, Any, Any) -> None
        self._instances[class_name][instance_id] = value

    def get(self, class_name, instance_id, create_promise):
        # type: (str, Any, bool) -> Any
        if create_promise:
            assert self._rpc_client is not None

        d = self._instances[class_name]
        if instance_id not in d:
            if not create_promise:
                raise KeyError("Not found")

            if class_name not in self._promise_class_table:
                raise KeyError("class_name not in promise_class entry")

            assert self._rpc_client is not None
            klass = self._promise_class_table[class_name]
            promise = klass._create_promise(instance_id, self._rpc_client)
            d[instance_id] = promise

        return d[instance_id]


def deserialize(session, object_json, create_promise=False):
    # type: (SerializeSession, Dict[str, Any], bool) -> Any
    otype = object_json["t"]
    value = object_json["v"]
    if otype == "none":
        return None
    elif otype == "int":
        assert isinstance(value, int)
        return value
    elif otype == "float":
        assert isinstance(value, float)
        return value
    elif otype == "str":
        assert isinstance(value, str)
        return value
    elif otype == "list":
        assert isinstance(value, list)
        result = []
        for element in value:
            result.append(deserialize(session, element, create_promise))
        return result
    elif otype == "dict":
        assert isinstance(value, list)
        result = []
        for element in value:
            assert len(element) == 2
            e_key = deserialize(session, element[0], create_promise)
            e_value = deserialize(session, element[1], create_promise)
            result[e_key] = e_value
        return result
    elif otype == "class":
        class_name = object_json["c"]
        return session.get(class_name, value, create_promise)


def _create_entry(otype, value, class_name=None):
    # type: (str, Any, Optional[str]) -> Dict[str, Any]
    entry = {}
    entry["t"] = otype
    entry["v"] = value
    if class_name is not None:
        entry["c"] = class_name

    return entry


def serialize(session, obj):
    # type: (SerializeSession, Any) -> Dict[str, Any]
    if obj is None:
        return _create_entry("none", obj)
    elif isinstance(obj, int):
        return _create_entry("int", obj)
    elif isinstance(obj, float):
        return _create_entry("float", obj)
    elif isinstance(obj, str):
        return _create_entry("str", obj)
    elif isinstance(obj, list) or isinstance(obj, tuple):
        return _create_entry("list", [serialize(session, e) for e in obj])
    elif isinstance(obj, dict):
        elements = []
        for k, v in obj.items():
            k_entry = serialize(session, k)
            v_entry = serialize(session, v)
            elements.append([k_entry, v_entry])
        return _create_entry("dict", elements)
    else:
        class_name = obj.__class__.__name__
        instance_id = obj._key()
        session.put(class_name, instance_id, obj)
        return _create_entry("class", instance_id, class_name)
