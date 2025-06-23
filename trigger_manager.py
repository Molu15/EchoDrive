# trigger_manager.py

import keyboard
#print("keyboard.is_pressed('space') =", keyboard.is_pressed('space'))

class TriggerManager:
    def __init__(self, keys=('space', 'enter')):
        print ("[Debug] trigger init")
        self.keys = keys

        try:
            keyboard.is_pressed('shift')  # Dummy read to trigger hook setup
        except:
            print("[TriggerManager] Warning: keyboard hook failed to initialize")
        print ("[Debug] trigger ready")

    def check_trigger(self):
        """Returns the name of the key currently pressed, or None."""
        for key in self.keys:
            if keyboard.is_pressed(key):
                return key
        return None

    def is_pressed(self, key):
        """Returns True if the specified key is currently pressed."""
        #print (key)
        return keyboard.is_pressed(key)