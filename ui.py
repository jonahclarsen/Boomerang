import datetime

from PySide6.QtWidgets import (QMainWindow, QTextEdit, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLabel, QDialog, QFileDialog, QMessageBox, QSpinBox)
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt, QEvent
import platform
from idea_manager import load_idea, save_idea, delete_idea, postpone_idea, create_new_idea, list_due_ideas


if platform.system() == 'Darwin':
    try:
        from AppKit import NSApp, NSApplicationActivationPolicyRegular, NSApplicationActivationPolicyAccessory
    except ImportError:
        NSApp = None

def _show_in_dock():
    if NSApp:
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyRegular)

def _hide_from_dock():
    if NSApp:
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

class PostponeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Postpone Idea")
        self.setModal(True)
        self.days_str = ''
        layout = QVBoxLayout()
        self.label = QLabel("Enter number of days:")
        self.days_label = QLabel(self.days_str)
        self.date_label = QLabel("")
        self.info_label = QLabel("Press Enter to confirm")
        layout.addWidget(self.label)
        layout.addWidget(self.days_label)
        layout.addWidget(self.date_label)
        layout.addWidget(self.info_label)
        self.setLayout(layout)

    def keyPressEvent(self, event):
        key = event.key()
        if key >= Qt.Key_0 and key <= Qt.Key_9:
            self.days_str += chr(key)
        elif key in (Qt.Key_Backspace, Qt.Key_Delete):
            if self.days_str:
                self.days_str = self.days_str[:-1]
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            try:
                days = int(self.days_str) if self.days_str else 0
                self.accept()
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Please enter a valid number.")
        self.update_labels()
        super().keyPressEvent(event)

    def update_labels(self):
        self.days_label.setText(self.days_str or '0')
        try:
            days = int(self.days_str or '0')
            future_date = datetime.date.today() + datetime.timedelta(days=days)
            self.date_label.setText(future_date.strftime('%A, %B %d, %Y'))
        except ValueError:
            self.date_label.setText("")

