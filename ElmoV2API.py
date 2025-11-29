import requests

class ElmoV2API:
    PORT = 8001

    def __init__(self, robot_ip, debug=False):
        self.REQUEST_PATH = f"http://{robot_ip}:{self.PORT}/"
        self.GET_REQUEST_PATH = self.REQUEST_PATH + "status"
        self.POST_COMMAND_PATH = self.REQUEST_PATH + "command"
        self.debug = debug

    # Check the status of the robot and
    def status(self):
        try:
            response = requests.get(self.GET_REQUEST_PATH)
            response.raise_for_status()
            # Additional code will only run if the request is successful

            if self.debug:
                print(response.json())

            return response.json()

        except requests.exceptions.HTTPError as error:
            print(error)


    def enable_behavior(self, name, control):
        command = {
            "op": "enable_behaviour",
            "name": name,
            "control": control,
        }
        self.post_command(command)

    def set_pan_torque(self, control):
        command = {
            "op": "set_pan_torque",
            "control": control,
        }
        self.post_command(command)

    def set_pan(self, angle):
        command = {
            "op": "set_pan",
            "angle": angle,
        }
        self.post_command(command)

    def set_tilt_torque(self, control):
        command = {
            "op": "set_tilt_torque",
            "control": control,
        }
        self.post_command(command)

    def set_tilt(self, angle):
        command = {
            "op": "set_tilt",
            "angle": angle,
        }
        self.post_command(command)

    def play_sound(self, name):
        command = {
            "op": "play_sound",
            "name": name,
        }
        self.post_command(command)

    def play_audio(self, name):
        command = {
            "op": "play_audio",
            "name": name,
        }
        self.post_command(command)

    def set_volume(self, volume):
        command = {
            "op": "set_volume",
            "volume": volume,
        }
        self.post_command(command)

    def start_recording(self):
        command = {
            "op": "start_recording",
        }
        self.post_command(command)

    def stop_recording(self):
        command = {
            "op": "stop_recording",
        }
        self.post_command(command)

    def set_screen(self, image="", video="", text="", url=""):
        command = {
            "op": "set_screen",
            "image": image,
            "video": video,
            "text": text,
            "url": url
        }
        self.post_command(command)

    def update_leds(self, colors):
        command = {
            "op": "update_leds",
            "colors": colors,
        }
        self.post_command(command)

    def update_leds_icon(self, name):
        command = {
            "op": "update_leds_icon",
            "name": name,
        }
        self.post_command(command)

    def start_video_recording(self):
        command = {
            "op": "start_video_recording",
        }
        self.post_command(command)

    def stop_video_recording(self):
        command = {
            "op": "stop_video_recording",
        }
        self.post_command(command)

    def reboot(self):
        command = {
            "op": "reboot",
        }
        self.post_command(command)

    def shutdown(self):
        command = {
            "op": "shutdown",
        }
        self.post_command(command)

    def post_command(self, command):
        try:
            response = requests.post(self.POST_COMMAND_PATH, json=command)
            response.raise_for_status()
            # Additional code will only run if the request is successful
        except requests.exceptions.HTTPError as error:
            print(error)

        if self.debug:
            print(response.json())
