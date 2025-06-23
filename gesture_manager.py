# gesture_manager.py

import time
import cv2
import mediapipe as mp
import math
import statistics
from collections import deque
from csv_logger import CSVLogger

# #REALLY make sure the webcam frame closes
# import atexit
# atexit.register(cv2.destroyAllWindows)

class GestureManager:
    def __init__(self):
        print ("[Debug] gesture init")
        self.debug = False  # or True to view Finger landmarks & extended debug prints
        print ("[Debug] gesture 1")
        self.cap = cv2.VideoCapture(0)# BuG: prob diff cam index at LabPc
        print ("[Debug] gesture 2")
        #capping webcam quality for performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        print ("[Debug] gesture 3")  
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)  
        print ("[Debug] gesture 4")
        self.cap.set(cv2.CAP_PROP_FPS, 15)  #  instead of 60
        print ("[Debug] gesture 5")

        #if not self.cap.isOpened():
        #    raise RuntimeError("Failed to open webcam.")

        # Initialize MediaPipe Hands once, to be used in both tracking and live feed
        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,    
            max_num_hands=1)
        print ("[Debug] gesture 6")
        if self.debug:
            # Store drawing utils
            print ("[Debug] gesture 6.5")
            self.drawing_utils = mp.solutions.drawing_utils
        print ("[Debug] gesture 7")
        self.latest_frame = None
        print ("[Debug] gesture 8")
        self.running = True # open/close Gesture Manager
        print ("[Debug] gesture 9")
        self.allow_gesture_logic = True # enable/disable gesture logic 
        print ("[Debug] gesture 10")

        self.display_override = None  # None = use live feed; otherwise use this frame
        print ("[Debug] gesture 11")

        print("[Gesture] Initializing Webcam...")
        # Start webcam loop in background
        import threading
        print ("[Debug] gesture 12")
        threading.Thread(target=self._webcam_loop, daemon=True).start()
        print ("[Debug] gesture 13")

        self.last_gesture_angle = None  # stores the last gesture angle (after sominant angle translation)
        print ("[Debug] gesture 14")
        self.last_precise_gesture_angle = None  # stores the last precise gesture angle (actual detected hand angle)
        print ("[Debug] gesture 15")

        #Initiate logger
        self.logger = CSVLogger("gestureLog", [ # initate CSV logger with those Columns
            "timestamp_initGestureTime",
            "timestamp_inputGestureTime","gesture_reactTime","angle_preciseGesture","angle_gesture", "angle_object",
            "angle_deviation", "matched_objAngle"
        ])

        print ("[Debug] gesture ready")

    def __del__(self):
        self.running = False
        if self.cap:
            self.cap.release()
        if hasattr(self, 'hands'):
            self.hands.close()
        cv2.destroyAllWindows()

    def _webcam_loop(self):
        """
        Continuously shows webcam feed. Uses self.display_override if set.
        """
        print("[Gesture] Webcam feed running. Press ESC in window to close it.")
        while self.running:
            success, frame = self.cap.read()
            if not success:
                continue

            frame = cv2.flip(frame, 1)
            frame = cv2.flip(frame, 1) # UNCOMMENT THIS LINE FOR LAB SETUP, Comment for Laptop testing

            self.latest_frame = frame.copy()

            if self.debug: #activate handtracking for whole webcam loop in debug mode
                image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.hands.process(image_rgb)
                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        mp.solutions.drawing_utils.draw_landmarks(
                            frame, hand_landmarks, mp.solutions.hands.HAND_CONNECTIONS
                        )

            # Show the override frame if available, otherwise show normal live feed
            display_frame = self.display_override if self.display_override is not None else frame

            cv2.imshow("Gesture Camera", display_frame)

            if cv2.waitKey(5) & 0xFF == 27:
                self.running = False
                break

        self.cap.release()
        cv2.destroyAllWindows()

    def wait_for_gesture(self, target_location, timeout=7.0):
        """
        Tracks gesture for a limited time. Returns True only if the user
        holds a pointing gesture for a certain duration.
        """
        if not self.allow_gesture_logic:
            return False

        print("[Gesture] Waiting for gesture...")

        #Reset values
        detected = False
        self.last_gesture_angle = None

        # Require the gesture angle to stay within a small deviation range for at least X amount of frames to be detected as true
        angle_buffer = deque(maxlen=10) # buffer frame depth (adjust as you please)  
        wobble_threshold = 10.0  # Max standard deviation allowed for stability
        frame_counter = 0 # to analyze only every second frame -> less CPU impact

        start_time = time.time()
        #log log log
        self.logger.set_value("timestamp_initGestureTime", round(start_time, 4))

        #for debug, remove in running study
        object_angle = self.get_object_angle(target_location)
        print(f"Object angle: {object_angle}")

        while self.running and self.allow_gesture_logic and  (time.time() - start_time < timeout):
            if self.latest_frame is None:
                continue

            frame_counter += 1
            if frame_counter % 2 != 0:
                continue

            frame = self.latest_frame.copy()

            # Red border to indicate tracking is active
            cv2.rectangle(frame, (0, 0), (frame.shape[1]-1, frame.shape[0]-1), (0, 0, 255), 3)

            frame, gesture_angle = self.get_hand_angle(frame, self.hands)

            if gesture_angle is not None:
                angle_buffer.append(gesture_angle)

                if len(angle_buffer) == angle_buffer.maxlen:
                    wobble = statistics.stdev(angle_buffer)

                    if wobble < wobble_threshold:
                        print("[Gesture] Intentional gesture detected.")

                        gestureInput_time=time.time()
                        self.logger.set_value("timestamp_inputGestureTime", round(gestureInput_time, 4))
                        gestureReact_time=gestureInput_time-start_time
                        self.logger.set_value("gesture_reactTime", round(gestureReact_time, 4))
                        
                        self.logger.set_value("angle_preciseGesture", angle_buffer[-1])
                        dominant_direction_angle = self.translate_handAngle_to_dominant_direction_angle(angle_buffer[-1]) # most recently appended angle
                        self.last_gesture_angle = dominant_direction_angle

                        print(f"[Gesture] Actual Gesture angle: {angle_buffer[-1]}")
                        print(f"[Gesture] Dominant Gesture angle: {self.last_gesture_angle}")

                        
                        detected = True
                        break
                    else:
                        print("[Gesture] Gesture still wobbles, hold hand steady")

            self.display_override = frame
            time.sleep(0.05)

        self.display_override = None

        return detected

    def get_hand_angle(self, frame, hands):
        """
        Processes frame and returns gesture angle if hand is detected.
        """
        if not self.allow_gesture_logic:
            return frame, None

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(image_rgb)

        h, w, _ = frame.shape
        current_angle = None

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:

                if self.debug:
                    self.drawing_utils.draw_landmarks(
                        frame, hand_landmarks, mp.solutions.hands.HAND_CONNECTIONS)

                is_index_extended = self.is_finger_extended(hand_landmarks.landmark, [5, 6, 8])

                if self.debug:
                    print(f"[Debug] Index extended: {is_index_extended}")

                if is_index_extended:
                    print("[Debug] Valid finger pointing gesture detected (index extended).")
                    tip = hand_landmarks.landmark[8]
                    base = hand_landmarks.landmark[6]
                    p1 = [tip.x * w, tip.y * h]
                    p2 = [base.x * w, base.y * h]
                    current_angle = self.calculate_direction_angle(p1, p2)
                else:
                    print("[Debug] Pointing Gesture rejected: index not extended.")

        return frame, current_angle

    def is_finger_extended(self, landmarks, finger_indices):
        def angle(a, b, c):
            ab = [a.x - b.x, a.y - b.y]
            cb = [c.x - b.x, c.y - b.y]
            dot = ab[0]*cb[0] + ab[1]*cb[1]
            mag_ab = math.hypot(*ab)
            mag_cb = math.hypot(*cb)
            if mag_ab * mag_cb == 0:
                return 0
            return math.degrees(math.acos(dot / (mag_ab * mag_cb)))

        base, middle, tip = [landmarks[i] for i in finger_indices]
        bend_angle = angle(base, middle, tip)
        if self.debug:
            print(f"[Debug] Finger bend angle: {bend_angle:.2f}")
        return bend_angle > 150  # Threshold: nearly straight

    def translate_handAngle_to_dominant_direction_angle(self, angle):
        """
        Takes an angle in degrees (0–360) and returns the dominant cardinal direction angle:
        - 0°   = FRONT
        - 90°  = RIGHT
        - 180° = BACK
        - 270° = LEFT

        Direction ranges (inclusive/exclusive): matches with the one from echolocation_game
        - FRONT:  [315°, 360) and [0°, 45)
        - RIGHT:  [45°, 135)
        - BACK:   [135°, 225)
        - LEFT:   [225°, 315)
        """
        if angle >= 315 or angle < 45:
            return 0      # FRONT
        elif 45 <= angle < 135:
            return 90     # RIGHT
        elif 135 <= angle < 225:
            return 180    # BACK
        elif 225 <= angle < 315:
            return 270    # LEFT

    def get_object_angle(self, target_location):
        """
        Calculates object angle relative assuming hero_pos =(0, 0) and returns the object angle
        """
        if not self.allow_gesture_logic:
            return

        angle_deg = (math.degrees(math.atan2(target_location.x, target_location.y)) + 360) % 360
        direction_angle = int(angle_deg)

        return direction_angle

    def calculate_deviation(self, angle1, angle2):
        """
        Calculate Angle deviation between gesture-angle and object-angle
        """
        if not self.allow_gesture_logic:
            return

        deviation = abs(angle1 - angle2)
        if deviation > 180:
            deviation = 360 - deviation
        return deviation

    def calculate_direction_angle(self, p1, p2):
        """
        Calculates angle from point p1 to p2 in screen coordinates (0° = up).
        """
        if not self.allow_gesture_logic:
            return

        dx = p2[0] - p1[0]
        dy = p1[1] - p2[1]
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        angle_int = int(angle_deg) # make angle an int for simplicity
        return (270 - angle_int) % 360

    def get_offset_to_target(self, target_location):
        """
        Computes and returns the deviation between the last gesture angle and the object.
        """
        if not self.allow_gesture_logic:
            return False #for the Score we know TOR was requested and dont count it

        if not hasattr(self, 'last_gesture_angle'):
            print("[Gesture] No gesture angle available.")
            return False #for the Score we know something is not right and dont count it

        gesture_angle = self.last_gesture_angle
        object_angle = self.get_object_angle(target_location)
        deviation = self.calculate_deviation(gesture_angle, object_angle)

        print(f"[Gesture] Object angle: {object_angle}")

        self.logger.set_value("angle_gesture", gesture_angle)
        self.logger.set_value("angle_object", object_angle)
        self.logger.set_value("angle_deviation", deviation)

        if deviation == 0:
            self.logger.set_value("matched_objAngle", True)
            self.logger.commit_row() # All 6 values are now set
            return True
        else:
            self.logger.set_value("matched_objAngle", False)
            self.logger.commit_row() # All 6 values are now set
            return False
        

    def shutdown(self):
        """
        Properly shuts down webcam and closes any OpenCV windows, logs the last row and closes logger stream
        """
        print("[Gesture] Shutting down webcam thread...")
        self.running = False
        time.sleep(0.05)  # Let the thread exit

        try:
            if hasattr(self.logger, "commit_row"):
                self.logger.commit_row()
            if hasattr(self.logger, "close"):
                self.logger.close()
        except Exception as e:
            print(f"[Gesture] Logger cleanup failed: {e}")

    def enable_gesture_process(self, activebool):
        """
        Stops/Enables gesture detection without killing the webcam loop.
        """
        self.allow_gesture_logic = activebool

        if not activebool:
            print("[Gesture] Gesture detection disabled as TOR active")
            if hasattr(self, "logger"):
                self.logger.set_value("angle_deviation", "TOR aborted") #so we know this process was aborted by TOR
                self.logger.commit_row()
        else:
            print("[Gesture] Gesture detection enabled as TOR ended")