class ProcessWindow(QMainWindow):
    def __init__(self, ideas_folder, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Process Ideas")
        # Make window stay on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.ideas_folder = ideas_folder
        self.due_ideas = list_due_ideas(ideas_folder)  # From idea_manager
        self.current_index = 0
        self.is_editing = False

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout()

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        button_layout = QHBoxLayout()
        self.edit_btn = QPushButton("Edit (E)")
        self.delete_btn = QPushButton("Delete (D)")
        self.postpone_btn = QPushButton("Postpone (P)")
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.postpone_btn)
        layout.addLayout(button_layout)

        # Postpone inline widgets (hidden by default)
        self.postpone_mode = False
        self.days_str = ''
        self.days_label = QLabel("Days: ")
        self.date_label_inline = QLabel("")
        self.info_label_inline = QLabel("Enter to confirm • Esc to cancel")
        self.inline_layout = QHBoxLayout()
        self.inline_layout.addWidget(self.days_label)
        self.inline_layout.addWidget(self.date_label_inline)
        layout.addLayout(self.inline_layout)
        layout.addWidget(self.info_label_inline)
        self.days_label.setVisible(False)
        self.date_label_inline.setVisible(False)
        self.info_label_inline.setVisible(False)

        self.central_widget.setLayout(layout)

        self.edit_btn.clicked.connect(self.toggle_edit)
        self.delete_btn.clicked.connect(self.handle_delete)
        self.postpone_btn.clicked.connect(self.handle_postpone)

        QShortcut(QKeySequence('E'), self, self.toggle_edit)
        QShortcut(QKeySequence('D'), self, self.handle_delete)
        QShortcut(QKeySequence('P'), self, self.handle_postpone)

        self.load_current_idea()

    def keyPressEvent(self, event):
        if self.postpone_mode:
            key = event.key()
            if Qt.Key_0 <= key <= Qt.Key_9:
                self.days_str += chr(key)
                self.update_inline_labels()
            elif key in (Qt.Key_Backspace, Qt.Key_Delete):
                if self.days_str:
                    self.days_str = self.days_str[:-1]
                    self.update_inline_labels()
            elif key in (Qt.Key_Return, Qt.Key_Enter):
                self.handle_postpone()
            elif key == Qt.Key_Escape:
                self.exit_postpone_mode()
            return

        if self.is_editing and event.key() == Qt.Key_Return:
            if event.modifiers() & Qt.ShiftModifier:
                self.text_edit.insertPlainText('\n')
            else:
                self.toggle_edit()
        elif event.key() == Qt.Key_Escape:
            # Always allow Escape to close the window
            self.close()
        else:
            super().keyPressEvent(event)

    def toggle_edit(self):
        if self.current_index >= len(self.due_ideas):
            return
        if self.is_editing:
            text = self.text_edit.toPlainText()
            save_idea(self.due_ideas[self.current_index], text)
            self.text_edit.setReadOnly(True)
            self.is_editing = False
            self.edit_btn.setText("Edit (E)")
        else:
            self.text_edit.setReadOnly(False)
            self.text_edit.setFocus()
            self.is_editing = True
            self.edit_btn.setText("Save (Enter)")

    def handle_delete(self):
        if self.current_index >= len(self.due_ideas):
            return
        delete_idea(self.due_ideas[self.current_index], self.ideas_folder)
        self.move_to_next()

    def handle_postpone(self):
        if self.current_index >= len(self.due_ideas):
            return
        if not self.postpone_mode:
            # enter postpone mode
            self.postpone_mode = True
            self.days_str = ''
            self.days_label.setVisible(True)
            self.date_label_inline.setVisible(True)
            self.info_label_inline.setVisible(True)
            self.update_inline_labels()
            self.setFocus()
        else:
            # confirm postpone
            days = int(self.days_str or '0')
            postpone_idea(self.due_ideas[self.current_index], days, self.ideas_folder)
            self.exit_postpone_mode()
            self.move_to_next()

    def update_inline_labels(self):
        self.days_label.setText(f"Days: {self.days_str or '0'}")
        try:
            days = int(self.days_str or '0')
            future_date = datetime.date.today() + datetime.timedelta(days=days)
            self.date_label_inline.setText(future_date.strftime('%A, %B %d, %Y'))
        except ValueError:
            self.date_label_inline.setText("")

    def exit_postpone_mode(self):
        self.postpone_mode = False
        self.days_label.setVisible(False)
        self.date_label_inline.setVisible(False)
        self.info_label_inline.setVisible(False)

    def move_to_next(self):
        self.current_index += 1
        self.load_current_idea()

    def showEvent(self, event):
        super().showEvent(event)
        try:
            _show_in_dock()
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            _hide_from_dock()
        except Exception:
            pass
        super().closeEvent(event)

    def load_current_idea(self):
        if self.current_index >= len(self.due_ideas):
            self.text_edit.setText("No more ideas to process today.")
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.postpone_btn.setEnabled(False)
            return
        self.exit_postpone_mode()
        text = load_idea(self.due_ideas[self.current_index])
        self.text_edit.setText(text)
        self.text_edit.setReadOnly(True)
        self.is_editing = False
        self.edit_btn.setText("Edit (E)")
        self.edit_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.postpone_btn.setEnabled(True)

    def showEvent(self, event):
        super().showEvent(event)
        _show_in_dock()

    def closeEvent(self, event):
        _hide_from_dock()
        super().closeEvent(event)

