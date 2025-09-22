import os
import hashlib
import json
import time
from json import JSONDecodeError
import re
import threading
from visualizer import count_log_events, visualize_log_counts_horizontal

class DirectoryMonitor:
    def __init__(self, dir_path, log_file='log.txt'):
        if not os.path.isdir(dir_path):
            raise FileNotFoundError(f" The specified directory does not exist: {dir_path}")
        self.dir_path = dir_path
        self.log_file = log_file
        self.snapshot_file = os.path.join(dir_path, '.monitor_states.json')
        self.current_state = {'files': {}, 'directories': {}}
        self.previous_state = self.load_state()
        self.file_metadata = {}
        self.monitor_active = False

    def _calculate_hash(self, file_path):
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                while True:
                    text_body = f.read(4096)
                    if not text_body:
                        break
                    hasher.update(text_body)
            return hasher.hexdigest()
        except(IOError , PermissionError):
            self._log_event(f" can not access this file {os.path.basename(file_path)}")
            return  None

    def _get_current_state(self):
        state = {'files': {}, 'directories': {}}
        for root, dirs, files in os.walk(self.dir_path):
            for d in dirs:
                dir_path = os.path.join(root, d)
                try:
                    state['directories'][dir_path] = {
                    'modified': os.path.getmtime(dir_path),
                    'basename': os.path.basename(dir_path) }
                except FileNotFoundError:
                    continue
            for file in files:
                file_path = os.path.join(root, file)
                if file_path == self.snapshot_file or file_path == self.log_file:
                    continue
                file_hash = self._calculate_hash(file_path)
                if file_hash is not None:
                    try:
                        state['files'][file_path] = {
                            'hash': file_hash,
                            'size': os.path.getsize(file_path),
                            'basename': os.path.basename(file_path),
                            'modified_time': os.path.getmtime(file_path)
                        }
                    except FileNotFoundError:
                        continue
        return state

    def load_state(self):
        if os.path.exists(self.snapshot_file):
            try:
                with open(self.snapshot_file, 'r' , encoding='utf-8') as f:
                    return json.load(f)
            except JSONDecodeError:
                self._log_event(" cannot  load this file ")
        return {'files': {}, 'directories': {}}

    def save_state(self , state):
       try:
            with open(self.snapshot_file, 'w' , encoding='utf-8') as f:
                json.dump(state, f, indent=4)
       except IOError:
           self._log_event("cannot save his file")

    def _log_event(self, message):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_message + "\n")
        except IOError:
            print(f"[{timestamp}]  cannot write in log.txt file")

    def _find_renamed_items(self, old_file_data, new_files_state ,item_type):
        for new_path, new_data in new_files_state.items():
            if item_type == 'files':
                if (new_data['hash'] == old_file_data['hash'] and
                        new_data['size'] == old_file_data['size'] and
                        new_data['modified_time'] == old_file_data['modified_time'] and
                        new_path not in self.current_state['files']):
                        return new_path
            elif item_type == 'directories':
                if (new_data['modified'] == old_file_data['modified'] and
                        new_path not in self.current_state['directories']):
                        return new_path
        return None


    def monitor_changes(self):
        print("=" * 80)
        self._log_event(f"Monitoring: {self.dir_path}")
        print("=" * 80)
        current_state = self._get_current_state()

        old_files = self.previous_state.get('files', {})
        new_files = current_state.get('files', {})
        old_dirs = self.previous_state.get('directories', {})
        new_dirs = current_state.get('directories', {})

        renamed_files = {}
        for old_path, old_data in old_files.items():
            new_path = self._find_renamed_items(old_data, new_files ,'files' )
            if new_path and old_data['basename'] != os.path.basename(new_path):
                renamed_files[old_path] = new_path
                self._log_event(f"File RENAMED: {old_path} -> {new_path}")


        for file_path in set(old_files) - set(new_files) - set(renamed_files):
            self._log_event(f"File DELETED: {file_path}")

        for file_path, new_data in new_files.items():
            if file_path not in old_files and file_path not in renamed_files.values():
                self._log_event(f"File CREATED: {file_path} (Size: {new_data['size']} bytes)")
            elif file_path in old_files and old_files[file_path]['hash'] != new_data['hash']:
                self._log_event(f"File MODIFIED: {file_path}")


        renamed_directories = {}
        for old_path, old_data in old_dirs.items():
            new_path = self._find_renamed_items(old_data,new_dirs, 'directories')
            if new_path and old_data['basename'] != os.path.basename(new_path):
                renamed_directories[old_path] = new_path
                self._log_event(f"Directory RENAMED: {old_path} -> {new_path}")

        for old_path in old_dirs:
            if old_path not in new_dirs and old_path not in renamed_directories:
                self._log_event(f"Directory DELETED: {old_path}")

        for new_path in new_dirs:
            if new_path not in old_dirs and new_path not in renamed_directories.values():
                self._log_event(f"Directory CREATED: {new_path}")

        self.previous_state = current_state
        self.save_state(current_state)


    def start_monitoring(self, interval=5):
        if not os.path.isdir(self.dir_path):
            self._log_event(f"ERROR: Directory not found: {self.dir_path}")
            return

        self._log_event("first scan complete. Monitoring started...")
        self.monitor_active = True
        print("\n--- Starting monitoring (Press Ctrl+C to return to menu) ---")
        try:
            while self.monitor_active:
                self.monitor_changes(),
                time.sleep(interval)
        except KeyboardInterrupt:
            self._log_event("Monitoring stopped by user")
            self._log_event("Monitor stopped")
            self.monitor_active = False

    def stop_monitor(self):
        self.monitor_active = False
        self._log_event("Monitor stopped")

