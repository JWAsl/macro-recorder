"""
This module captures and records keyboard and mouse inputs in real time using
the pynput library. Recorded events support pause/resume and can be saved
for later playback.

Classes:
    EventType: Constants for supported input event types.
    MouseState: Keeps track of the mouse's current position and timestamps.
    KeyboardState: Keeps track of all current keys being pressed. 
    MacroRecorder: Engine for capturing, buffering, and processing inputs during
        a recording session.
"""

import logging
import threading
from collections import deque
from enum import Enum
from time import perf_counter, sleep
from typing import Any, Callable, Dict, Optional

from pynput import keyboard, mouse

logger = logging.getLogger("recorder")


class EventType(Enum):
    """Constants representing the different types of input events."""

    KEY_DOWN = "keyDown"
    KEY_UP = "keyUp"
    MOUSE_DOWN = "mouseDown"
    MOUSE_UP = "mouseUp"
    MOUSE_MOVE = "mouseMove"
    SCROLL = "scroll"


class MouseState:
    """Tracks mouse position and timing for move events."""

    def __init__(self):
        self.position = None
        self.curr_timestamp = 0.0
        self.last_timestamp = 0.0


class KeyboardState:
    """Tracks currently pressed keys."""

    def __init__(self):
        self.pressed_keys = set()


