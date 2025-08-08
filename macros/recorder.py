"""
Records mouse and keyboard events using the pynput library.

This module captures key presses, mouse clicks, and scroll events,
and saves them along with a timestamp relative to the start of recording.
"""

import threading
from time import time
from pynput import mouse, keyboard

from utils.countdown import countdown_timer


class EventType:
    CLICK = 'click'
    KEY_DOWN = 'keyDown'
    KEY_UP = 'keyUp'
    SCROLL = 'scroll'


class MacroRecorder:
    """
    Records mouse and keyboard events with pause and resume support.

    The recording is paused, resumed, and ended via hotkeys.
    """
    # Use pynput library key codes
    PAUSE_KEY = keyboard.Key.pause
    EXIT_KEY = keyboard.Key.esc
    # A list of keys to be ignored during recording
    IGNORED_KEYS = []

    def __init__(self):
        """
        Initializes the recorder's state variables.

        - pressed_keys: Tracks currently held down keys.
        - saved_inputs: A list to store all recorded events before saving to file.
        - start_time: The timestamp when recording officially began.
        - is_paused: A boolean flag to indicate if recording is currently paused.
        - pause_start_time: The timestamp when the last pause was initiated.
        - total_pause_time: The cumulative time spent in the paused state.
        - exit_event: A threading.Event to signal the main loop to terminate gracefully.
        """
        self.pressed_keys = set()
        self.saved_inputs = []
        self.start_time = None
        self.is_paused = False
        self.pause_start_time = None
        self.total_pause_time = 0.0
        self.exit_event = threading.Event()

    def elapsed_time(self) -> float:
        """
        Calculates the elapsed time since recording started,
        excluding any periods of pausing.

        Returns:
            float: The total active recording time in seconds.
        """
        now = time()
        if self.is_paused:
            # If paused, return the time up to the moment the pause started.
            return self.pause_start_time - self.start_time - self.total_pause_time
        else:
            # If not paused, return the total time minus the paused time.
            return now - self.start_time - self.total_pause_time

    def run_listeners(self) -> None:
        self.start_time = time()
        self.mouse_listener = mouse.Listener(
            on_click=self.on_click,
            on_scroll=self.on_scroll
        )
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )

        self.mouse_listener.start()
        self.keyboard_listener.start()

        # The main thread now waits here until the exit event is set.
        self.exit_event.wait()

        # Cleanup and stop listeners after the event is set.
        self.cleanup()

        self.keyboard_listener.stop()
        self.mouse_listener.stop()

    def stringify_key(self, key) -> str:
        """
        Converts a pynput key object into a string representation.
        Handles both character keys and special keys.

        Args:
            key: The key object from pynput.

        Returns:
            A string representation of the key.
        """
        try:
            # For character keys (e.g., 'a', 'b')
            return key.char
        except AttributeError:
            # For special keys (e.g., Key.esc, Key.shift)
            return str(key)

    def on_press(self, key) -> None:
        """
        Callback from the pynput listener on a key press event.
        Handles the pause key and records the keydown event.
        """
        if key == self.PAUSE_KEY:
            self.toggle_pause()
            return

        if self.is_paused or key in self.IGNORED_KEYS or key in self.pressed_keys:
            return

        self.pressed_keys.add(key)
        self.record_event(EventType.KEY_DOWN,
                          self.elapsed_time(), self.stringify_key(key))

    def on_release(self, key) -> None:
        """
        Callback from the pynput listener on a key release event.
        Handles the exit key and records the keyup event.
        """
        if self.is_paused or key in self.IGNORED_KEYS or key == self.PAUSE_KEY:
            return

        if key in self.pressed_keys:
            self.pressed_keys.remove(key)

        self.record_event(EventType.KEY_UP, self.elapsed_time(),
                          self.stringify_key(key))

        if key == self.EXIT_KEY:
            # Set the event to signal the main thread to terminate
            self.exit_event.set()

    def on_click(self, x, y, button, pressed) -> None:
        """Callback from the pynput listener on a mouse click event."""
        if self.is_paused:
            return
        if not pressed:
            self.record_event(
                EventType.CLICK, self.elapsed_time(), button, pos=(x, y))

    def on_scroll(self, x, y, dx, dy) -> None:
        """Callback from the pynput listener on a mouse scroll event."""
        if self.is_paused:
            return
        self.record_event(EventType.SCROLL, self.elapsed_time(),
                          'mouse_wheel', pos=(x, y), scroll_direction={'dx': dx, 'dy': dy})

    def record_event(self, event_type, event_time, button, **kwargs) -> None:
        """
        Creates an event dictionary and adds it to the saved inputs list.
        """
        event_data = {
            'time': event_time,
            'type': event_type,
            'button': str(button),
            'pos': None,
            'scroll_direction': None
        }

        # Update with event-specific parameters (e.g., position, scroll direction)
        event_data.update(kwargs)
        self.saved_inputs.append(event_data)
        self.print_event(event_data)

    def print_event(self, event_data) -> None:
        """
        Prints a summary of a recorded event to the console for debugging.
        """
        print(f"Event: {event_data['type']}")
        print(f"Button: {event_data['button']}")
        if event_data.get('pos'):
            print(f"Position: {event_data['pos']}")
        if event_data.get('scroll_direction'):
            print(f"Scroll: {event_data['scroll_direction']}")
        print(f"Time: {event_data['time']:.4f}\n")

    def toggle_pause(self) -> None:
        """
        Toggles the recording state between paused and resumed.
        """
        if not self.is_paused:
            self.pause_start_time = time()
            self.is_paused = True
            print("[Paused]")
        else:
            # Calculate and add the duration of the pause to the total
            paused_time = time() - self.pause_start_time
            self.total_pause_time += paused_time
            self.pause_start_time = None
            self.is_paused = False
            print("[Resumed]")

    def cleanup(self) -> None:
        """
        Records key-up events for all keys that are still marked as pressed.
        This ensures a clean and complete macro file on exit with no phantom key down events.
        """
        # Create a list from the set to iterate over, as the set will be modified
        keys_to_release = list(self.pressed_keys)
        for key in keys_to_release:
            # Call on_release for each key, which will remove it from the set
            # and record the key-up event.
            self.on_release(key)

    def record(self) -> None:
        """
        Starts a countdown and then begins the recording process.
        """
        countdown_timer()
        self.run_listeners()
