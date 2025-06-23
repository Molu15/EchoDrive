# shared_audio_state.py
import threading

print ("[Debug] shared audio init")
# Shared list to track currently active audio sources
active_sources = []

# Lock to protect access to active_sources across threads
sources_lock = threading.Lock()

print ("[Debug] shared audio ready")
