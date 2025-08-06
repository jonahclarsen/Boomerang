import os
import json

import datetime
import traceback
import shutil
import threading
import time

from PySide6.QtWidgets import QMessageBox

def get_options_path():
    return os.path.expanduser('~/.boomerang_options.json')

def load_options():
    path = get_options_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            options = json.load(f)
        print(f"Loaded options: {options}")
        return options
    except Exception as e:
        print(f"Error loading options: {e}\n{traceback.format_exc()}")
        QMessageBox.critical(None, "Error", f"Failed to load options: {e}\n{traceback.format_exc()}")
        return {}

def save_options(options):
    path = get_options_path()
    try:
        with open(path, 'w') as f:
            json.dump(options, f, indent=4)
        print(f"Saved options: {options}")
    except Exception as e:
        print(f"Error saving options: {e}\n{traceback.format_exc()}")
        QMessageBox.critical(None, "Error", f"Failed to save options: {e}\n{traceback.format_exc()}")

def get_ideas_folder(options):
    return options.get('ideas_folder')

def set_ideas_folder(options, folder):
    options['ideas_folder'] = folder
    save_options(options)

def list_due_ideas(ideas_folder):
    if not ideas_folder or not os.path.exists(ideas_folder):
        return []
    files = [f for f in os.listdir(ideas_folder) if f.endswith('.txt')]
    files.sort()  # Alphabetical = chronological
    due = []
    today = datetime.date.today()
    for f in files:
        try:
            date_str = f[:8]
            file_date = datetime.datetime.strptime(date_str, '%Y%m%d').date()
            if file_date <= today:
                due.append(os.path.join(ideas_folder, f))
        except ValueError:
            print(f"Invalid filename format: {f}")
    print(f"Found {len(due)} due ideas")
    return due

def load_idea(file_path):
    try:
        with open(file_path, 'r') as f:
            text = f.read()
        print(f"Loaded idea from {file_path}: {text[:50]}...")
        return text
    except Exception as e:
        print(f"Error loading idea {file_path}: {e}\n{traceback.format_exc()}")
        QMessageBox.critical(None, "Error", f"Failed to load idea: {e}\n{traceback.format_exc()}")
        return ''

def save_idea(file_path, text):
    try:
        with open(file_path, 'w') as f:
            f.write(text)
        print(f"Saved idea to {file_path}")
    except Exception as e:
        print(f"Error saving idea {file_path}: {e}\n{traceback.format_exc()}")
        QMessageBox.critical(None, "Error", f"Failed to save idea: {e}\n{traceback.format_exc()}")

def _generate_unique_filename(date_obj, ideas_folder):
    base = date_obj.strftime('%Y%m%d')
    filename = f"{base}.txt"
    idx = 1
    while os.path.exists(os.path.join(ideas_folder, filename)):
        idx += 1
        filename = f"{base}_{idx}.txt"
    return filename


def delete_idea(file_path, ideas_folder):
    deleted_dir = os.path.join(ideas_folder, 'deleted_ideas')
    os.makedirs(deleted_dir, exist_ok=True)
    try:
        shutil.move(file_path, os.path.join(deleted_dir, os.path.basename(file_path)))
        print(f"Moved {file_path} to deleted_ideas")
    except Exception as e:
        print(f"Error deleting idea {file_path}: {e}\n{traceback.format_exc()}")
        QMessageBox.critical(None, "Error", f"Failed to delete idea: {e}\n{traceback.format_exc()}")

def postpone_idea(file_path, days, ideas_folder):
    try:
        new_date = datetime.date.today() + datetime.timedelta(days=days)
        new_filename = _generate_unique_filename(new_date, ideas_folder)
        new_path = os.path.join(ideas_folder, new_filename)
        os.rename(file_path, new_path)
        print(f"Postponed {file_path} to {new_path}")
    except Exception as e:
        print(f"Error postponing idea {file_path}: {e}\n{traceback.format_exc()}")
        QMessageBox.critical(None, "Error", f"Failed to postpone idea: {e}\n{traceback.format_exc()}")

def create_new_idea(ideas_folder, text, days):
    try:
        target_date = datetime.date.today() + datetime.timedelta(days=days)
        filename = _generate_unique_filename(target_date, ideas_folder)
        file_path = os.path.join(ideas_folder, filename)
        save_idea(file_path, text)
        print(f"Created new idea {file_path}")
        return file_path
    except Exception as e:
        print(f"Error creating new idea: {e}\n{traceback.format_exc()}")
        QMessageBox.critical(None, "Error", f"Failed to create new idea: {e}\n{traceback.format_exc()}")
        return None

# Backup functionality
def should_backup(options):
    """Check if backup is due based on last backup time and interval"""
    backup_folder = options.get('backup_folder')
    if not backup_folder:
        return False
        
    interval_days = options.get('backup_interval_days', 7)
    last_backup = options.get('last_backup_time', 0)
    
    # Check if 12+ hours have passed since last backup check
    current_time = time.time()
    if current_time - last_backup < 12 * 3600:  # 12 hours in seconds
        return False
        
    # Check if backup is due based on interval
    last_backup_date = options.get('last_backup_date')
    if not last_backup_date:
        return True
        
    try:
        last_date = datetime.datetime.strptime(last_backup_date, '%Y%m%d').date()
        days_since = (datetime.date.today() - last_date).days
        return days_since >= interval_days
    except ValueError:
        return True

def perform_backup(options, show_prompts=True):
    """Perform backup if conditions are met"""
    backup_folder = options.get('backup_folder')
    ideas_folder = options.get('ideas_folder')
    
    if not backup_folder or not ideas_folder:
        print("Backup skipped: backup_folder or ideas_folder not set")
        return False
        
    # Check if backup folder exists
    if not os.path.exists(backup_folder):
        if show_prompts:
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                None, 
                "Create Backup Folder?", 
                f"Backup folder '{backup_folder}' does not exist. Create it?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return False
        try:
            os.makedirs(backup_folder, exist_ok=True)
            print(f"Created backup folder: {backup_folder}")
        except Exception as e:
            print(f"Failed to create backup folder: {e}")
            if show_prompts:
                QMessageBox.critical(None, "Backup Error", f"Failed to create backup folder: {e}")
            return False
    
    # Create today's backup folder
    today_str = datetime.date.today().strftime('%Y%m%d')
    today_backup = os.path.join(backup_folder, today_str)
    
    if os.path.exists(today_backup):
        print(f"Backup already exists for today: {today_backup}")
        return False
        
    try:
        # Copy ideas folder to backup
        shutil.copytree(ideas_folder, today_backup)
        print(f"Backup completed: {today_backup}")
        
        # Update last backup info
        options['last_backup_date'] = today_str
        options['last_backup_time'] = time.time()
        save_options(options)
        
        return True
    except Exception as e:
        print(f"Backup failed: {e}")
        if show_prompts:
            QMessageBox.critical(None, "Backup Error", f"Backup failed: {e}")
        return False

def start_backup_thread(options):
    """Start background thread to check for backups every 12 hours"""
    def backup_worker():
        while True:
            time.sleep(12 * 3600)  # Wait 12 hours
            try:
                current_options = load_options()
                if should_backup(current_options):
                    perform_backup(current_options, show_prompts=True)
            except Exception as e:
                print(f"Backup thread error: {e}")
    
    backup_thread = threading.Thread(target=backup_worker, daemon=True)
    backup_thread.start()
    print("Backup thread started") 