# Macro Recorder

A cross-platform desktop automation tool to record and replay user actions. Built using Python and provides a straightforward GUI for automating repetitive tasks.

---

## Features

- **Captures and saves keyboard and mouse events.**
- **Replays the recorded events as the user performed them to accurately automate repetitive tasks.**
- **Simple GUI.**
- **Pause key allows user to pause during a recording or during playback.**
- **Ignore keys list**

---

## Requirements

- Python 3.8+
- Install dependencies:
  ```bash
  pip install pynput pyautogui keyboard
  ```

---

## Usage

    Run main.py. You will see a simple GUI with a record and play button.

    Record: Click the "Record" button and a countdown will begin. After the countdown is over you can then perform the actions you want to capture. Press the 'ESC' key when you're finished. When the recording finishes, you will be prompted to save your macro to a .json file in the recordings/ directory.

    Play: The recordings/ directory will be opened and you'll be asked to select a .json file to replay. Once a macro is loaded, a countdown will begin, and the recorded actions will be replayed.

    Pause: At any time during the recording or playback you can press the 'Pause' key to pause. Press the 'Pause' key again to resume.

    Exiting playback immediately: If you move your cursor to the top left of your monitor (0,0) PyAutoGUI immediately raises a pyautogui.FailSafeException. This exception halts the execution of the PyAutoGUI script.

    Inside of recorder.py are the following:
    PAUSE_KEY
    EXIT_KEY
    IGNORED_KEYS

    These can be edited with pynput key codes

    Inside of playback.py is the following:
    PAUSE_KEY

    This can be edited with keyboard key codes
---

## Limitations

Since key's are recorded and played back as individual keys, key combinations will not work (Ex. CTRL+S to save)

# License

This project is licensed under the MIT License. Feel free to use, modify, and distribute it as per the license terms.
