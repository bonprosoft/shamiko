from __future__ import absolute_import

import contextlib
import os
import subprocess
import tempfile
import threading
import time
from typing import Callable, Iterator, Optional

import click
import jinja2

import shamiko
from shamiko import proc_utils, session_utils
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
    if not proc_utils.pid_exists(pid):
        click.echo("Pid={} doesn't exists.".format(pid))

    ctx.obj = {}
    ctx.obj["pid"] = pid
    ctx.obj["executable"] = executable
    ctx.obj["context"] = context


@contextlib.contextmanager
def _get_session(ctx):
    # type: (click.Context) -> Iterator[Session]
    with session_utils.create_session(
        ctx.obj["pid"], ctx.obj["executable"], ctx.obj["context"]
    ) as session:
        yield session


@contextlib.contextmanager
def _get_inferior(ctx):
    # type: (click.Context) -> Iterator[InferiorWrapper]
    with _get_session(ctx) as s:
        inferior = s.session.get_inferior()[0]
        yield inferior


def _run(
    ctx,  # type: click.Context
    func,  # type: Callable[[FrameWrapper], bool]
    thread,  # type: Optional[int]
    frame,  # type: Optional[int]
):
    # type: (...) -> bool
    with _get_inferior(ctx) as inferior:
        return session_utils.traverse_frame(inferior, func, thread, frame)


def _print_result_message(result):
    # type: (bool) -> None
    if result:
        click.echo("Ran successfully")
    else:
        click.echo(
            "Traversed all matched frames, but couldn't run successfully"
        )
        click.echo("HINT: Try without --thread or --frame option")


@cli.command(help="inspect the running process")
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

    with _get_inferior(ctx) as inferior:
        session_utils.visit(
            inferior, visit_thread, visit_frame, lambda _: False
        )


@cli.command(help="inject a python script file into the running process")
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

    _print_result_message(_run(ctx, impl, thread, frame))


@cli.command(help="inject a python code into the running process")
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

    _print_result_message(_run(ctx, impl, thread, frame))


AVAILABLE_DEBUGGERS = [
    "pdb",
]


@cli.command(help="attach a debugger to the running process")
@click.option("--thread", type=int, default=None)
@click.option("--frame", type=int, default=None)
@click.option(
    "--debugger", type=click.Choice(AVAILABLE_DEBUGGERS), default=None
)
@click.pass_context
def attach(ctx, thread, frame, debugger):
    # type: (click.Context, Optional[int], Optional[int], Optional[str]) -> None
    debugger = debugger or "pdb"
    assert debugger in AVAILABLE_DEBUGGERS

    template_name = "attach_{}.py.template".format(debugger)
    template_dir = shamiko._get_template_dir()
    env = jinja2.Environment(
        autoescape=False, loader=jinja2.FileSystemLoader(template_dir)
    )
    template = env.get_template(template_name)
    disposed = threading.Event()

    with tempfile.TemporaryDirectory(prefix="shamiko_dbg_") as session_root:
        socket_path = os.path.join(session_root, "proc.sock")
        script_path = os.path.join(session_root, "script.py")

        script = template.render(unix_socket_path=socket_path)
        with open(script_path, "w") as f:
            f.write(script)

        def connect_stream():
            # type: () -> None
            dt = 0.1
            wait_sec = 100.0
            max_counter = int(wait_sec / dt)

            for i in range(max_counter):
                if os.path.exists(socket_path) or disposed.is_set():
                    break

                if i % 10 == 0:
                    click.echo("waiting for the session to get ready...")

                time.sleep(dt)
            else:
                raise RuntimeError("couldn't open socket. something went wrong")

            if disposed.is_set():
                return

            process = subprocess.Popen(["nc", "-U", socket_path],)

            click.echo("session opened")
            while True:
                if process.poll() is not None:
                    return

                time.sleep(dt)

        def impl(frame):
            # type: (FrameWrapper) -> bool
            try:
                frame.run_file(script_path)
            except Exception:
                return False

            return True

        t = threading.Thread(target=connect_stream)
        t.start()
        try:
            ret = _run(ctx, impl, thread, frame)
            if not ret:
                # show message only when traversing is failed
                _print_result_message(ret)
        finally:
            disposed.set()
        t.join()


def _launch_ipshell(pid, session):
    # type: (int, GdbWrapper) -> None
    from IPython.terminal.embed import InteractiveShellEmbed
    from IPython.config.loader import Config

    banner = """

=== SHAMIKO SHELL ===
Opened a session to pid={}. You can access it from the variable `session`.
=====================

""".format(
        pid
    )
    ipshell = InteractiveShellEmbed(
        config=Config(), banner1=banner, exit_msg="Bye."
    )
    ipshell()


@cli.command(help="launch an interactive shell")
@click.pass_context
def shell(ctx):
    # type: (click.Context) -> None
    with _get_session(ctx) as session:
        _launch_ipshell(ctx.obj["pid"], session.session)


if __name__ == "__main__":
    cli()
