#####################################################################
#                                                                   #
# /__init__.py                                                      #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the program BLACS, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
import os
from .__version__ import __version__

BLACS_DIR = os.path.dirname(os.path.realpath(__file__))

# CODEX CHANGE START: Support old user device imports with pyqtgraph 0.11.
def _add_pyqtgraph_qtwidgets_alias():
    """Add the QtWidgets name used by older local device code."""
    try:
        import labscript_utils.h5_lock  # Load the HDF5 lock before pyqtgraph.
        import pyqtgraph
        from qtutils.qt import QtWidgets
    except ImportError:
        return

    if not hasattr(pyqtgraph, "QtWidgets"):
        pyqtgraph.QtWidgets = QtWidgets


_add_pyqtgraph_qtwidgets_alias()
# CODEX CHANGE END: Support old user device imports with pyqtgraph 0.11.

# CODEX CHANGE START: Optional workaround for the legacy PulseBlaster status UI.
if os.environ.get("BLACS_ALLOW_UNSAFE_QT_STATUS") == "1":
    from qtutils.locking import qtlock

    qtlock.enforce(False)
# CODEX CHANGE END: Optional workaround for the legacy PulseBlaster status UI.
