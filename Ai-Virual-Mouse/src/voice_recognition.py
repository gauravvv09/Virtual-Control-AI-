import speech_recognition as sr

class VoiceControl:
    def __init__(self):
        self.is_active = False
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

    def listen_for_commands(self):
        """ Listens for 'start' or 'stop' commands to control gesture recognition."""
        with self.microphone as source:
            print("Listening for commands...")
            self.recognizer.adjust_for_ambient_noise(source)  # Adjust for ambient noise
            audio = self.recognizer.listen(source)
        
        try:
            command = self.recognizer.recognize_google(audio).lower()
            print(f"Voice command received: {command}")
            if "start" in command:
                self.start_gesture_control()
            elif "stop" in command:
                self.stop_gesture_control()
        except sr.UnknownValueError:
            print("Sorry, I could not understand the command.")
        except sr.RequestError:
            print("Sorry, there was an error with the speech recognition service.")
    
    def start_gesture_control(self):
        """ Activate gesture control """
        self.is_active = True
        print("Gesture control started.")

    def stop_gesture_control(self):
        """ Deactivate gesture control """
        self.is_active = False
        print("Gesture control stopped.")
    
    def is_control_active(self):
        """ Returns whether gesture control is active. """
        return self.is_active
