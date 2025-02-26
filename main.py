from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.card import MDCard
import threading
import time
import os

# Thresholds for detecting an accident
GYRO_THRESHOLD = 5.0  # degrees/second
ACCEL_THRESHOLD = 5.0
MOCK_GPS_COORDINATES = {'latitude': 40.7128, 'longitude': -74.0060}

accident_prompt_shown = False
accident_loop_exit = False

# KivyMD Screens
KV = '''
ScreenManager:
    MainScreen:
    ResultScreen:

<MainScreen>:
    name: "main"
    MDBoxLayout:
        orientation: "vertical"
        spacing: dp(10)
        padding: dp(20)

        MDLabel:
            text: "Accident Detection System"
            halign: "center"
            font_style: "H5"

        MDTextField:
            id: file_path
            hint_text: "Enter or Browse Sensor Data File Path"
            size_hint_x: 0.9
            pos_hint: {"center_x": 0.5}

        MDRaisedButton:
            text: "Browse"
            size_hint_x: 0.5
            pos_hint: {"center_x": 0.5}
            on_release: app.open_file_manager()

        MDRaisedButton:
            text: "Start Monitoring"
            size_hint_x: 0.5
            pos_hint: {"center_x": 0.5}
            on_release: app.start_monitoring()

<ResultScreen>:
    name: "results"
    MDBoxLayout:
        orientation: "vertical"
        spacing: dp(10)
        padding: dp(20)

        MDLabel:
            text: "Accident Detection Results"
            halign: "center"
            font_style: "H5"

        MDScrollView:
            MDList:
                id: results_list

        MDRaisedButton:
            text: "Back to Main Screen"
            size_hint_x: 0.5
            pos_hint: {"center_x": 0.5}
            on_release: app.go_back_to_main()
'''


# Screens
class MainScreen(Screen):
    pass


class ResultScreen(Screen):
    pass


class AccidentDetectionApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.file_manager = MDFileManager(exit_manager=self.close_file_manager, select_path=self.select_file_path)
        self.file_path = ""
        self.monitor_thread = None

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        return Builder.load_string(KV)

    def open_file_manager(self):
        self.file_manager.show(os.getcwd())  # Show current working directory

    def close_file_manager(self, *args):
        self.file_manager.close()

    def select_file_path(self, path):
        self.root.get_screen("main").ids.file_path.text = path
        self.file_manager.close()

    def start_monitoring(self):
        file_path = self.root.get_screen("main").ids.file_path.text
        if not os.path.exists(file_path):
            self.show_dialog("Error", "Invalid file path! Please select a valid file.")
            return

        self.file_path = file_path
        self.root.current = "results"  # Ensure the correct screen name is used
        self.monitor_thread = threading.Thread(target=self.monitor_sensor_data, daemon=True)
        self.monitor_thread.start()

    def monitor_sensor_data(self):
        """
        Automatically monitors the sensor data file at regular intervals.
        """
        while True:
            file_path = self.file_path
            if os.path.exists(file_path):
                gyroscope_data, accelerometer_data = self.read_sensor_data_from_file(file_path)
                results = self.detect_accident(gyroscope_data, accelerometer_data)
                if results:
                    Clock.schedule_once(lambda *args: self.show_accident_results(results))
            time.sleep(15)  # Check every 15 seconds

    def read_sensor_data_from_file(self, file_path):
        gyroscope_data = []
        accelerometer_data = []
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                next(file)  # Skip header
                for line in file:
                    parts = line.strip().split(',')
                    if len(parts) == 7:
                        gx, gy, gz = map(float, parts[1:4])
                        ax, ay, az = map(float, parts[4:7])
                        gyroscope_data.append((gx, gy, gz))
                        accelerometer_data.append((ax, ay, az))
        except Exception as e:
            self.show_dialog("File Error", f"Could not read {file_path}. Ensure the format is correct.")
            print(f"Error reading file {file_path}: {e}")  # Log error
        return gyroscope_data, accelerometer_data

    def detect_accident(self, gyroscope_data, accelerometer_data):
        results = []
        ax_data = [ax for ax, ay, az in accelerometer_data]
        smoothed_ax = self.moving_average(ax_data, 5)

        for i, (gx, gy, gz) in enumerate(gyroscope_data):
            if abs(gx) > GYRO_THRESHOLD or abs(gy) > GYRO_THRESHOLD or abs(gz) > GYRO_THRESHOLD:
                results.append(f"Gyroscope spike detected at {i}s: {gx}, {gy}, {gz}")
            if i < len(smoothed_ax) and abs(smoothed_ax[i]) > ACCEL_THRESHOLD:
                results.append(f"Accelerometer spike detected at {i}s: {smoothed_ax[i]}")
        return results

    def moving_average(self, data, window_size):
        if len(data) < window_size:
            return data
        return [sum(data[i:i + window_size]) / window_size for i in range(len(data) - window_size + 1)]

    def show_accident_results(self, results):
        def update_ui(*args):
            # Clear previous results
            results_list = self.root.get_screen("results").ids.results_list
            results_list.clear_widgets()

            # Add new results inside MDCard for better UI
            for result in results:
                card = MDCard(
                    size_hint=(None, None),
                    size=("280dp", "100dp"),
                    padding=("10dp"),
                    elevation=10,
                    radius=[10, 10, 10, 10],
                    orientation="vertical"
                )
                card.add_widget(MDLabel(text=result, theme_text_color="Secondary", halign="left", size_hint_y=None, height="40dp"))
                results_list.add_widget(card)

        # Schedule UI update on the main thread
        Clock.schedule_once(update_ui)

        # Show the dialog asking if the person is okay only if the dialog hasn't been shown yet
        if not accident_prompt_shown:
            self.prompt_user_for_response()

    def prompt_user_for_response(self):
        global accident_prompt_shown
        if not accident_prompt_shown:
            dialog = MDDialog(
                title="Accident Detected",
                text="Are you okay?",
                buttons=[
                    MDFlatButton(text="YES", on_release=self.user_is_okay),
                    MDRaisedButton(text="NO", on_release=self.call_emergency_services),
                ],
            )
            dialog.open()

            # Set a 3-second timer to automatically call emergency services if no response
            Clock.schedule_once(lambda *args: self.call_emergency_services(), 3)

    def user_is_okay(self, *args):
        self.show_dialog("Response", "Glad to hear you're okay!")
        global accident_prompt_shown
        accident_prompt_shown = True  # Prevent the dialog from appearing again

    def call_emergency_services(self, *args):
        self.show_dialog("Emergency", f"Calling emergency services...\nLocation: {MOCK_GPS_COORDINATES}")
        global accident_prompt_shown
        accident_prompt_shown = True  # Prevent the dialog from appearing again

    def show_dialog(self, title, message):
        if hasattr(self, 'dialog') and self.dialog:
            self.dialog.dismiss()
        self.dialog = MDDialog(
            title=title,
            text=message,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: self.dialog.dismiss())]
        )
        self.dialog.open()

    def go_back_to_main(self):
        global accident_loop_exit
        accident_loop_exit = True
        self.root.current = "main"


if __name__ == "__main__":
    AccidentDetectionApp().run()









