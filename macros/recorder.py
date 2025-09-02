"""
Records mouse and keyboard events using the pynput library.

This module captures key presses, mouse clicks, and scroll events,
and saves them along with a timestamp relative to the start of recording.
"""

import threading
import logging

from time import time, perf_counter
from pynput import mouse, keyboard

from utils.countdown import countdown_timer

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format='%(message)s')


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
        - last_event_time: Track last event's time to get time delta
        - is_paused: A boolean flag to indicate if recording is currently paused.
        - pause_start_time: The timestamp when the last pause was initiated.
        - exit_event: A threading.Event to signal the main loop to terminate gracefully.
        """
        self.pressed_keys = set()
        self.saved_inputs = []
        self.last_event_time = None
        self.is_paused = False
        self.pause_start_time = None
        self.exit_event = threading.Event()

    def run_listeners(self) -> None:
        self.last_event_time = perf_counter()

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

        # Do not record event if paused, is an ignored key, or already being pressed.
        if self.is_paused or key in self.IGNORED_KEYS or key in self.pressed_keys:
            return

        self.pressed_keys.add(key)
        self.record_event(EventType.KEY_DOWN,
                          self.stringify_key(key),
                          pressed_keys=[self.stringify_key(key) for key in self.pressed_keys])

    def on_release(self, key) -> None:
        """
        Callback from the pynput listener on a key release event.
        Handles the exit key and records the keyup event.
        """

        # Do not record event if paused, is an ignored key, or the pause key.
        if self.is_paused or key in self.IGNORED_KEYS or key == self.PAUSE_KEY:
            return

        self.record_event(EventType.KEY_UP,
                          self.stringify_key(key),
                          pressed_keys=[self.stringify_key(key) for key in self.pressed_keys])

        if key in self.pressed_keys:
            self.pressed_keys.remove(key)

        if key == self.EXIT_KEY:
            # Set the event to signal the main thread to terminate.
            self.exit_event.set()

    def on_click(self, x, y, button, pressed) -> None:
        """Callback from the pynput listener on a mouse click event."""
        if self.is_paused:
            return
        if not pressed:
            self.record_event(
                EventType.CLICK, button, pos=(x, y))

    def on_scroll(self, x, y, dx, dy) -> None:
        """Callback from the pynput listener on a mouse scroll event."""
        if self.is_paused:
            return
        self.record_event(EventType.SCROLL,
                          'mouse_wheel', pos=(x, y), scroll_direction={'dx': dx, 'dy': dy})

    def record_event(self, event_type, button, **kwargs) -> None:
        """
        Creates an event dictionary and adds it to the saved inputs list.
        """
        now = perf_counter()
        # Calculate time elapsed since last recorded event.
        time_delta = now - self.last_event_time

        event_data = {
            'time_delta': time_delta,
            'type': event_type,
            'button': str(button),
            'pos': None,
            'scroll_direction': None,
            'pressed_keys': []
        }

        # Update with event-specific parameters (e.g., position, scroll direction).
        event_data.update(kwargs)
        self.saved_inputs.append(event_data)
        self.last_event_time = now

        log_message = (
            f"Event: {event_data['type']} | "
            f"Button: {event_data['button']} | "
            f"Time Delta: {event_data['time_delta']:.4f}s"
        )
        if event_data.get('pos'):
            log_message += f" | Position: {event_data['pos']}"
        if event_data.get('scroll_direction'):
            log_message += f" | Scroll: {event_data['scroll_direction']}"

        logger.debug(log_message)

    def toggle_pause(self) -> None:
        """
        Toggles the recording state between paused and resumed.
        """
        if not self.is_paused:
            self.pause_start_time = perf_counter()
            self.is_paused = True
            logging.info("[Paused]")
        else:
            paused_time = perf_counter() - self.pause_start_time
            # Adjusts last_event_time to correct for pause duration.
            # Ensures time_delta for the next recorded event accurately reflects the time since the last active event
            # and not the time since the pause began.
            self.last_event_time += paused_time
            self.pause_start_time = None
            self.is_paused = False
            logging.info("[Resumed]")

    def cleanup(self) -> None:
        """
        Records key-up events for all keys that are still marked as pressed.
        Ensures a clean and complete macro file on exit with no phantom key down events.
        """
        keys_to_release = list(self.pressed_keys)
        for key in keys_to_release:
            self.on_release(key)

    def record(self) -> None:
        countdown_timer()
        self.run_listeners()
