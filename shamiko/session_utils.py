import contextlib
from typing import Callable, Iterator, Optional

from shamiko.app import Shamiko
from shamiko.gdb_rpc import FrameWrapper, InferiorWrapper, ThreadWrapper
from shamiko.session import Session


def visit(
    inferior,  # type: InferiorWrapper
    visit_thread,  # type: Callable[[ThreadWrapper], bool]
    visit_frame,  # type: Callable[[FrameWrapper], bool]
    frame_predicate,  # type: Callable[[FrameWrapper], bool]
):
    # type: (...) -> bool
    for thread in inferior.threads:
        if not visit_thread(thread):
            continue

        thread.switch()

        for frame in thread.get_python_frames():
            if not visit_frame(frame):
                continue

            if frame_predicate(frame):
                return True

    return False


def traverse_frame(
    inferior,  # type: InferiorWrapper
    predicate,  # type: Callable[[FrameWrapper], bool]
    thread_id=None,  # type: Optional[int]
    frame_idx=None,  # type: Optional[int]
):
    # type: (...) -> bool

    def default_thread(_):
        # type: (ThreadWrapper) -> bool
        return True

    if thread_id is not None:

        def thread_pred(thread):
            # type: (ThreadWrapper) -> bool
            tid = thread.num
            return tid == thread_id

    else:

        def thread_pred(thread):
            # type: (ThreadWrapper) -> bool
            return True

    visit_thread = thread_pred

    if frame_idx is not None:

        def frame_pred(frame):
            # type: (FrameWrapper) -> bool
            idx = frame.get_index()
            return idx == frame_idx

    else:

        def frame_pred(frame):
            # type: (FrameWrapper) -> bool
            return True

    visit_frame = frame_pred

    return visit(inferior, visit_thread, visit_frame, predicate)


@contextlib.contextmanager
def create_session(pid, executable=None, context_dir=None):
    # type: (int, Optional[str], Optional[str]) -> Iterator[Session]
    with Shamiko() as smk:
        session = smk.attach(pid, executable, context_dir)
        with session as s:
            yield s
