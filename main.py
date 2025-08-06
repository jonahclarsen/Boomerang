import os
import sys
import traceback

from PySide6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QMessageBox, QFileDialog)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtNetwork import QLocalServer

from idea_manager import load_options, save_options, get_ideas_folder, set_ideas_folder, list_due_ideas, start_backup_thread, perform_backup
from ui import ProcessWindow, AddIdeaWindow, OptionsWindow
def handle_exception(exc_type, exc_value, exc_traceback):
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(error_msg)
    QMessageBox.critical(None, "Unexpected Error", error_msg)

sys.excepthook = handle_exception

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Hide from dock on macOS
    import platform
    if platform.system() == 'Darwin':  # macOS
        try:
            from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
            NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        except Exception as e:
            print(e)
            traceback.print_exc()

    # Tray Icon
    tray = QSystemTrayIcon()
    tray.setIcon(QIcon('icon.png'))
    tray.setVisible(True)

    menu = QMenu()
    bring_back_action = QAction("Bring it Back")
    log_new_action = QAction("Log New Idea")
    backup_now_action = QAction("Backup Now")
    options_action = QAction("Options")
    quit_action = QAction("Quit")
    menu.addAction(bring_back_action)
    menu.addAction(log_new_action)
    menu.addSeparator()
    menu.addAction(backup_now_action)
    menu.addAction(options_action)
    menu.addSeparator()
    menu.addAction(quit_action)
    tray.setContextMenu(menu)

    # Keep references to windows to prevent garbage collection
    open_windows = []

    # Load options and handle startup
    options = load_options()
    ideas_folder = get_ideas_folder(options)
    if not ideas_folder:
        folder = QFileDialog.getExistingDirectory(None, "Select Ideas Folder")
        if folder:
            set_ideas_folder(options, folder)
            ideas_folder = folder
        else:
            sys.exit(0)
    elif not os.path.exists(ideas_folder):
        reply = QMessageBox.question(None, "Folder Not Found", f"The ideas folder '{ideas_folder}' does not exist. Create it?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            os.makedirs(ideas_folder, exist_ok=True)
            print(f"Created folder {ideas_folder}")
        else:
            folder = QFileDialog.getExistingDirectory(None, "Select Ideas Folder")
            if folder:
                set_ideas_folder(options, folder)
                ideas_folder = folder
            else:
                sys.exit(0)

    def open_process_window():
        if list_due_ideas(ideas_folder):
            window = ProcessWindow(ideas_folder)
            open_windows.append(window)
            window.show()
            try:
                window.raise_()
                window.activateWindow()
            except Exception:
                pass
        else:
            QMessageBox.information(None, "No Ideas", "No ideas to process today.")

    def open_add_window():
        print("Opening add window")
        window = AddIdeaWindow(ideas_folder)
        open_windows.append(window)
        window.show()
        try:
            window.raise_()
            window.activateWindow()
        except Exception as e:
            print(e)
            pass

    def backup_now():
        perform_backup(options, show_prompts=True)

    def open_options():
        dialog = OptionsWindow(options)
        if dialog.exec():
            # Save updated options
            save_options(options)
            # Update ideas_folder if it changed
            if dialog.selected_folder:
                ideas_folder = dialog.selected_folder

    # ------- IPC server for global hotkey -------
    ipc_server = QLocalServer()
    # If server name already exists from previous crash, remove it
    QLocalServer.removeServer("boomerang_ipc")
    if not ipc_server.listen("boomerang_ipc"):
        print("Failed to start IPC server", ipc_server.errorString())
    else:
        print("IPC server listening for commands")

    def _ipc_handle_new_connection():
        socket = ipc_server.nextPendingConnection()
        if socket is None:
            return
        socket.readyRead.connect(lambda s=socket: _ipc_read_socket(s))

    def _ipc_read_socket(sock):
        data = bytes(sock.readAll()).decode().strip()
        print(f"IPC received: {data}")
        if data == 'log':
            open_add_window()
        sock.disconnectFromServer()

    ipc_server.newConnection.connect(_ipc_handle_new_connection)

    bring_back_action.triggered.connect(open_process_window)
    log_new_action.triggered.connect(open_add_window)
    backup_now_action.triggered.connect(backup_now)
    options_action.triggered.connect(open_options)
    quit_action.triggered.connect(app.quit)

    # Start backup thread
    start_backup_thread(options)

    print("Boomerang app started")
    sys.exit(app.exec()) 