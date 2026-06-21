import os as _os
import sys as _sys

# Ableton imports this script as a package by its folder name, with only the
# parent "Remote Scripts" directory on sys.path. The modules below (material,
# behaviors, protocol, state_writer) are imported as top-level names, so the
# package's own directory must be on sys.path — the simulator does the same.
_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)


def create_instance(c_instance):
    from .LPX95Custom import LPX95Custom
    return LPX95Custom(c_instance)
