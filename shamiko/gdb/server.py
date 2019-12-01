import shamiko.gdb.wrapper
import shamiko.simple_rpc.server


def create_server(socket_path, session_dir):
    # type: (str, str) -> shamiko.simple_rpc.server.RPCServer

    server = shamiko.simple_rpc.server.RPCServer(socket_path)
    server.register(shamiko.gdb.wrapper.GdbWrapper)
    server.register(shamiko.gdb.wrapper.InferiorWrapper)
    server.register(shamiko.gdb.wrapper.ThreadWrapper)
    server.register(shamiko.gdb.wrapper.FrameWrapper)

    wrapper = shamiko.gdb.wrapper.GdbWrapper()
    server.register_instance(wrapper)
    return server
