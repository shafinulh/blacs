"""Provide compatibility names for the local Spectrum AWG worker."""

import os

import labscript_utils.h5_lock  # Load the HDF5 lock before pyqtgraph.
import pyqtgraph
from qtutils.qt import QtWidgets


if not hasattr(pyqtgraph, "QtWidgets"):
    pyqtgraph.QtWidgets = QtWidgets

if os.environ.get("BLACS_ALLOW_UNSAFE_QT_STATUS") == "1":
    from qtutils.locking import qtlock

    qtlock.enforce(False)
