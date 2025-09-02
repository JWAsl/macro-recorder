"""
Manages playback of the recorded macro.
"""
import threading
import pyautogui
import keyboard

import time

from utils.key_mappings import key_map
from utils.countdown import countdown_timer

# time.perf_counter() > time()
# to fix the performance issues with playback


class MacroPlayer:
    """ 
    Manages playback of the recorded macro.

    This class plays back a serialized JSON of recorded events and simulates those events using pyautogui.
    It supports a pause/resume feature triggered by a hotkey.
    """
    # use keyboard library key codes
    PAUSE_KEY = 'pause'
    """
    Determines how far each 'scroll' action will travel.
    A user might need to edit it to match how far one notch of their mouse wheel travels on their system
    """
    SCROLL_MULTIPLIER: int = 120
    """
    The time in seconds to wait between pressing keys in a hotkey combination
    to ensure the OS registers the key press.
    """
    HOTKEY_DELAY: float = 0.05

    def __init__(self):
        """
        Initializes the MacroPlayer with default settings and action handlers.
        """
        pyautogui.FAILSAFE = False
        self.is_paused = False
        # Condition variable for thread synchronization (pause/resume)
        self.pause_lock = threading.Condition()
        # Importing pynput -> pyautogui key code conversions from key_mappings.py
        self.key_map = key_map
        self.action_handlers = {
            'click': self.handle_click,
            'keyDown': self.handle_key_down,
            'keyUp': self.handle_key_up,
            'scroll': self.handle_scroll
        }
        # Keep track of which keys are currently held down
        self.pressed_keys = set()
        self.mouse_button_map = {
            "Button.left": "left",
            "Button.right": "right",
            "Button.middle": "middle"
        }

    def _press_and_release_combination(self, keys: list) -> None:
        """
        Presses and releases a list of keys in sequence with a small delay.
        This is a more reliable way to handle hotkey combinations.

        Args:
            keys: A list of key names to press.
        """
        print(f"Executing hotkey combination: {keys}")

        # Press all keys in the combination
        for key in keys:
            pyautogui.keyDown(key)
            time.sleep(self.HOTKEY_DELAY)

        # Release all keys in the reverse order
        for key in reversed(keys):
            pyautogui.keyUp(key)
            time.sleep(self.HOTKEY_DELAY)

    def handle_click(self, action) -> None:
        self.wait_if_paused()
        button = self.mouse_button_map.get(action['button'], 'left')

        # Move to the position before clicking
        if action['pos']:
            pyautogui.moveTo(
                x=action['pos'][0],
                y=action['pos'][1]
            )

        pyautogui.click(
            button=button
        )
        print(f"Click: {button} at {action['pos']}")

    def handle_key_down(self, action) -> None:
        self.wait_if_paused()
        key = self.convert_key(action['button'])
        if key not in self.pressed_keys:
            pyautogui.keyDown(key)
            self.pressed_keys.add(key)
            print(f"Key down: {key}")

    def handle_key_up(self, action) -> None:
        self.wait_if_paused()
        key = self.convert_key(action['button'])
        if key in self.pressed_keys:
            pyautogui.keyUp(key)
            self.pressed_keys.remove(key)
            print(f"Key up: {key}")

    def handle_scroll(self, action) -> None:
        self.wait_if_paused()
        x = action['pos'][0]
        y = action['pos'][1]
        dx = action['scroll_direction'].get('dx', 0)
        dy = action['scroll_direction'].get('dy', 0)

        pyautogui.moveTo(x, y)

        if dy != 0:
            pyautogui.scroll(int(dy * self.SCROLL_MULTIPLIER))
            print(
                f"Scrolled vertically: {int(dy * self.SCROLL_MULTIPLIER)} at {x}, {y}")

        if dx != 0:
            pyautogui.hscroll(int(dx * self.SCROLL_MULTIPLIER))
            print(
                f"Scrolled horizontally: {int(dx * self.SCROLL_MULTIPLIER)} at {x}, {y}")

    def toggle_pause(self) -> None:
        """
        Toggles the playback state between paused and resumed.
        This method is called by the hotkey listener thread.
        """
        with self.pause_lock:
            self.is_paused = not self.is_paused
            if not self.is_paused:
                print("Resuming playback...")
                self.pause_lock.notify_all()
                countdown_timer()
            else:
                print("Playback paused.")

        # This sleep prevents the user from accidentally resuming right after attempting to pause
        if self.is_paused:
            print("Playback paused. Ignoring further key presses for 3 seconds.")
            time.sleep(3)

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
                print(f"Currently paused... Press {self.PAUSE_KEY} to resume.")
                # This will block until a notify() call is received from toggle_pause
                self.pause_lock.wait()

    def play_actions(self, data) -> None:
        """
        Iterates through a list of actions and simulates them.

        Args:
            data: A list of dictionaries, where each dictionary represents a recorded event.
        """
        self.start_pause_listener()

        # Clear any initially pressed keys from previous runs
        self.pressed_keys.clear()

        # Set a satartikng point for the playback timer
        playback_start_time = time.perf_counter()

        # Store the absolute time of the last played action
        macro_start_time = data[0]['time'] if data else 0

        for index, action in enumerate(data):
            self.wait_if_paused()

            # This is the target time for the current action, relative to playback start.
            # We use the absolute timestamps from the recording.
            target_playback_time = (action['time'] - macro_start_time)

            # Wait until the target time has passed since the start of the playback loop
            while (time.perf_counter() - playback_start_time) < target_playback_time:
                pass  # We use a busy-wait for maximum precision.

            if self.convert_key(action['button']) == 'esc':
                print("Encountered ESC key in macro, playback ending.")
                break

            handler = self.action_handlers.get(action['type'])
            if handler:
                handler(action)
            else:
                raise Exception(
                    'No action handler found for type: {}'.format(action['type']))

        # Ensure all keys are released at the end of playback
        self.cleanup()

        # Clean up the hotkey listener after playback is complete.
        keyboard.remove_hotkey(self.PAUSE_KEY)
        print("Playback finished.")

    def cleanup(self) -> None:
        """
        Releases any keys that might still be pressed at the end of playback.
        """
        for key in list(self.pressed_keys):
            try:
                pyautogui.keyUp(key)
                print(f"Releasing key: {key}")
            except Exception as e:
                print(f"Could not release key {key}: {e}")
        self.pressed_keys.clear()

    def handle_delay(self, current_action, next_action) -> None:
        """
        Pauses execution for the time duration between two recorded actions.
        """
        elapsed_time = next_action['time'] - current_action['time']
        if elapsed_time < 0:
            raise ValueError(
                'Unexpected ordering between next_action and current_action.')

        slept = 0.0
        while slept < elapsed_time:
            self.wait_if_paused()
            start_time: float = time()
            # Sleep for a small, fixed interval to allow for responsiveness to pause hotkey.
            time.sleep(min(0.01, elapsed_time - slept))
            slept += time() - start_time

    def convert_key(self, button) -> str:
        """
        Converts a pynput key string to a PyAutoGUI library key string.
        """
        return self.key_map.get(button, button)
