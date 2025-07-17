import cv2
import mediapipe as mp
import pyautogui
import math
import speech_recognition as sr
import threading
import time
from enum import IntEnum
from google.protobuf.json_format import MessageToDict

pyautogui.FAILSAFE = False
mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

# Multi-handedness Labels
class HLabel(IntEnum):
    MINOR = 0
    MAJOR = 1

# Gesture Encodings
class Gest(IntEnum):
    PALM = 0
    THUMB_UP = 1
    THUMB_DOWN = 2
    TWO_PALMS = 3

# Convert Mediapipe Landmarks to recognizable Gestures
class HandRecog:

    def __init__(self, hand_label):
        self.gesture = Gest.PALM
        self.hand_label = hand_label
        self.hand_result = None

    def update_hand_result(self, hand_result):
        self.hand_result = hand_result

    def detect_gesture(self):
        if self.hand_result is None:
            return Gest.PALM

        landmarks = self.hand_result.landmark
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        ring_tip = landmarks[16]
        pinky_tip = landmarks[20]
        wrist = landmarks[0]

        # Check for open palm
        if (all(landmarks[i].y < wrist.y for i in range(5, 21)) and
            self.get_dist(4, 8) > 0.1 and self.get_dist(4, 12) > 0.1):
            self.gesture = Gest.PALM
        # Check if thumb is up
        elif thumb_tip.y < landmarks[3].y < landmarks[2].y:
            self.gesture = Gest.THUMB_UP
        # Check if thumb is down
        elif thumb_tip.y > landmarks[3].y > landmarks[2].y:
            self.gesture = Gest.THUMB_DOWN
        # Check for two open palms
        elif all(landmarks[i].y < wrist.y for i in [5, 6, 9, 10, 13, 14, 17, 18]):
            self.gesture = Gest.TWO_PALMS
        else:
            self.gesture = Gest.PALM

        return self.gesture

    def get_dist(self, point1, point2):
        dist = (self.hand_result.landmark[point1].x - self.hand_result.landmark[point2].x)**2
        dist += (self.hand_result.landmark[point1].y - self.hand_result.landmark[point2].y)**2
        dist = math.sqrt(dist)
        return dist

# Executes commands according to detected gestures
class Controller:
    tx_old = 0
    ty_old = 0

    @staticmethod
    def get_position(hand_result):
        point = 9
        position = [hand_result.landmark[point].x, hand_result.landmark[point].y]
        sx, sy = pyautogui.size()
        x = int(position[0] * sx)
        y = int(position[1] * sy)
        delta_x = x - Controller.tx_old
        delta_y = y - Controller.ty_old
        clocX = Controller.tx_old + delta_x / 7
        clocY = Controller.ty_old + delta_y / 7
        Controller.tx_old, Controller.ty_old = clocX, clocY
        return (clocX, clocY)

    @staticmethod
    def handle_controls(gestures, hand_results):
        clocX, clocY = Controller.get_position(hand_results[0])

        if Gest.PALM in gestures:
            pyautogui.moveTo(clocX, clocY, duration=0.1)
            print("Moving mouse to:", clocX, clocY)
        elif Gest.THUMB_UP in gestures:
            pyautogui.click(button='left')
            print("Left click")
        elif Gest.THUMB_DOWN in gestures:
            pyautogui.click(button='right')
            print("Right click")
        elif gestures.count(Gest.PALM) == 2:
            pyautogui.scroll(50)  # Scroll up
            print("Scroll up")
        elif Gest.PALM in gestures and Gest.THUMB_DOWN in gestures:
            pyautogui.scroll(-50)  # Scroll down
            print("Scroll down")
        else:
            print("Unknown gesture")

# Voice command recognition to toggle gesture controls
def listen_for_commands():
    global gesture_enabled
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    while True:
        with mic as source:
            print("Listening for 'start' or 'stop'...")
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)

        try:
            command = recognizer.recognize_google(audio).lower()
            print(f"Voice Command: {command}")

            if "start" in command and not gesture_enabled:
                gesture_enabled = True
                print("Gesture control started.")
            elif "stop" in command and gesture_enabled:
                gesture_enabled = False
                print("Gesture control stopped.")

        except sr.UnknownValueError:
            print("Could not understand the audio.")
        except sr.RequestError:
            print("Could not request results from Google Speech Recognition service.")

# Main loop to capture video feed and process hand gestures
gesture_enabled = False
cap = cv2.VideoCapture(0)

# Start voice command listener in a separate thread
voice_thread = threading.Thread(target=listen_for_commands)
voice_thread.daemon = True
voice_thread.start()

# Main loop to capture video feed and process hand gestures
cap = cv2.VideoCapture(0)

with mp_hands.Hands(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5) as hands:
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            continue

        image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = hands.process(image)

        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        if gesture_enabled and results.multi_hand_landmarks:  # Only process gestures if enabled
            gestures = []
            hand_results = []
            num_open_palms = 0
            num_fists = 0
            for hand_landmarks, hand_handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                hand_label_dict = MessageToDict(hand_handedness)
                hand_label = hand_label_dict['classification'][0]['label']
                hand_label = HLabel.MINOR if hand_label == 'Left' else HLabel.MAJOR

                hand_rec = HandRecog(hand_label)
                hand_rec.update_hand_result(hand_landmarks)
                gesture = hand_rec.detect_gesture()
                gestures.append(gesture)
                hand_results.append(hand_landmarks)
                print(f"Detected gesture: {gesture.name}")  # Debug print
                
                if gesture == Gest.PALM:
                    num_open_palms += 1
                if gesture == Gest.THUMB_DOWN:
                    num_fists += 1
            
            Controller.handle_controls(gestures, hand_results)
            
            if num_open_palms >= 2:
                pyautogui.scroll(50)  # Scroll up
                print("Scroll up")
            if Gest.PALM in gestures and Gest.THUMB_DOWN in gestures:
                pyautogui.scroll(-50)  # Scroll down
                print("Scroll down")
        
        cv2.imshow('MediaPipe Hands', image)
        if cv2.waitKey(5) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()

