from __future__ import absolute_import

import contextlib
from typing import Callable, Iterator, Optional

import click

import shamiko.utils
from shamiko.app import Shamiko
from shamiko.gdb_rpc import (
    FrameWrapper,
    GdbWrapper,
    InferiorWrapper,
    ThreadWrapper,
)
from shamiko.session import Session


@click.group()
@click.argument("pid", type=int, required=True)
@click.option("--executable", "-e", type=str, default=None)
@click.option("--context", "-c", type=str, default=None)
@click.pass_context
def cli(ctx, pid, executable, context):
    # type: (click.Context, int, Optional[str], Optional[str]) -> None
    if not shamiko.utils.pid_exists(pid):
        click.echo("Pid={} doesn't exists.".format(pid))

    ctx.obj = {}
    ctx.obj["pid"] = pid
    ctx.obj["executable"] = executable
    ctx.obj["context"] = context


def _visit(
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


def _traverse_frame(
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

    return _visit(inferior, visit_thread, visit_frame, predicate)


@contextlib.contextmanager
def _create_session(ctx):
    # type: (click.Context) -> Iterator[Session]
    with Shamiko() as smk:
        session = smk.attach(
            ctx.obj["pid"], ctx.obj["executable"], ctx.obj["context"]
        )
        with session as s:
            yield s


@contextlib.contextmanager
def _get_session_inferior(ctx):
    # type: (click.Context) -> Iterator[InferiorWrapper]
    with _create_session(ctx) as s:
        inferior = s.session.get_inferior()[0]
        yield inferior


def _run(
    ctx,  # type: click.Context
    func,  # type: Callable[[FrameWrapper], bool]
    thread,  # type: Optional[int]
    frame,  # type: Optional[int]
):
    # type: (...) -> None

    with _get_session_inferior(ctx) as inferior:
        ret = _traverse_frame(inferior, func, thread, frame)
        if ret:
            click.echo("Ran successfully")
        else:
            click.echo(
                "Traversed all matched frames, but couldn't run successfully"
            )
            click.echo("HINT: Try without --thread or --frame option")


@cli.command()
@click.pass_context
def inspect(ctx):
    # type: (click.Context) -> None

    def visit_thread(thread):
        # type: (ThreadWrapper) -> bool
        args = {
            "num": thread.num,
            "global_num": thread.global_num,
            "ptid": thread.ptid,
            "name": thread.name,
            "is_running": thread.is_running,
            "is_exited": thread.is_exited,
            "is_stopped": thread.is_stopped,
        }
        fmt = """=== Frame [num={num}] ===
 - name: {name}
 - ptid: {ptid}
 - global_num: {global_num}
 - is_running: {is_running}
 - is_exited: {is_exited}
 - is_stopped: {is_stopped}
 - available python frames"""
        click.echo(fmt.format(**args))
        return True

    def visit_frame(frame):
        # type: (FrameWrapper) -> bool
        description = "(Unknown Frame)"

        if frame.is_evalframe:
            description = "(unable to read python frame information)"
            try:
                filename = frame.filename
                line_num = frame.current_line_num
                description = "File={}:{}".format(filename, line_num)
            except Exception:
                pass  # NOQA
        else:
            info = frame.is_other_python_frame
            if info:
                description = info

        fmt = "   * Frame #{}: {}".format(frame.get_index(), description)
        click.echo(fmt)
        return True

    with _get_session_inferior(ctx) as inferior:
        _visit(inferior, visit_thread, visit_frame, lambda _: False)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--thread", type=int, default=None)
@click.option("--frame", type=int, default=None)
@click.pass_context
def run_file(ctx, file_path, thread, frame):
    # type: (click.Context, str, Optional[int], Optional[int]) -> None

    def impl(frame):
        # type: (FrameWrapper) -> bool
        try:
            frame.run_file(file_path)
        except Exception:
            return False

        return True

    _run(ctx, impl, thread, frame)


@cli.command()
@click.argument("script", type=str)
@click.option("--thread", type=int, default=None)
@click.option("--frame", type=int, default=None)
@click.pass_context
def run_script(ctx, script, thread, frame):
    # type: (click.Context, str, Optional[int], Optional[int]) -> None

    def impl(frame):
        # type: (FrameWrapper) -> bool
        try:
            frame.run_simple_string(script)
        except Exception:
            return False

        return True

    _run(ctx, impl, thread, frame)


def _launch_ipshell(pid, session):
    # type: (int, GdbWrapper) -> None
    from IPython.terminal.embed import InteractiveShellEmbed
    from IPython.config.loader import Config

    banner = """

=== SHAMIKO SHELL ===
Opened a session to pid={}. You can access it from the variable `session`.
=====================

""".format(pid)
    ipshell = InteractiveShellEmbed(
        config=Config(), banner1=banner, exit_msg="Bye."
    )
    ipshell()


@cli.command()
@click.pass_context
def attach(ctx):
    # type: (click.Context) -> None
    with _create_session(ctx) as session:
        _launch_ipshell(ctx.obj["pid"], session.session)


if __name__ == "__main__":
    cli()
