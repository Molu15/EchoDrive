import threading
from csv_logger import CSVLogger

class ScoreTracker:
    def __init__(self):
        print ("[Debug] Score init")
        #self.total_offset = 0.0
        self.num_echolocations = 0
        self.last_direction = "-"
        self.score = 0
        #self.last_accuracy = "-"  # Store the most recent accuracy category
        print("[Score] Tracker initialized")
        self.lock = threading.Lock()

        # Initiate logger
        self.logger = CSVLogger("scoreLog", [
            "num_ObjEcholocations", "score_total", "correct_direction"
        ])
        print ("[Debug] Score ready")

    def update(self, scored, direction):
        with self.lock:
            self.num_echolocations += 1
            self.logger.set_value("num_ObjEcholocations", self.num_echolocations)

            '''
            if offset in [998.0, 999.0]:  # Invalid offsets
                print("[Score] Skipping invalid/TOR offset")
                self.logger.set_value("accuracy", self.last_accuracy)
                self.logger.commit_row()
                return
            '''

            # Set direction arrow
            if direction == "front":
                self.last_direction = "\u2191"  # ↑
            elif direction == "back":
                self.last_direction = "\u2193"  # ↓
            elif direction == "left":
                self.last_direction = "\u2190"  # ←
            elif direction == "right":
                self.last_direction = "\u2192"  # →
            else:
                self.last_direction = "?"  # Unknown direction

            print(f"[Score] Correct direction {direction} and updated self.last_direction to {self.last_direction}")

            if scored:
                self.score += 5
            else:
                self.score -= 3

            self.score = max(0, self.score)  # Prevent negative score

            self.logger.set_value("score_total", self.score)
            self.logger.set_value("correct_direction", direction)
            #self.logger.set_value("accuracy", self.last_accuracy)
            self.logger.commit_row()

    def get_average_offset(self):
        with self.lock:
            if self.num_echolocations == 0:
                return 0.0
            return self.total_offset / self.num_echolocations

    def get_score(self):
        with self.lock:
            return self.score

    def get_direction(self):
        with self.lock:
            return self.last_direction

    def closeCSV(self):
        if hasattr(self, 'logger'):
            self.logger.close()
