import os
import csv
import atexit
from datetime import datetime
#much leaner and more performant in txt csv-format than Excel Logger with pandas and xml in memory structure

# GLOBAL EXPERIMENT CONTEXT 
_experiment_id = "default"
_scenario_type = "default"
_experiment_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")#remove - if it gets mixed up

def set_experiment_context(expid,scentyp):
    """
    Sets the global experiment ID and timestamp for all CSVLogger instances.
    Should be called once at the beginning of the program (e.g., from start_carla.py).
    """
    global _experiment_id, _scenario_type, _experiment_timestamp
    _experiment_id = expid.strip() or "default"
    _scenario_type = scentyp.strip() or "default"
    _experiment_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") #remove - if it gets mixed up


class CSVLogger:
    def __init__(self, log_name, fieldnames):
        """
        Initializes a new logger. The CSV will be named using:
        experiment-id + log-name + global timestamp
        and saved to the user's Desktop.
        """
        self.fieldnames = fieldnames
        self.row_buffer = {}
        self._closed = False

        filename = f"{_experiment_id}_{_scenario_type}_{log_name}_{_experiment_timestamp}.csv"

        #-------WHERE TO WRITE TO---
        # desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        # self.file_path = os.path.join(desktop_path, filename)
        # Get root project directory dynamically
        project_root = os.path.abspath(os.path.dirname(__file__))  # This points to the folder containing csv_logger.py
        log_folder = os.path.join(project_root, "CSVLogs")  
        os.makedirs(log_folder, exist_ok=True)
        self.file_path = os.path.join(log_folder, filename)

        self.file = open(self.file_path, mode='w', newline='', encoding='utf-8')
        self.writer = csv.DictWriter(self.file, fieldnames=fieldnames, delimiter=';')
        self.writer.writeheader()

        atexit.register(self._safe_close)# backup automatic close 

        print(f"[CSVLogger] Logging {log_name} to: {self.file_path}")

    def set_value(self, key, value):
        """
        Sets an individual column value in the current row buffer.
        """
        if key not in self.fieldnames:
            raise ValueError(f"'{key}' is not a valid column name. Allowed: {self.fieldnames}")
        self.row_buffer[key] = value

    def commit_row(self):
        """
        Writes the current row to the CSV, filling in missing columns with empty strings,
        then resets the row buffer.
        """
        complete_row = {k: self.row_buffer.get(k, "") for k in self.fieldnames}
        self.writer.writerow(complete_row)
        self.file.flush()
        self.row_buffer = {}

    def add_entry(self, data_dict):
        """
        Alternative: Writes a full row at once using a dictionary. Missing columns will be empty.
        """
        for key in data_dict:
            if key not in self.fieldnames:
                raise ValueError(f"'{key}' is not a valid column name.")
        complete_row = {k: data_dict.get(k, "") for k in self.fieldnames}
        self.writer.writerow(complete_row)
        self.file.flush()

    def close(self):
        """
        Finalizes the logger and closes the file. Always call this at the end of use.
        """
        if not self._closed:
            self.file.close()
            self._closed = True
            print(f"[CSVLogger] File saved to: {self.file_path}")
            print("[Debug] csv self closed")

    def _safe_close(self):
        """
        Automatically called by atexit to ensure file is closed even if .close() was not explicitly called.
        """
        if not self._closed:
            self.file.close()
            print(f"[CSVLogger] File (auto) saved to: {self.file_path}")
            print("[Debug] csv self closed automatic")
