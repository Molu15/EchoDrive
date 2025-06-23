import wave
from openal import oalOpen, Listener
import time
import threading

from shared_audio_state import active_sources, sources_lock

def get_wave_duration(wav_path):
    with wave.open(wav_path, 'rb') as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)

def setup_listener():
    listener = Listener()
    listener.set_position([0, 0, 0])
    listener.set_orientation([0, 0, -1, 0, 1, 0])
    return listener

def play_positional_tone_async(location, sound_file, gain=3.0, duration=3.0):
    def worker(control):
        src = oalOpen(sound_file)
        src.set_position([location.x, location.y, location.z])
        print(f"[Answer] Playing {sound_file} at location: {location}")
        src.set_gain(gain)
        control["src"] = src

        src.play()
        start = time.time()

        while time.time() - start < duration:
            if control.get("interrupted"):
                print(f"[Answer] Interrupted sound: {sound_file}")
                break
            time.sleep(0.05)

        try:
            src.stop()
            if hasattr(src, "delete"):
                src.delete()
        except Exception as e:
            print(f"[Answer] Error stopping sound: {e}")

        with sources_lock:
            if control in active_sources:
                active_sources.remove(control)

    # Create shared control object
    control = {"interrupted": False, "src": None}
    with sources_lock:
        active_sources.append(control)
    threading.Thread(target=worker, args=(control,), daemon=True).start()