class AddIdeaWindow(QMainWindow):
    def __init__(self, ideas_folder, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log New Idea")
        # Make window stay on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.ideas_folder = ideas_folder
        self.days_str = ''
        self.state = 'edit'  # 'edit' or 'days'
        self.temp_text = ''

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout()

        self.text_edit = QTextEdit()
        self.text_edit.installEventFilter(self)
        self.layout.addWidget(self.text_edit)

        self.days_label = QLabel("Days from now: " + self.days_str)
        self.date_label = QLabel("")

        # Buttons
        self.button_layout = QHBoxLayout()
        self.edit_btn = QPushButton("Edit (E)")
        self.postpone_btn = QPushButton("Postpone (P)")
        self.cancel_btn = QPushButton("Cancel (Esc)")
        self.button_layout.addWidget(self.edit_btn)
        self.button_layout.addWidget(self.postpone_btn)
        self.button_layout.addWidget(self.cancel_btn)

        self.layout.addWidget(self.days_label)
        self.layout.addWidget(self.date_label)
        self.layout.addLayout(self.button_layout)

        central_widget.setLayout(self.layout)

        # Connect buttons
        self.edit_btn.clicked.connect(self.back_to_edit)
        self.postpone_btn.clicked.connect(self.postpone_clicked)
        self.cancel_btn.clicked.connect(self.close)
        self.update_ui()

        print("AddIdeaWindow initialized")
        _show_in_dock()

    def showEvent(self, event):
        super().showEvent(event)
        _show_in_dock()

    def closeEvent(self, event):
        _hide_from_dock()
        super().closeEvent(event)

    def update_ui(self):
        if self.state == 'edit':
            self.text_edit.setVisible(True)
            self.text_edit.setReadOnly(False)
            self.text_edit.setFocus()
            self.days_label.setVisible(False)
            self.date_label.setVisible(False)
            self.edit_btn.setVisible(False)
            self.postpone_btn.setVisible(True)
            self.cancel_btn.setVisible(True)
        elif self.state == 'days':
            self.text_edit.setVisible(True)
            self.text_edit.setReadOnly(True)
            self.days_label.setVisible(True)
            self.date_label.setVisible(True)
            self.edit_btn.setVisible(True)
            self.postpone_btn.setVisible(True)
            self.cancel_btn.setVisible(True)
            self.setFocus()  # Focus on window for key events

    def keyPressEvent(self, event):
        if self.state == 'days':
            key = event.key()
            if key >= Qt.Key_0 and key <= Qt.Key_9:
                self.days_str += chr(key)
            elif key in (Qt.Key_Backspace, Qt.Key_Delete):
                if self.days_str:
                    self.days_str = self.days_str[:-1]
            elif key == Qt.Key_Return or key == Qt.Key_Enter:
                self.handle_save()
            elif key == Qt.Key_E:
                self.back_to_edit()
            elif key == Qt.Key_P:
                self.postpone_clicked()
            elif key == Qt.Key_Escape:
                self.close()
            self.update_labels()

    def eventFilter(self, obj, event):
        if obj is self.text_edit and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
                self.finish_edit()
                return True

            if event.key() == Qt.Key_Escape:
                self.close()
                return True
        return super().eventFilter(obj, event)

    def back_to_edit(self):
        self.state = 'edit'
        self.update_ui()

    def postpone_clicked(self):
        if self.state == 'edit':
            self.finish_edit()
        else:
            self.handle_save()

    def finish_edit(self):
        self.temp_text = self.text_edit.toPlainText()
        if not self.temp_text:
            QMessageBox.warning(self, "Empty Idea", "Please enter some text.")
            return
        self.state = 'days'
        self.days_str = ''
        self.update_ui()
        self.update_labels()

    def update_labels(self):
        self.days_label.setText("Days from now: " + (self.days_str or '0'))
        try:
            days = int(self.days_str or '0')
            future_date = datetime.date.today() + datetime.timedelta(days=days)
            self.date_label.setText(future_date.strftime('%A, %B %d, %Y'))
        except ValueError:
            self.date_label.setText("")

    def handle_save(self):
        text = self.temp_text
        try:
            days = int(self.days_str or '0')
        except ValueError:
            QMessageBox.warning(self, "Invalid Days", "Please enter a valid number of days.")
            return
        create_new_idea(self.ideas_folder, text, days)
        self.close()

class OptionsWindow(QDialog):
    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Options")
        self.options = options
        self.selected_folder = None
        self.selected_backup_folder = None
        
        layout = QVBoxLayout()
        
        # Ideas folder
        current_folder = options.get('ideas_folder', 'Not set')
        self.folder_label = QLabel(f"Ideas Folder: {current_folder}")
        browse_btn = QPushButton("Browse Ideas Folder")
        browse_btn.clicked.connect(self.browse_folder)
        layout.addWidget(self.folder_label)
        layout.addWidget(browse_btn)
        
        # Backup settings
        layout.addWidget(QLabel(""))  # Spacer
        layout.addWidget(QLabel("Backup Settings:"))
        
        # Backup folder
        current_backup = options.get('backup_folder', 'Not set')
        self.backup_label = QLabel(f"Backup Folder: {current_backup}")
        backup_browse_btn = QPushButton("Browse Backup Folder")
        backup_browse_btn.clicked.connect(self.browse_backup_folder)
        layout.addWidget(self.backup_label)
        layout.addWidget(backup_browse_btn)
        
        # Backup interval
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Backup every:"))
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setMinimum(1)
        self.interval_spinbox.setMaximum(365)
        self.interval_spinbox.setValue(options.get('backup_interval_days', 7))
        self.interval_spinbox.setSuffix(" days")
        interval_layout.addWidget(self.interval_spinbox)
        layout.addLayout(interval_layout)
        
        # Save/Cancel buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.save_options)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Ideas Folder")
        if folder:
            self.selected_folder = folder
            self.folder_label.setText(f"Ideas Folder: {folder}")

    def browse_backup_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Backup Folder")
        if folder:
            self.selected_backup_folder = folder
            self.backup_label.setText(f"Backup Folder: {folder}")

    def save_options(self):
        # Update options dict
        if self.selected_folder:
            self.options['ideas_folder'] = self.selected_folder
        if self.selected_backup_folder:
            self.options['backup_folder'] = self.selected_backup_folder
        self.options['backup_interval_days'] = self.interval_spinbox.value()
        self.accept() 