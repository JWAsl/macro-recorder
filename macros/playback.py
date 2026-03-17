"""
This module replays recorded keyboard and mouse events using pyautogui with precise 
timing and pause/resume support. 

Classes:
    MacroPlayer: Engine for executing recorded events with high temporal accuracy.
"""

import logging
import queue
import threading
import time
from typing import Callable, Dict, List, Optional, Any

import keyboard
import pyautogui

from utils.mappings import key_map, mouse_button_map

logger = logging.getLogger("playback")


class MacroPlayer:
    """
    Executes recorded keyboard and mouse inputs.

    Runs input listeners on background threads and processes events
    through a synchronized queue to ensure thread-safe recording.

    Supports pause/resume with timestamp correction so recorded
    event timing remains consistent across pauses.
    """

    PAUSE_KEY = "pause"
    SCROLL_MULTIPLIER = 120
    MIN_DELAY_THRESHOLD = 0.005
    PAUSE_COOLDOWN = 3  # seconds to ignore pause/resume

    def __init__(self, status: Optional[Callable[[str], None]] = None) -> None:
        """
        Initialize the MacroPlayer engine.

        Args:
            status (Callable[[str], None] | None): Optional callback used to update GUI 
                status (e.g., passing "Playing" or "Paused").
        """
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.0

        self.action_queue = queue.Queue()
        self.pause_event = threading.Event()
        self.pause_event.set()

        self.playback_thread = None
        self.total_paused_duration = 0.0
        self.pause_start_time = None
        self.last_pause_toggle = None

        self.pressed_keys = set()
        self.pressed_mouse_buttons = {}

        self.status = status

        self.handlers = {
            "keyDown": self.handle_key,
            "keyUp": self.handle_key,
            "mouseDown": self.handle_mouse,
            "mouseUp": self.handle_mouse,
            "mouseMove": self.handle_mouse_move,
            "scroll": self.handle_scroll,
        }

    def start_playback(self, actions: List[Dict[str, Any]]) -> None:
        """
        Start playback of recorded macro actions.

        Args:
            actions: List of recorded events.
        """
        self.start_pause_listener()
        self.load_event(actions)

        self.playback_thread = threading.Thread(target=self.playback_loop)
        self.playback_thread.start()

    def start_pause_listener(self) -> None:
        """Register hotkey used to pause and resume playback."""
        keyboard.add_hotkey(self.PAUSE_KEY, self.toggle_pause, suppress=True)

    def toggle_pause(self) -> None:
        """
        Toggle the playback pause state.

        A cooldown is in place to prevent accidentally resuming immediately. 
        Paused time is tracked and removed from playback timing (drift correction) 
        to maintain accurate timing relative to the recorded macro.
        """
        now = time.perf_counter()
        if self.last_pause_toggle and now - self.last_pause_toggle < self.PAUSE_COOLDOWN:
            return
        self.last_pause_toggle = now

        # Pause playback
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_start_time = now
            logger.info(
                "[Playback Paused. Can not resume for at least 3 seconds.]")
            if self.status:
                self.status("Paused")
        else:
            # Resume playback
            paused_duration = now - self.pause_start_time
            self.total_paused_duration += paused_duration
            self.pause_event.set()
            self.pause_start_time = None
            logger.info("[Playback Resumed] (paused {%.3f}s)", paused_duration)
            if self.status:
                self.status("Playing")

    def load_event(self, actions: List[Dict[str, Any]]) -> None:
        """
        Enqueue actions into the playback queue.

        Args:
            actions: List of recorded events.
        """
        for action in actions:
            self.action_queue.put(action)

    def playback_loop(self) -> None:
        """
        Consumes and executes recorded inputs.

        Implements drift correction by calculating the cumulative time delay to
        ensure accurate timing relative to the recorded macro's start. Handles 
        interruptions and ensures input states are cleaned up after playback ends.
        """
        start_time = time.perf_counter()
        elapsed = 0.0

        while not self.action_queue.empty():
            action = self.action_queue.get()
            self.pause_event.wait()

            time_delta = max(action.get("time_delta", 0),
                             self.MIN_DELAY_THRESHOLD)

            elapsed += time_delta
            target_time = start_time + elapsed + self.total_paused_duration

            while True:
                now = time.perf_counter()
                remaining = target_time - now
                if remaining <= 0:
                    break
                time.sleep(min(remaining, 0.001))

            actual_time = time.perf_counter()
            error = actual_time - target_time
            logger.debug("Timing delta: %+0.6f s (%+.3f ms)",
                         error, error * 1000)

            try:
                self.execute_action(action)
            except pyautogui.FailSafeException:
                logger.warning(
                    "PyAutoGUI fail-safe triggered. Stopping playback.")
                break
            except (OSError, RuntimeError, ValueError, TypeError):
                logger.exception("Error during %s", action['type'])

        self.cleanup()

        total_duration = time.perf_counter() - start_time
        logger.info("Recorded macro duration: {%.3f}s", elapsed)
        logger.info("Actual playback duration: {%.3f}s", total_duration)
        logger.info(
            "Total pause duration: {%.3f}s", self.total_paused_duration)
        logger.info("Drift: {%.3f}s", total_duration -
                    elapsed - self.total_paused_duration)

    def execute_action(self, action: Dict[str, Any]) -> None:
        """
        Matches event to its appropriate handler.

        Args:
            action: The event dictionary containing the event's recorded 
            details (type, button, pos, etc.).
        """
        handler = self.handlers.get(action["type"])
        if handler:
            handler(action)
        else:
            logger.warning("No handler for action type: %s['type']", action)

    def handle_key(self, action: Dict[str, Any]) -> None:
        """
        Handle keyDown and keyUp events.

        Args:
            action: The dictionary containing the event's recorded details.
        """
        key = key_map.get(action["button"], action["button"])
        if action["type"] == "keyDown" and key not in self.pressed_keys:
            pyautogui.keyDown(key)
            self.pressed_keys.add(key)
            logger.debug("Key down: {%s}", key)
        elif action["type"] == "keyUp" and key in self.pressed_keys:
            pyautogui.keyUp(key)
            self.pressed_keys.remove(key)
            logger.debug("Key up: {%s}", key)

    def handle_mouse(self, action: Dict[str, Any]) -> None:
        """
        Handle mouseDown and mouseUp events.

        Args:
            action: The dictionary containing the event's recorded details.
        """
        button = mouse_button_map.get(
            action.get("button", "Button.left"), "left")
        pos = action.get("pos", pyautogui.position())
        pyautogui.moveTo(*pos, duration=0)

        if action["type"] == "mouseDown" and button not in self.pressed_mouse_buttons:
            pyautogui.mouseDown(button=button)
            self.pressed_mouse_buttons[button] = pos
            logger.debug("Mouse down: {%s} at {%s}", button, pos)
        elif action["type"] == "mouseUp" and button in self.pressed_mouse_buttons:
            pyautogui.mouseUp(button=button)
            self.pressed_mouse_buttons.pop(button)
            logger.debug("Mouse up: {%s} at {%s}", button, pos)

    def handle_mouse_move(self, action: Dict[str, Any]) -> None:
        """
        Handle mouseMove events.

        Suppresses redundant movement calls if the cursor is within a 2-pixel 
        threshold of the target to optimize system overhead.

        Args:
            action: The dictionary containing the event's recorded details.
        """
        pos = action.get("pos")
        if not pos:
            return

        current_pos = pyautogui.position()
        if abs(current_pos[0] - pos[0]) < 2 and abs(current_pos[1] - pos[1]) < 2:
            return

        pyautogui.moveTo(*pos, duration=0)
        logger.debug("Mouse move: %s", pos)

    def handle_scroll(self, action: Dict[str, Any]) -> None:
        """
        Handle scroll events.

        Applies a SCROLL_MULTIPLIER to vertical/horizontal scrolls to match the
        user's scroll speed.

        Args:
            action: The dictionary containing the event's recorded details.
        """
        if action.get("pos"):
            pyautogui.moveTo(action["pos"][0], action["pos"][1], duration=0)

        dx = action.get("scroll_direction", {}).get("dx", 0)
        dy = action.get("scroll_direction", {}).get("dy", 0)

        if dy:
            pyautogui.scroll(int(dy * self.SCROLL_MULTIPLIER))
        if dx:
            pyautogui.hscroll(int(dx * self.SCROLL_MULTIPLIER))

        logger.debug("Scroll: dx=%s, dy=%s", dx, dy)

    def cleanup(self) -> None:
        """
        Release any pressed keys, mouse buttons, and then removes the pause hotkey.

        Ensures that no keyDown/mouse button presses remain active without 
        a corresponding keyUp/mouse button release when playback ends or is stopped.
        """
        for key in list(self.pressed_keys):
            try:
                pyautogui.keyUp(key)
            except (pyautogui.FailSafeException, OSError, RuntimeError):
                pass
        self.pressed_keys.clear()

        for button in list(self.pressed_mouse_buttons.keys()):
            try:
                pyautogui.mouseUp(button=button)
            except (pyautogui.FailSafeException, OSError, RuntimeError):
                pass
        self.pressed_mouse_buttons.clear()

        try:
            keyboard.remove_hotkey(self.PAUSE_KEY)
        except KeyError:
            pass
