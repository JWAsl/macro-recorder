"""
Manages playback of the recorded macro.
"""
import threading
import pyautogui
import keyboard

from time import sleep, time

from utils.key_mappings import key_map
from utils.countdown import countdown_timer


class MacroPlayer:
    """ 
    Manages playback of the recorded macro.

    This class plays back a serialized JSON of recorded events and simulates those events using pyautogui.
    It supports a pause/resume feature triggered by a hotkey.
    """
    # use keyboard library key codes
    PAUSE_KEY: str = 'pause'
    """
    Determines how far each 'scroll' action will travel.
    A user might need to edit it to match how far one notch of their mouse wheel travels on their system
    """
    SCROLL_MULTIPLIER: int = 120

    def __init__(self) -> None:
        """
        Initializes the MacroPlayer with default settings and action handlers.
        """
        pyautogui.FAILSAFE = True
        self.is_paused = False
        # Condition variable for thread synchronization (pause/resume)
        self.pause_lock: threading.Condition = threading.Condition()
        # Importing pynput -> pyautogui key code conversions from key_mappings.py
        self.key_map = key_map
        self.action_handlers = {
            'click': self.handle_click,
            'keyDown': self.handle_key_down,
            'keyUp': self.handle_key_up,
            'scroll': self.handle_scroll
        }

    def handle_click(self, action) -> None:
        self.wait_if_paused()
        button_map = {
            "Button.left": "left",
            "Button.right": "right",
            "Button.middle": "middle"
        }
        button = button_map.get(action['button'], 'left')

        pyautogui.click(
            x=action['pos'][0],
            y=action['pos'][1],
            duration=0,
            button=button
        )
        # print(f"{button} click on {action['pos']}")

    def handle_key_down(self, action) -> None:
        self.wait_if_paused()
        key: str = self.convert_key(action['button'])
        pyautogui.keyDown(key)
        # print(f"Keydown on {key}")

    def handle_key_up(self, action) -> None:
        self.wait_if_paused()
        key: str = self.convert_key(action['button'])
        pyautogui.keyUp(key)
        # print(f"Keyup on {key}")

    def handle_scroll(self, action) -> None:
        self.wait_if_paused()
        x: float = action['pos'][0]
        y: float = action['pos'][1]
        dx: int = action['scroll_direction'].get('dx', 0)
        dy: int = action['scroll_direction'].get('dy', 0)

        pyautogui.moveTo(x, y)

        if dy != 0:
            pyautogui.scroll(int(dy * self.SCROLL_MULTIPLIER))
            '''
            print(
                f"Scrolled vertically: {int(dy * self.SCROLL_MULTIPLIER)} at {x}, {y}")
            '''

        if dx != 0:
            pyautogui.hscroll(int(dx * self.SCROLL_MULTIPLIER))
            '''
            print(
                f"Scrolled horizontally: {int(dx * self.SCROLL_MULTIPLIER)} at {x}, {y}")
            '''

    def toggle_pause(self) -> None:
        """
        Toggles the playback state between paused and resumed.
        This method is called by the hotkey listener thread.
        """
        was_paused: bool = False

        with self.pause_lock:
            self.is_paused = not self.is_paused
            was_paused = self.is_paused
            print(f"Playback paused: {self.is_paused}")
            if not self.is_paused:
                # Notify the playback loop to resume
                self.pause_lock.notify_all()
                countdown_timer()

        # This sleep prevents the user from accidentally resuming right after attempting to pause
        if was_paused:
            print("Playback paused. Ignoring further hotkey presses for 3 seconds.")
            sleep(3)

    def start_pause_listener(self) -> None:
        """
        Sets up a hotkey listener for the pause key.
        """
        keyboard.add_hotkey(self.PAUSE_KEY, self.toggle_pause)

    def wait_if_paused(self) -> None:
        """
        Blocks the playback thread if the playback is paused.
        """
        with self.pause_lock:
            while self.is_paused:
                print("Currently paused... Press 'pause' to resume.")
                # This will block until a notify() call is received from toggle_pause
                self.pause_lock.wait()

    def play_actions(self, data) -> None:
        """
        Iterates through a list of actions and simulates them.

        Args:
            data: A list of dictionaries, where each dictionary represents a recorded event.
        """
        self.start_pause_listener()
        for index, action in enumerate(data):
            self.wait_if_paused()

            if action['button'] == 'Key.esc':
                print("Encountered ESC key in macro, playback ending.")
                break

            handler = self.action_handlers.get(action['type'])
            if handler:
                handler(action)
            else:
                raise Exception(
                    'No action handler found for type: {}'.format(action['type']))

            if index + 1 < len(data):
                next_action = data[index + 1]
                self.handle_delay(action, next_action)

        # Clean up the hotkey listener after playback is complete.
        keyboard.remove_hotkey(self.PAUSE_KEY)
        print("Playback finished.")

    def handle_delay(self, current_action, next_action) -> None:
        """
        Pauses execution for the time duration between two recorded actions.
        """
        elapsed_time: float = next_action['time'] - current_action['time']
        if elapsed_time < 0:
            raise ValueError(
                'Unexpected ordering between next_action and current_action.')

        slept: float = 0.0
        while slept < elapsed_time:
            self.wait_if_paused()
            start_time: float = time()
            # Sleep for a small, fixed interval to allow for responsiveness to pause hotkey.
            sleep(min(0.01, elapsed_time - slept))
            slept += time() - start_time

    def convert_key(self, button: str) -> str:
        """
        Converts a pynput key string to a PyAutoGUI library key string.
        """
        return self.key_map.get(button, button)
