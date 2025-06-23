# echolocation_game.py

import time
import math
import carla
from carla import Vehicle
import threading
from csv_logger import CSVLogger


class EcholocationGame:
    def __init__(self, carla_world, ego_vehicle: Vehicle, rss_manager, audio_manager, gesture_manager, score_tracker, takeover_manager, trigger_manager):
        print ("[Debug] echo init")
        print ("[Debug] echo 1")
        self.world = carla_world
        print ("[Debug] echo 2")
        self.ego = ego_vehicle
        print ("[Debug] echo 3")
        self.rss = rss_manager
        print ("[Debug] echo 4")
        self.audio = audio_manager
        print ("[Debug] echo 5")
        self.gesture = gesture_manager
        print ("[Debug] echo 6")
        self.score_tracker = score_tracker
        print ("[Debug] echo 7")
        self.takeover_manager = takeover_manager
        print ("[Debug] echo 8")
        self.trigger = trigger_manager
        print ("[Debug] echo 9")
        self.active = True
        print ("[Debug] echo 10")
        self._takeover_lock = threading.Lock()

        print ("[Debug] echo init logger")

        #Initiate logger
        self.logger = CSVLogger("echoLog", [ # initate CSV logger with those Columns
            "timestamp_inputTap", "result_echowave", "gesturedetect_1round", "gesturedetect_2round"
        ])

        print ("[Debug] echo ready")

    def run(self, stop_event=None):
        print("[Game] Started. Press SPACEBAR to ping.")
        while self.active and (stop_event is None or not stop_event.is_set()):
            if self.takeover_manager.is_active():
                continue
            else:
                time.sleep(0.01)
                if 'space' not in self.trigger.keys:
                    print("[Game] WARNING: 'space' trigger not registered properly.")
                if self.trigger.is_pressed('space'):
                    self.logger.set_value("timestamp_inputTap", round(time.time(), 4))
                    self.handle_echolocation_event()

            self.audio.update_fade_out()
            time.sleep(0.05)  # Reduce CPU usage


    def handle_takeover(self):
        if not self._takeover_lock.acquire(blocking=False):
            print("[Game] Takeover already in progress, skipping.")
            return

        try:
            print("[Game] Takeover active pausing echolocation game")
            self.audio.stop_all_audio()
            if self.takeover_manager.is_active() and not self.takeover_manager.finished:
                self.audio.play_local_sound("TOR", resume=False, duration=4.0)
            self.gesture.enable_gesture_process(False)

            while self.takeover_manager.is_active() and self.active:
                time.sleep(0.1)
            print("[Game] Takeover ended resuming game.")
            if not self.active:
                print("[Game] Skipping resume: game already shut down.")
                return
            self.audio.stop_all_audio()
            self.audio.resume_music()
            self.gesture.enable_gesture_process(True)


        finally:
            self._takeover_lock.release()

    def handle_echolocation_event(self):
        self.audio.notify_echolocation_started()
        '''
        ego_tf = self.ego.get_transform()
        self.world.debug.draw_arrow(
            ego_tf.location,
            ego_tf.location + ego_tf.get_forward_vector() * 10.0,  # 5 meters forward
            thickness=0.1,
            color=carla.Color(255, 0, 0),  # red arrow
            life_time=2  # lasts 0.1 seconds (refresh frequently)
        )
        '''

        try:
            if self.takeover_manager.is_active():
                print("[Game] Aborting Echolocation Handling.")
                #log log log
                self.logger.set_value("result_echowave", "TOR aborted")
                self.logger.commit_row()
                return
            entity = self.rss.get_nearest_entity(self.ego)
            if not entity:
                print("[Game] No entity found.")
                self.audio.play_local_sound("unknown")
                #log log log
                self.logger.set_value("result_echowave", "no entity found")
                self.logger.commit_row() 
                return

            rel_location, obj_type, direction = self.get_relative_location_and_type(entity)
            print (rel_location)

            if rel_location.length() > 15.0:
                print(f"Entity '{obj_type}' is too far: {rel_location.length():.2f}m    ignoring.")
                #self.audio.play_local_sound("unknown")
                #log log log
                self.logger.set_value("result_echowave", "entity to far away")
                self.logger.commit_row() 
                return

            print(f"[Game] Entity found: {obj_type} at {rel_location}")
            #log log log
            self.logger.set_value("result_echowave", f"{obj_type} found")
            # self.logger.commit_row() 

            self.audio.duck_music()
            self.audio.play_entity_tone(rel_location, obj_type)
            time.sleep(1.5)

            if self.takeover_manager.is_active():
                print("[Game] Aborting Echolocation Handling.")
                #log log log
                self.logger.set_value("gesturedetect_1round","TOR aborted")
                self.logger.commit_row() 
                return

            if self.gesture.wait_for_gesture(rel_location):
                if self.takeover_manager.is_active():
                    print("[Game] Aborting Echolocation Handling.")
                    self.logger.set_value("gesturedetect_1round", "TOR aborted")
                    self.logger.commit_row() 
                    return

                scored = self.gesture.get_offset_to_target(rel_location)
                print("[Game] Gesture detected! Success.")
                self.score_tracker.update(scored, direction)
                print("[Game] Score:", self.score_tracker.get_score())
                if self.takeover_manager.is_active():
                    print("[Game] Aborting Echolocation Handling.")
                    self.logger.set_value("gesturedetect_1round", "TOR aborted")
                    self.logger.commit_row() 
                    return
                if scored: 
                    self.audio.play_local_sound("confirmation")
                else:
                    self.audio.play_local_sound("fail")
                self.logger.set_value("gesturedetect_1round", True)
                self.logger.commit_row() 
            else:
                self.logger.set_value("gesturedetect_1round", False)
                if self.takeover_manager.is_active():
                    print("[Game] Takeover active before echolocation starts, aborting.")
                    self.logger.set_value("gesturedetect_2round", "TOR aborted")
                    self.logger.commit_row()
                    return
                
                print("[Game] No gesture detected. Playing alarm tone...")
                
                self.audio.play_entity_tone(rel_location, obj_type, alarm=True)
                time.sleep(1.5)

                if self.gesture.wait_for_gesture(rel_location):
                    scored = self.gesture.get_offset_to_target(rel_location)
                    self.score_tracker.update(scored, direction)
                    print("[Game] Score:", self.score_tracker.get_score())
                    if self.takeover_manager.is_active():
                        print("[Game] Aborting Echolocation Handling.")
                        self.logger.set_value("gesturedetect_2round", "TOR aborted")
                        self.logger.commit_row()
                        return
                    if scored: 
                        self.audio.play_local_sound("confirmation")
                    else:
                        self.audio.play_local_sound("fail")
                    self.logger.set_value("gesturedetect_2round", True)
                    self.logger.commit_row()
                else:
                    print("[Game] Gesture failed again. Playing unknown tone.")
                    self.logger.set_value("gesturedetect_2round", False)
                    self.logger.commit_row()
                    #self.audio.play_local_sound("unknown")
        finally:
            self.audio.notify_echolocation_ended()



    def get_relative_location_and_type(self, entity):
        ego_tf = self.ego.get_transform()
        entity_tf = entity.get_transform()

        dx = entity_tf.location.x - ego_tf.location.x
        dy = entity_tf.location.y - ego_tf.location.y
        dz = entity_tf.location.z - ego_tf.location.z

        yaw = math.radians(ego_tf.rotation.yaw)

        # Convert world-space delta to ego-local space
        rel_x = dx * math.cos(-yaw) - dy * math.sin(-yaw)  # Forward (X axis in ego)
        rel_y = dx * math.sin(-yaw) + dy * math.cos(-yaw)  # Right (Y axis in ego)
        rel_z = dz  # Z axis remains unchanged (up)

        rel_location = carla.Location(x=rel_x, y=rel_y, z=rel_z)
        obj_type = self.classify_object(entity)

        translated_location, direction = self.translate_to_directional_location(rel_location)

        return translated_location, obj_type, direction


    def classify_object(self, entity):
        tid = entity.type_id.lower()
        if 'pedestrian' in tid:
            return 'pedestrian'
        elif 'vehicle.bh.crossbike' in tid:
            return 'bicycle'
        elif 'vehicle.bicycle' in tid:
            return 'bicycle'
        elif 'vehicle' in tid:
            return 'car'
        else:
            return 'unknown'

    def translate_to_directional_location(self, rel_location):
        x = rel_location.x
        y = rel_location.y

        # Determine which direction it's closest to
        angle = math.atan2(y, x)  # rel_location in ego-local space

        # Map angle to closest direction
        # Define thresholds (in radians) to determine closest direction
        if -math.pi / 4 <= angle < math.pi / 4:
            # FRONT (positive x-axis in ego space)
            return carla.Location(x=0, y=5, z=0), "front"
        elif math.pi / 4 <= angle < 3 * math.pi / 4:
            # RIGHT (positive y-axis)
            return carla.Location(x=10, y=0, z=0), "right"
        elif angle >= 3 * math.pi / 4 or angle < -3 * math.pi / 4:
            # BACK (negative x-axis)
            return carla.Location(x=0, y=-15, z=0), "back"
        else:
            # LEFT (negative y-axis)
            return carla.Location(x=-10, y=0, z=0), "left"


    def stop(self):
        print("[Game] shutting down.")
        self.active = False
    
    def closeCSV(self):
        if hasattr(self, 'logger'):
            self.logger.close()
