import os
import json

import datetime
import traceback
import shutil

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