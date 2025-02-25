from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.properties import StringProperty
from plyer import accelerometer, gyroscope, gps, sms
import platform
import time


class AccidentDetector(BoxLayout):
    status_text = StringProperty("Monitoring...")
    location_text = StringProperty("Unknown")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.acc_threshold = 5.0  # 5g acceleration
        self.gyro_threshold = 10.0  # 10 rad/s angular velocity
        self.emergency_contacts = ["+1234567890"]  # Add your contacts here
        self.accident_detected = False

        # Initialize layout
        self.orientation = 'vertical'

        # Create labels for status and location
        self.status_label = Label(text=self.status_text, font_size='20sp')
        self.location_label = Label(text=self.location_text, font_size='20sp')

        self.add_widget(self.status_label)
        self.add_widget(self.location_label)

        # Initialize sensors
        self.init_sensors()

        # Start GPS
        self.init_gps()

    def init_sensors(self):
        try:
            if platform.system() != "Windows":
                accelerometer.enable()
                gyroscope.enable()
                Clock.schedule_interval(self.check_sensors, 0.1)  # Check every 100ms
            else:
                self.status_text = f"Sensors not available on {platform.system()}!"
                # Simulate sensors for testing on Windows
                self.status_text = "Using mock sensors"
                Clock.schedule_interval(self.mock_check_sensors, 0.1)  # Check every 100ms
        except NotImplementedError:
            self.status_text = "Sensors not available!"
        self.update_ui()

    def init_gps(self):
        try:
            if platform.system() != "Windows":
                gps.configure(on_location=self.on_gps_location)
                gps.start()
            else:
                self.location_text = f"GPS not available on {platform.system()}!"
        except NotImplementedError:
            self.location_text = "GPS not available!"
        self.update_ui()

    def on_gps_location(self, **kwargs):
        self.lat = kwargs.get('lat')
        self.lon = kwargs.get('lon')
        self.location_text = f"Lat: {self.lat}, Lon: {self.lon}"
        self.update_ui()

    def mock_check_sensors(self, dt):
        # Simulated data for testing on Windows
        accel = (1, 1, 1)  # Simulated acceleration
        gyro = (1, 1, 1)  # Simulated gyroscope

        # Check if accident is detected (use same logic as in `check_sensors`)
        if not self.accident_detected and self.is_accident(accel, gyro):
            self.trigger_emergency()

    def check_sensors(self, dt):
        try:
            accel = accelerometer.acceleration
            gyro = gyroscope.rotation

            if not self.accident_detected and self.is_accident(accel, gyro):
                self.trigger_emergency()

        except Exception as e:
            self.status_text = f"Error: {str(e)}"
        self.update_ui()

    def is_accident(self, accel, gyro):
        # Calculate net acceleration (excluding gravity)
        net_accel = (accel[0] ** 2 + accel[1] ** 2 + accel[2] ** 2) ** 0.5

        # Calculate net angular velocity
        net_gyro = (gyro[0] ** 2 + gyro[1] ** 2 + gyro[2] ** 2) ** 0.5

        # Check thresholds
        if net_accel > self.acc_threshold and net_gyro > self.gyro_threshold:
            return True
        return False

    def trigger_emergency(self):
        self.accident_detected = True
        self.status_text = "Accident detected! Sending alerts..."

        # Get current location
        location = f"Emergency! Possible accident at: {self.lat}, {self.lon}"

        # Send SMS to emergency contacts
        for contact in self.emergency_contacts:
            try:
                sms.send(recipient=contact, message=location)
            except Exception as e:
                self.status_text = f"Failed to send SMS: {str(e)}"

        # Schedule system to reset after 1 minute
        Clock.schedule_once(self.reset_system, 60)
        self.update_ui()

    def reset_system(self, dt):
        self.accident_detected = False
        self.status_text = "Monitoring resumed..."
        self.update_ui()

    def update_ui(self):
        # Update the labels with the latest status and location text
        self.status_label.text = self.status_text
        self.location_label.text = self.location_text


class AccidentDetectionApp(App):
    def build(self):
        return AccidentDetector()

    def on_pause(self):
        return True

    def on_resume(self):
        pass


if __name__ == '__main__':
    AccidentDetectionApp().run()
