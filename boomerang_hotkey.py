#!/usr/bin/env python3
"""CLI helper to send commands to a running Boomerang instance via QLocalSocket.

Usage:  python boomerang_hotkey.py log
This will tell the running app to open the "Log New Idea" window. Returns
non-zero exit code if the app is not running.
"""
import sys
from PySide6.QtNetwork import QLocalSocket
from PySide6.QtCore import QCoreApplication

COMMAND = sys.argv[1] if len(sys.argv) > 1 else "log"

app = QCoreApplication(sys.argv)  # Needed for Qt event loop in PySide6

socket = QLocalSocket()
socket.connectToServer("boomerang_ipc")

if not socket.waitForConnected(500):
    print("Boomerang is not running.")
    sys.exit(1)

socket.write(COMMAND.encode("utf-8"))
socket.flush()
if not socket.waitForBytesWritten(500):
    print("Failed to send command.")
    sys.exit(2)

socket.disconnectFromServer()
print("Command sent:", COMMAND)