class MacroRecorder:
    """
    Captures keyboard and mouse input events in real time.

    Input listeners run on background threads and push raw events into
    a synchronized queue. A separate thread consumes these events, normalizes 
    timestamps, and appends them to the recorded event list.

    Pause/resume is supported with timestamp adjustment to ensure accurate 
    playback timing.

    Recording continues until the EXIT_KEY is pressed.
    """

    # Use pynput key codes
    PAUSE_KEY = keyboard.Key.pause
    EXIT_KEY = keyboard.Key.esc
    IGNORED_KEYS = []
    # Polling rates for mouse movement recording, measured in seconds.
    # Default minimum interval between recorded moves (50 events/second).
    BASE_MOUSE_MOVE_POLL = 0.02
    # Fast interval used during rapid motion (100 events/second).
    HIGH_MOUSE_MOVE_POLL = 0.01
    # Time delta threshold: if movement is faster than this, HIGH_MOUSE_MOVE_POLL is used.
    RATE_THRESHOLD = 0.03

    def __init__(self, status: Optional[Callable[[str], None]]) -> None:
        """
        Initializes a MacroRecorder instance.

        Args:
            status (Callable[[str], None] | None): Callback used to update GUI 
                status labels. Either "Paused" or "Recording".
        """
        self.is_paused = False
        # Timestamp used as the reference baseline for computing event timing.
        self.recording_start_time = None
        # Timestamp when the current pause began.
        self.pause_start_time = None

        self.mouse = MouseState()
        self.keyboard = KeyboardState()
        self.events = []

        self.exit = threading.Event()
        self.lock = threading.Lock()
        self.event_queue = deque()

        self.processor_thread = None
        self.mouse_listener = None
        self.keyboard_listener = None

        self.status = status

    def start_recording(self) -> None:
        """
        Starts the mouse and keyboard listeners and begins event processing.

        This method blocks until the exit key (ESC by default) is pressed. Afterward,
        listeners and the processor thread are properly shut down.
        """
        session_start_time = perf_counter()
        logger.info("Recording started")

        self.processor_thread = threading.Thread(
            target=self.process_events,
            daemon=True
        )
        self.processor_thread.start()

        self.mouse_listener = mouse.Listener(
            on_click=self.on_click,
            on_scroll=self.on_scroll,
            on_move=self.on_move,
        )
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release,
        )

        self.mouse_listener.start()
        self.keyboard_listener.start()

        # Block until exit key is pressed
        self.exit.wait()
        self.cleanup()

        logger.info("Recording finished")
        total = perf_counter() - session_start_time
        logger.info("Total duration: %.2fs", total)

    def toggle_pause(self) -> None:
        """
        Toggles the paused state of the recorder.

        When resuming from a pause, the internal timestamps are adjusted to
        ensure consistent event timing.
        """
        if not self.is_paused:
            self.is_paused = True
            self.pause_start_time = perf_counter()
            if self.status:
                self.status("Paused")
        else:
            paused_duration = perf_counter() - self.pause_start_time
            if self.recording_start_time is not None:
                self.recording_start_time += paused_duration

            self.pause_start_time = None
            self.is_paused = False
            if self.status:
                self.status("Recording")

    def normalize_key(self, key: keyboard.Key | keyboard.KeyCode) -> str:
        """
        Converts a keyboard key event into a normalized string representation.

        Args:
            key (pynput.keyboard.Key | pynput.keyboard.KeyCode): The key pressed.

        Returns:
            str: A normalized string representation of the key
        """
        if isinstance(key, keyboard.KeyCode):
            return key.char.lower() if key.char else str(key)
        return str(key)

    def on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """
        Handles keyDown key press events.

        Adds the event to the recorder's queue unless the recorder is paused
        or the key is in the ignored keys list. Also checks the PAUSE_KEY 
        to toggle recording.

        Args:
            key (pynput.keyboard.Key | pynput.keyboard.KeyCode): The key pressed.
        """
        if key == self.PAUSE_KEY:
            self.toggle_pause()
            return

        key_str = self.normalize_key(key)

        if (
            key in self.IGNORED_KEYS
            or key_str in self.keyboard.pressed_keys
            or self.is_paused
        ):
            return

        self.keyboard.pressed_keys.add(key_str)

        event = {
            "timestamp": perf_counter(),
            "event_type": EventType.KEY_DOWN,
            "button": key_str,
        }

        with self.lock:
            self.event_queue.append(event)

    def on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """
        Handles a key up event and adds it to queue unless paused or ignored.

        Pressing the ESC key triggers the recording shutdown via exit.

        Args:
            key (pynput.keyboard.Key | pynput.keyboard.KeyCode): The key released.
        """
        key_str = self.normalize_key(key)

        if (
            key in self.IGNORED_KEYS
            or self.is_paused
            or key == self.PAUSE_KEY
        ):
            return

        self.keyboard.pressed_keys.discard(key_str)

        event = {
            "timestamp": perf_counter(),
            "event_type": EventType.KEY_UP,
            "button": key_str,
        }

        with self.lock:
            self.event_queue.append(event)

        if key == self.EXIT_KEY:
            self.exit.set()

    def on_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        """
        Handles mouse click events and adds it to queue unless paused.

        Args:
            x (int): X-coordinate of the mouse cursor.
            y (int): Y-coordinate of the mouse cursor.
            button (pynput.mouse.Button): Mouse button pressed/released.
            pressed (bool): True if pressed (MOUSE_DOWN), False if released (MOUSE_UP).
        """
        if self.is_paused:
            return

        ev_type = EventType.MOUSE_DOWN if pressed else EventType.MOUSE_UP

        event = {
            "timestamp": perf_counter(),
            "event_type": ev_type,
            "button": str(button),
            "pos": (x, y),
        }

        with self.lock:
            self.event_queue.append(event)

    def on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        """
        Handles mouse scroll events and adds it to queue unless paused.

        Args:
            x (int): X-coordinate of the cursor.
            y (int): Y-coordinate of the cursor.
            dx (int): Horizontal scroll amount.
            dy (int): Vertical scroll amount.
        """
        if self.is_paused:
            return

        event = {
            "timestamp": perf_counter(),
            "event_type": EventType.SCROLL,
            "button": "mouse_wheel",
            "pos": (x, y),
            "scroll_direction": {"dx": dx, "dy": dy},
        }

        with self.lock:
            self.event_queue.append(event)

    def on_move(self, x: int, y: int) -> None:
        """
        Handles mouse movement events and adds it to the queue unless paused.

        Movement events are rate-limited based on time since the last recorded event.

        Args:
            x (int): Current mouse X-coordinate.
            y (int): Current mouse Y-coordinate.
        """
        now = perf_counter()
        self.mouse.position = (x, y)
        self.mouse.curr_timestamp = now

        dt = now - self.mouse.last_timestamp

        if dt < self.RATE_THRESHOLD:
            poll = self.HIGH_MOUSE_MOVE_POLL
        else:
            poll = self.BASE_MOUSE_MOVE_POLL

        if now - self.mouse.last_timestamp >= poll and not self.is_paused:
            event = {
                "timestamp": now,
                "event_type": EventType.MOUSE_MOVE,
                "button": "mouse_move",
                "pos": self.mouse.position,
            }
            with self.lock:
                self.event_queue.append(event)
            self.mouse.last_timestamp = now

    def process_events(self) -> None:
        """
        Background thread that processes events from the queue.

        Runs separately from the input listeners and handles events safely in batches.
        """
        while not self.exit.is_set() or self.event_queue:
            batch = []

            with self.lock:
                while self.event_queue:
                    batch.append(self.event_queue.popleft())

            for raw_event in batch:
                try:
                    self.record_event(raw_event)
                except (KeyError, TypeError) as e:
                    logger.error("Error processing event: %s", e)

            sleep(0.002)

    def record_event(self, event: Dict[str, Any]) -> None:
        """
        Saves the event recorded by listeners to the final events list.

        Calculates elapsed time and time delta between events.

        Args:
            event (dict): Event captured by listeners, containing at least 
                'timestamp' and 'event_type'.
        """
        timestamp = event["timestamp"]
        event_type = event.get("event_type")
        button = event.get("button")
        pos = event.get("pos")
        scroll_direction = event.get("scroll_direction")

        if self.recording_start_time is None:
            self.recording_start_time = timestamp

        elapsed_time = timestamp - self.recording_start_time
        prev_elapsed = self.events[-1]["elapsed_time"] if self.events else 0
        delta = elapsed_time - prev_elapsed

        event_struct = {
            "elapsed_time": elapsed_time,
            "time_delta": delta,
            "type": event_type.value,
            "button": str(button),
            "pos": pos,
            "scroll_direction": scroll_direction,
        }

        self.events.append(event_struct)

        logger.debug(
            "%-10s %-12s delta_t=%.4f s %s",
            event_type.value,
            button,
            delta,
            event_struct.get('pos', '')
        )

    def cleanup(self) -> None:
        """
        Records the last mouse position, records KeyUp events for any currently 
        pressed keys, and shuts down the mouse and keyboard listeners.
        """
        if self.mouse.position:
            event = {
                "timestamp": perf_counter(),
                "event_type": EventType.MOUSE_MOVE,
                "button": "mouse_move",
                "pos": self.mouse.position,
            }
            with self.lock:
                self.event_queue.append(event)

        for key in list(self.keyboard.pressed_keys):
            key_str = self.normalize_key(key)
            event = {
                "timestamp": perf_counter(),
                "event_type": EventType.KEY_UP,
                "button": key_str,
            }
            with self.lock:
                self.event_queue.append(event)

        self.keyboard.pressed_keys.clear()

        try:
            if self.mouse_listener and self.mouse_listener.running:
                self.mouse_listener.stop()
            if self.keyboard_listener and self.keyboard_listener.running:
                self.keyboard_listener.stop()
        except RuntimeError as e:
            logger.warning("Listener stop failed: %s", e)
