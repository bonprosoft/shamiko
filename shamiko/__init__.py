# NOTE: gdb uses system python.
# We don't want to import shamiko.app by default
# since it load 3rd party libraries at module level although system python might not be able to load them.
# So we do hacky things as follows:
try:
    import gdb  # NOQA
except ImportError:
    import shutil
    if shutil.which("gdb") is None:
        raise RuntimeError("gdb command is required") from None

    from shamiko.app import Shamiko  # NOQA
    from shamiko.session import Session  # NOQA

import os


def _get_package_root():
    # type: () -> str
    return os.path.dirname(__file__)


def _get_template_dir():
    # type: () -> str
    root = _get_package_root()
    return os.path.join(root, "templates")
