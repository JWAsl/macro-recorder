"""
A mapping of pynput key codes -> pyautogui key codes.

This module provides a translation layer to ensure that keys recorded by pynput
can be correctly simulated by pyautogui.
"""

# utils/key_mappings.py

# A INCOMPLETE mapping from pynput key names to pyautogui key names.
key_map = {
    # Modifier Keys
    "Key.alt": "alt",
    "Key.alt_l": "altleft",
    "Key.alt_r": "altright",
    "Key.ctrl": "ctrl",
    "Key.ctrl_l": "ctrlleft",
    "Key.ctrl_r": "ctrlright",
    "Key.shift": "shift",
    "Key.shift_l": "shiftleft",
    "Key.shift_r": "shiftright",
    "Key.cmd": "win",
    "Key.cmd_l": "winleft",
    "Key.cmd_r": "winright",

    # Special Keys
    "Key.space": "space",
    "Key.enter": "enter",
    "Key.tab": "tab",
    "Key.backspace": "backspace",
    "Key.delete": "del",
    "Key.esc": "esc",
    "Key.caps_lock": "capslock",
    "Key.f1": "f1",
    "Key.f2": "f2",
    "Key.f3": "f3",
    "Key.f4": "f4",
    "Key.f5": "f5",
    "Key.f6": "f6",
    "Key.f7": "f7",
    "Key.f8": "f8",
    "Key.f9": "f9",
    "Key.f10": "f10",
    "Key.f11": "f11",
    "Key.f12": "f12",
    "Key.print_screen": "printscreen",
    "Key.scroll_lock": "scrolllock",
    "Key.pause": "pause",
    "Key.insert": "insert",
    "Key.home": "home",
    "Key.end": "end",
    "Key.page_up": "pageup",
    "Key.page_down": "pagedown",

    # Arrow Keys
    "Key.up": "up",
    "Key.down": "down",
    "Key.left": "left",
    "Key.right": "right",

    # Numpad Keys
    "Key.num_lock": "numlock",
    "Key.keypad_0": "num0",
    "Key.keypad_1": "num1",
    "Key.keypad_2": "num2",
    "Key.keypad_3": "num3",
    "Key.keypad_4": "num4",
    "Key.keypad_5": "num5",
    "Key.keypad_6": "num6",
    "Key.keypad_7": "num7",
    "Key.keypad_8": "num8",
    "Key.keypad_9": "num9",
    "Key.keypad_add": "+",
    "Key.keypad_subtract": "-",
    "Key.keypad_multiply": "*",
    "Key.keypad_divide": "/",
    "Key.keypad_decimal": ".",
    "Key.keypad_enter": "enter",

    'Key.space': 'space',
    'Key.tab': 'tab',
    'Key.enter': 'enter',
    'Key.esc': 'esc',
    'Key.backspace': 'backspace',
    'Key.delete': 'delete',
    'Key.home': 'home',
    'Key.end': 'end',
    'Key.page_up': 'pageup',
    'Key.page_down': 'pagedown',
    'Key.ctrl_l': 'ctrlleft',
    'Key.ctrl_r': 'ctrlright',
    'Key.alt_l': 'altleft',
    'Key.alt_r': 'altright',
    'Key.shift_l': 'shiftleft',
    'Key.shift_r': 'shiftright',

    # Add the specific mappings for the control characters recorded by pynput
    # for Ctrl+C and Ctrl+V.
    '\u0003': 'c',  # Maps Ctrl+C to 'c'
    '\u0016': 'v',  # Maps Ctrl+V to 'v'

    # You may also need to add a mapping for Ctrl+X if you use it.
    '\u0018': 'x',  # Maps Ctrl+X to 'x'

    # And other common keys that might be affected by modifier keys
    '\u0001': 'a',
}
