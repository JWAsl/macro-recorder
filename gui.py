"""
Manages the graphical user interface for the Macro Recorder application.

This module sets up the main window, buttons, and handles user interactions
like starting recording and playback. It uses multithreading to
keep the GUI responsive during long-running tasks.
"""
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog, PhotoImage
from pathlib import Path
import threading

from macros.recorder import MacroRecorder
from macros.playback import MacroPlayer
from utils.json_utils import save_file, open_file
from utils.countdown import countdown_timer


class MacroRecorderGUI:
    """
    A class to create and manage the Tkinter-based GUI for the macro recorder.
    """

    def __init__(self, master):
        """
        Initializes the GUI and sets up the main window.

        Args:
            master: The root Tkinter window.
        """
        self.master = master
        self.master.title("Macro Recorder")
        self.master.geometry("400x300")
        self.master.resizable(False, False)

        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_columnconfigure(1, weight=1)
        self.master.grid_rowconfigure(0, weight=1)

        # Handle window closing event
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.record_img = None
        self.play_img = None

        self.setup_widgets()

    def on_closing(self) -> None:
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.master.destroy()
            print("Application closed successfully.")

    def setup_widgets(self) -> None:
        assets_path = Path.cwd() / "assets"
        try:
            self.record_img = PhotoImage(file=str(assets_path / "record.png"))
            self.play_img = PhotoImage(file=str(assets_path / "play.png"))

            record_button = tk.Button(
                self.master, image=self.record_img, command=self.start_record_thread)
            record_button.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

            play_button = tk.Button(
                self.master, image=self.play_img, command=self.start_play_thread)
            play_button.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        except tk.TclError:
            # Fallback for when image files are not found
            print("Warning: Image assets not found. Using text labels instead.")
            record_button = tk.Button(
                self.master, text="Record", font=("Arial", 20), command=self.start_record_thread)
            play_button = tk.Button(
                self.master, text="Play", font=("Arial", 20), command=self.start_play_thread)
            record_button.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
            play_button.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

    def start_record_thread(self) -> None:
        """
        Starts a new thread to run the recording process.
        The save dialog will be triggered on the main thread after recording finishes.
        """
        thread = threading.Thread(
            target=self._record_and_save, daemon=True)
        thread.start()

    def _record_and_save(self) -> None:
        """
        Runs recording logic in a separate thread.
        Once recording is complete, it schedules a function to handle saving on the main thread.
        """
        manager = MacroRecorder()
        manager.record()
        print(f"Recording Duration: {manager.elapsed_time()} seconds")

        self.master.after(0, self._ask_and_save_recording,
                          manager.saved_inputs)

    def _ask_and_save_recording(self, saved_inputs) -> None:
        """
        Displays a simpledialog to ask the user for a filename and saves the recording.
        This function must be called from the main Tkinter thread.

        Args:
            saved_inputs: The list of recorded events to be saved.
        """
        filename = simpledialog.askstring(
            "Save Recording", "Enter filename to save (without .json):")
        if filename:
            if not filename.endswith(".json"):
                filename += ".json"
            save_file(filename, saved_inputs)
        else:
            print("Save cancelled.")

    def start_play_thread(self) -> None:
        """
        Displays a file dialog to select a recording, then starts a new thread to play it back.
        The file dialog must run on the main thread.
        """
        filepath = filedialog.askopenfilename(
            title="Select macro file to play",
            initialdir=Path.cwd() / "recordings",
            filetypes=[("JSON Files", "*.json")],
            defaultextension=".json"
        )

        if filepath:
            thread = threading.Thread(
                target=self._play_macro, args=(filepath,), daemon=True)
            thread.start()
        else:
            print("Playback cancelled.")

    def _play_macro(self, filepath) -> None:
        """
        Internal method to run the playback logic. This runs in a separate thread.

        Args:
            filepath: The path to the macro file to play.
        """
        manager = MacroPlayer()
        data = open_file(filepath)
        if data:
            countdown_timer()
            manager.play_actions(data)
            print(f"Played: {filepath}")


def setUpGUI() -> None:
    window = tk.Tk()
    app = MacroRecorderGUI(window)
    window.mainloop()
