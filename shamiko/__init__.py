# NOTE: gdb uses system python.
# We don't want to import shamiko.app by default
# since it load 3rd party libraries at module level although system python might not be able to load them.
# So we do hacky things as follows:
try:
    import gdb  # NOQA
except ImportError:
    from shamiko.app import Shamiko  # NOQA
    from shamiko.session import Session  # NOQA
