import os as _os
import sys as _sys
import inspect as _inspect

# Ableton imports this script as a package by its folder name, with only the
# parent "Remote Scripts" directory on sys.path. The modules below (material,
# behaviors, protocol, state_writer) are imported as top-level names, so the
# package's own directory must be on sys.path — the simulator does the same.
#
# NOTE: __file__ is unreliable inside Ableton's Python sandbox (see
# LPX95Custom._script_dir), so resolve this directory via inspect instead.
_HERE = _os.path.dirname(_os.path.realpath(_inspect.getfile(lambda: 0)))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)


def create_instance(c_instance):
    from .LPX95Custom import LPX95Custom
    return LPX95Custom(c_instance)