PATTERNS = {
    'created': [re.compile(r'File CREATED:.*'), re.compile(r'Directory CREATED:.*')],
    'deleted': (re.compile(r'File DELETED:.*'), re.compile(r'Directory DELETED:.*')),
    'renamed': (re.compile(r'File RENAMED:.*'), re.compile(r'Directory RENAMED:.*')),
    'modified': (re.compile(r'File MODIFIED:.*'), None)
}
def show_menu_items(pattern_f, pattern_d, name_f, log_file='log.txt'):

    while True:
        print("\n" + "=" * 80)
        print(f"=======[ View: {name_f.upper()} ]=======")
        print("=" * 80)
        print(f'[1] View {name_f} files')
        if pattern_d:
            print(f'[2] View {name_f} directories')
        print('[0] return to Main Menu')
        print("=" * 80)

        try:
            choice = input("Enter your choice: ")
            if choice == '1':
                display_logs(pattern_f, log_file)
            elif choice == '2' and pattern_d:
                display_logs(pattern_d, log_file)
            elif choice == '0':
                break
            else:
                print("invalid option, please try again.")
        except ValueError:
            print(" Please enter a valid number.")
        except Exception as e:
            print(f" unexpected error occurred: {e}")

def display_logs(pattern, log_file):
    print("\n====== Log Results ======")
    found = False
    try:
        with open(log_file, 'r', encoding='utf-8') as file:
            for line in file:
                if pattern.search(line):
                    print(line.strip())
                    found = True
    except FileNotFoundError:
        print("Log file not found.")
        input("\n============== Press Enter to continue ==================")
        return

    if not found:
        print("No matching log entries were found.")
    input("\n-- Press Enter to continue --")

def main_menu(monitor_instance):
    monitoring_thread = None
    while True:
        print('\n' + '===================================================================')
        print('==================      M A I N   M E N U      ==================')
        print('==================================================================')
        print('< [1] Start Monitoring >')
        print('< [-1] stop Monitoring')
        print('< [2] View Created Items >')
        print('< [3] View Deleted Items >')
        print('< [4] View Renamed Items >')
        print('< [5] View Modified Files >')
        print('< [6] Visualize Log Summary >')
        print('< [0] Exit >')
        print('===================================================================')


        try:
            choice = input("Enter your choice  ")

            if choice == '1':
                if monitoring_thread is None or not monitoring_thread.is_alive():
                    print("Starting monitoring in a separate thread...")
                    monitoring_thread = threading.Thread(target=monitor_instance.start_monitoring, args=(5,))
                    monitoring_thread.daemon = True
                    monitoring_thread.start()
                else:
                    print("Monitoring is already running.")
            elif choice == '-1':
                if monitoring_thread and monitoring_thread.is_alive():
                    monitor_instance.stop_monitor()
                    monitoring_thread.join(timeout=1)
                    if monitoring_thread.is_alive():
                        print("Monitoring thread did not stop gracefully. It might  still be running in background.")
                    else:
                        print("Monitoring stopped successfully.")
                else:
                    print("Monitoring is not active.")
            elif choice == '2':
                show_menu_items(PATTERNS['created'][0], PATTERNS['created'][1], "Created Items", monitor_instance.log_file)
            elif choice == '3':
                show_menu_items(PATTERNS['deleted'][0], PATTERNS['deleted'][1], "Deleted Items", monitor_instance.log_file)
            elif choice == '4':
                show_menu_items(PATTERNS['renamed'][0], PATTERNS['renamed'][1], "Renamed Items", monitor_instance.log_file)
            elif choice == '5':
                show_menu_items(PATTERNS['modified'][0], None, "Modified Files", monitor_instance.log_file)
            elif choice == '6':
                counts = count_log_events(monitor_instance.log_file)
                visualize_log_counts_horizontal(counts)
            elif choice == '0':
                print("Thank you for using the program!")
                if monitoring_thread and monitoring_thread.is_alive():
                    monitor_instance.stop_monitoring()
                    monitoring_thread.join(timeout=1)
                break
            else:
                print("invalid option, please try again.")
        except ValueError:
            print(" Please enter a valid number.")
        except Exception as e:
            print(f" unexpected error occurred: {e}")

print("=" * 80)
print("============== F I L E   M O N I T O R   T O O L ==============")
print("=" * 80)
def main():

    try:
        path_to_monitor = input("Enter directory path to monitor: ")
        monitor = DirectoryMonitor(path_to_monitor)
        main_menu(monitor)
    except FileNotFoundError as e:
        print(f"\n[FATAL ERROR]: {e}")
    except Exception as e:
        print(f" unexpected error occurred: {e}")
print("=" * 80)

main()