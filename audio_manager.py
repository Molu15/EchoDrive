import pygame
import time
import get_answer
import os
from openal import oalInit, oalQuit
import carla
from carla import Vector3D
import threading
from shared_audio_state import active_sources, sources_lock

print ("[Debug] audio init")
# Initialize pygame mixer
if not pygame.mixer.get_init():
    pygame.mixer.init()
pygame.mixer.music.load("background_music.mp3")

# Volume constants
NORMAL_VOL = 0.4
DUCKED_VOL = 0.1
#FADE_STEPS = [0.4, 0.3, 0.2, 0.15, 0.1, 0.05, 0.0] #old fade steps
FADE_STEPS = [0.4, 0.4] #keep music the same volume without changing structure codes
FADE_INTERVAL = 4  # seconds between fade steps (J:extended it a bit from 2, it was too fast)
FADE_STEP_COUNT = len(FADE_STEPS)

# Sound files dictionary
BASE_PATH = os.path.join(os.path.dirname(__file__), "sounds")
SOUND_FILES = {
    "car": os.path.join(BASE_PATH, "car.wav"),
    "car-alert": os.path.join(BASE_PATH, "car-alert.wav"),
    "pedestrian": os.path.join(BASE_PATH, "pedestrian.wav"),
    "pedestrian-alert": os.path.join(BASE_PATH, "pedestrian-alert.wav"),
    "bicycle": os.path.join(BASE_PATH, "bicycle.wav"),
    "bicycle-alert": os.path.join(BASE_PATH, "bicycle-alert.wav"),
    "confirmation": os.path.join(BASE_PATH, "confirmation.wav"),
    "unknown": os.path.join(BASE_PATH, "unknown.wav"),
    "ignored": os.path.join(BASE_PATH, "ignored.wav"),
    "fail": os.path.join(BASE_PATH, "fail.wav"),
    "TOR": os.path.join(BASE_PATH, "TOR.wav")
}

# Initialize OpenAL
oalInit()
listener = get_answer.setup_listener()

# State flags and fade state
echolocating = False
fade_out_active = False
fade_index = 0
last_fade_time = 0


#TOR_sound = pygame.mixer.Sound(SOUND_FILES["TOR"])

print ("[Debug] audio ready")

def smooth_volume_change(target_volume, steps=10, delay=0.05):
    if not pygame.mixer.get_init():
        print("[AudioManager] Mixer not initialized, skipping volume change.")
        return

    current_volume = pygame.mixer.music.get_volume()
    diff = target_volume - current_volume
    for i in range(1, steps + 1):
        intermediate = current_volume + (diff * i / steps)
        pygame.mixer.music.set_volume(intermediate)
        time.sleep(delay)


def play_music():
    if pygame.mixer.get_init():
        smooth_volume_change(NORMAL_VOL)
        pygame.mixer.music.play(-1)
        start_fade_out()


def duck_music():
    global echolocating
    if pygame.mixer.get_init():
        echolocating = True
        smooth_volume_change(DUCKED_VOL)


def pause_music():
    global fade_out_active
    if pygame.mixer.get_init():
        fade_out_active = False
        #pygame.mixer.music.set_volume(0.0)
        pygame.mixer.music.pause()
        print("[AudioManager] Music paused.")
    else:
        print("[AudioManager] Mixer not initialized, skipping pause.")


def resume_music():
    global echolocating
    if pygame.mixer.get_init():
        echolocating = False
        smooth_volume_change(NORMAL_VOL)
        pygame.mixer.music.unpause()
        start_fade_out()


def notify_echolocation_started():
    global echolocating, fade_out_active
    echolocating = True
    fade_out_active = False  # stop fading immediately


def notify_echolocation_ended():
    global echolocating
    echolocating = False
    start_fade_out()


def start_fade_out():
    global fade_out_active, fade_index, last_fade_time
    if not fade_out_active:
        fade_out_active = True
        fade_index = 0
        last_fade_time = time.time()


def update_fade_out():
    """
    Call this regularly (e.g., once per frame or iteration).
    Gradually lowers music volume unless echolocating is True.
    """
    global fade_out_active, fade_index, last_fade_time

    if not fade_out_active or echolocating:
        return  # Do nothing if not fading or echolocating

    now = time.time()
    if now - last_fade_time >= FADE_INTERVAL:
        if fade_index < FADE_STEP_COUNT:
            target_vol = FADE_STEPS[fade_index]
            pygame.mixer.music.set_volume(target_vol)
            fade_index += 1
            last_fade_time = now
        else:
            fade_out_active = False  # finished fading


def play_entity_tone(location, tone_type, alarm=False):
    key = tone_type + "-alert" if alarm else tone_type
    if key not in SOUND_FILES:
        print(f"[AudioManager] Unknown tone_type: '{key}', using 'unknown.wav'")
        sound_file = SOUND_FILES.get("unknown", None)
        if not sound_file:
            print("[AudioManager] 'unknown' key missing, cannot fallback")
            return
    else:
        sound_file = SOUND_FILES[key]

    get_answer.play_positional_tone_async(location, sound_file)



def play_local_sound(tone_type, resume=True, duration=2.0):
    sound_file = SOUND_FILES.get(tone_type)
    if sound_file:
        get_answer.play_positional_tone_async(Vector3D(0, 0, 0), sound_file, duration=duration)
    else:
        print(f"[AudioManager] {tone_type} sound file missing.")
    if resume:
        resume_music()


def shutdown_audio():
    global fade_out_active
    fade_out_active = False
    if pygame.mixer.get_init():
        pygame.mixer.music.stop()
        pygame.mixer.quit()
    else:
        print("[AudioManager] Pygame mixer not initialized; skipping stop.")

    try:
        oalQuit()
    except Exception as e:
        print(f"[AudioManager] OpenAL cleanup failed: {e}")

def stop_all_positional_sounds():
    with sources_lock:
        for control in active_sources:
            control["interrupted"] = True
            try:
                if control["src"]:
                    control["src"].stop()
            except Exception:
                pass
        active_sources.clear()


def stop_all_audio():
    global echolocating
    stop_all_positional_sounds()
    if pygame.mixer.get_init():
        echolocating = False
        pygame.mixer.music.pause()
        print("[AudioManager] Background music paused.")
