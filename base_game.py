import pygame
import time
import os
import threading

class BaseManager:
    def __init__(self, takeover_manager, stop_event, game_ready_event):
        print ("[Debug] base init")
        if not pygame.mixer.get_init():
            print ("[Debug] base 1")
            pygame.mixer.init()
            
        print ("[Debug] base 2")

        base_dir = os.path.dirname(os.path.abspath(__file__))  # root folder of the script
        print ("[Debug] base 3")
        self.background_music = os.path.join(base_dir, "background_music.mp3")
        print ("[Debug] base 4")
        self.tor_sound_file = os.path.join(base_dir, "sounds", "TOR.wav") 
        print ("[Debug] base 5") 
        self.tor_sound = pygame.mixer.Sound(self.tor_sound_file)
        print ("[Debug] base 6")


        self.music_playing = False
        print ("[Debug] base 7")
        self.takeover_manager = takeover_manager
        print ("[Debug] base 8")
        self.stop_event = stop_event
        print ("[Debug] base 9")
        self._takeover_lock = threading.Lock()
        print ("[Debug] base 10")
        self.active = True  # Helps exit takeover early if shutting down

        if game_ready_event:
            print ("[Debug] base 11")
            game_ready_event.set()
        print ("[Debug] base 12")
        self.play_music()

        print ("[Debug] base ready")

    def play_music(self):
        print ("[Debug] base play music 1")
        #if not self.music_playing:
        print ("[Debug] base play music 2")
        pygame.mixer.music.load(self.background_music)
        print ("[Debug] base play music 3")
        pygame.mixer.music.set_volume(0.5)
        print ("[Debug] base play music 4")
        pygame.mixer.music.play(-1)  # loop music
        print ("[Debug] base play music 5")
        self.music_playing = True
        print("[BaseManager] Background music started.")

    def pause_music(self):
        if self.music_playing:
            pygame.mixer.music.pause()
            print("[BaseManager] Background music paused.")

    def resume_music(self):
        if self.music_playing:
            pygame.mixer.music.unpause()
            print("[BaseManager] Background music resumed.")

    def run(self):
        self.play_music()
        try:
            while not self.stop_event.is_set():
                if self.takeover_manager.is_active():
                    self.handle_takeover()
                time.sleep(0.01)
        except KeyboardInterrupt:
            print("[BaseManager] Run loop stopped by user.")
        finally:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            self.shutdown()
            print("[BaseManager] Cleaned up audio.")

    def shutdown(self):
        print("[BaseManager] Shutting down...")
        self.active = False
        self.stop_event.set()
        pygame.mixer.music.stop()
        pygame.mixer.quit()

    def handle_takeover(self):
        if not self._takeover_lock.acquire(blocking=False):
            print("[BaseManager] Takeover already in progress, skipping.")
            return

        try:
            print("[BaseManager] Takeover detected.")
            self.pause_music()

            if self.takeover_manager.is_active() and not self.takeover_manager.finished:
                self.tor_channel = pygame.mixer.find_channel()
                if self.tor_channel:
                    self.tor_channel.play(self.tor_sound)

            while self.takeover_manager.is_active() and self.active:
                time.sleep(0.1)

            # Stop TOR sound if it's still playing
            if self.tor_channel and self.tor_channel.get_busy():
                self.tor_channel.stop()

            print("[BaseManager] Takeover ended. Resuming music.")
            self.resume_music()

        finally:
            print("[BaseManager] Releasing takeover lock.")
            self._takeover_lock.release()