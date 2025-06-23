import threading
import time
import pygame
from csv_logger import CSVLogger

class TakeoverManager:
    def __init__(self, trigger_delays, stop_event=None, trigger_manager=None):
        print ("[Debug] TOR init")
        self.takeover_requested = False
        self.takeover_time = None
        self.reaction_time = None
        self.sim_start_time = time.time()
        self.trigger_delays = trigger_delays
        self.tor_index = 0
        self.total_tors = len(trigger_delays)
        self.finished = False
        self.trigger = trigger_manager
        self.active = True
        self.stop_event = stop_event
        self.game = None
        self.thread = None
        self.reaction_logged = False
        self._takeover_timer=None # threading timer
        self.timed_out = False # if time for tor is timed out (5sec) or not

        self.logger = CSVLogger("TORLog", [
            "timestamp_initiation", "timestamp_reaction", "reaction_time", "successful_tor"
        ])
        print ("[Debug] TOR ready")

    def run(self):
        try:
            print("[TOR] Press ENTER or RETURN to respond.")
            while self.active and (self.stop_event is None or not self.stop_event.is_set()):
                if self.takeover_requested and self.trigger.is_pressed('enter') and not self.finished:
                    self.detect_reaction()
                    time.sleep(0.5)
        except KeyboardInterrupt:
            print("[TOR] Game interrupted by user.")
        finally:
            pygame.quit()
            print("[TOR] Pygame quit")

    def request_takeover(self):
        self.takeover_requested = True
        self.takeover_time = time.time()
        self.logger.set_value("timestamp_initiation", round(self.takeover_time, 4))

        # threading timer that triggers in 5 seconds
        timer = threading.Timer(5, self._handle_takeover_timeout)
        timer.daemon = True
        timer.start() #start timer (not very precise without taking exact self.takeover_time i know, but what can i do)
        self._takeover_timer = timer 

        print(f"[TOR] Takeover {self.tor_index + 1} requested! Press ENTER or RETURN to respond.")
        if self.game:
            print("[TOR] Notifying echolocation game of takeover.")
            threading.Thread(target=self.game.handle_takeover, daemon=True).start()

    def _handle_takeover_timeout(self):
        if self.takeover_requested:
            self.timed_out = True
            print("[TOR] Takeover timeout exceeded 5 seconds!")
            

    def detect_reaction(self):
        print("in detect")
        print(f"[TOR] self id: {id(self)}")
        if self.takeover_requested and self.reaction_time is None:
            print ("TOR detect 1")
            timestamp_reaction = time.time()
            print ("TOR detect 1,5")
            #cancel timer
            if self._takeover_timer and self._takeover_timer.is_alive():
                self._takeover_timer.cancel()
            print ("TOR detect 2")
            self.reaction_time = timestamp_reaction - self.takeover_time
            print ("TOR detect 3")
            self.logger.set_value("timestamp_reaction", round(timestamp_reaction, 4))
            print ("TOR detect 4")
            self.logger.set_value("reaction_time", self.reaction_time)
            print ("TOR detect 4,5")
            # Check if it was within 5 seconds 
            if not self.timed_out and self.reaction_time <= 5.0:
                self.logger.set_value("successful_tor", True)
                print ("TOR detect 5 success")
                print(f"[TOR] Reaction Time: {self.reaction_time:.2f} sec (success)")
            else:
                self.logger.set_value("successful_tor", False)
                print ("TOR detect 5 fail")
                print(f"[TOR] Reaction Time: {self.reaction_time:.2f} sec (too late)")
            print ("TOR detect 6")
            self.logger.commit_row()
            print ("TOR detect 7")
            self.reaction_logged = True   
        else:
            print(f"[TOR] {self.tor_index + 1} was triggered but no reaction recorded.")
            #log log log
            self.logger.set_value("timestamp_reaction", "no reaction recorded")
            self.logger.set_value("successful_tor", False)
            self.logger.commit_row()
            self.reaction_logged = True

    def reset_for_next_tor(self):
        # Cancel threading timer
        if self._takeover_timer and self._takeover_timer.is_alive():
            self._takeover_timer.cancel()
        self._takeover_timer = None 
        self.timed_out = False

        self.takeover_requested = False
        self.reaction_time = None
        self.takeover_time = None
        self.tor_index += 1
        self.reaction_logged = False
        if self.tor_index >= self.total_tors - 1:
            self.finished = True
            print("[TOR] All Takeover Requests completed.")

    def tick(self):
        elapsed_time = time.time() - self.sim_start_time

        if (self.tor_index < self.total_tors and
            not self.takeover_requested and
            elapsed_time >= self.trigger_delays[self.tor_index]):
            self.request_takeover()

        if self.takeover_requested and self.reaction_time is not None and self.reaction_logged:
            self.reset_for_next_tor()

    def is_active(self):
        return self.takeover_requested and self.reaction_time is None

    def shutdown(self):
        self.active = False
        self.finished = True
        print("[TOR] shutting down")

        if self.stop_event:
            self.stop_event.set()

        try:
            if hasattr(self.logger, "commit_row"):
                self.logger.commit_row()
            if hasattr(self.logger, "close"):
                self.logger.close()
        except Exception as e:
            print(f"[TOR] Logger cleanup failed: {e}")

        if self.thread:
            print("[TOR] Waiting for takeover thread to finish...")
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                print("[TOR] Warning: takeover thread did not shut down cleanly.")
            else:
                print("[TOR] Takeover thread finished.")

    def set_game(self, game):
        self.game = game 
        print("[TOR] Game set")
