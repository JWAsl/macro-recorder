"""
Entry point for the Macro Recorder GUI application.

This module implements the MacroGUI controller using Tkinter, providing a 
interface for recording and replaying user inputs. 

Classes:
    MacroGUI: Threaded controller that manages the application state.
"""

import logging
import threading
from pathlib import Path
from time import sleep

import tkinter as tk
from tkinter import filedialog, messagebox, PhotoImage, simpledialog

from macros.recorder import MacroRecorder
from macros.playback import MacroPlayer
from utils.json_utils import save_file, open_file

logger = logging.getLogger("GUI")


class MacroGUI:
    """Tkinter GUI controller for macro recording and playback."""

    def __init__(self, master: tk.Tk):
        """
        Initializes all UI elements and layout.

        Args:
            master (tk.Tk): Tkinter root window.
        """
        self.master = master
        self.master.title("Macro Recorder")
        self.master.geometry("400x300")

        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_columnconfigure(1, weight=1)
        self.master.grid_rowconfigure(0, weight=1)

        self.master.protocol("WM_DELETE_WINDOW", self.shutdown)

        self.record_img = None
        self.play_img = None
        self.current_macro = None

        self.status_label = tk.Label(
            self.master, text="Idle", font=("Arial", 12))
        self.status_label.grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=10)

        self.buttons: list[tk.Button] = []

        self.set_up_widgets()

    def set_up_widgets(self) -> None:
        """Initializes and places main UI components (Record + Play buttons)."""
        self.record_img = self.load_image("record.png")
        self.play_img = self.load_image("play.png")

        record_button = tk.Button(
            self.master,
            image=self.record_img,
            text="Record",
            font=("Arial", 20),
            compound="top",
            command=self.start_recorder,
        )
        record_button.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        play_button = tk.Button(
            self.master,
            image=self.play_img,
            text="Play",
            font=("Arial", 20),
            compound="top",
            command=self.start_playback,
        )
        play_button.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self.buttons = [record_button, play_button]

    def load_image(self, filename: str) -> PhotoImage | None:
        """
        Loads a PhotoImage from the assets folder.

        Args:
            filename (str): Name of the image file.

        Returns:
            PhotoImage | None: Loaded image, or None if missing.
        """
        path = Path.cwd() / "assets" / filename
        if path.exists():
            return PhotoImage(file=str(path))

        logger.warning("Asset not found: %s", filename)
        return None

    def shutdown(self) -> None:
        """
        Handles window close event.

        Prompts the user for confirmation before closing the application.
        """
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.master.destroy()
            logger.info("Application closed successfully.")

    def update_status(self, message: str) -> None:
        """
        Updates the status label safely from any thread.

        Schedules the status update to run on the main Tkinter thread,
        ensuring thread safety and UI stability.

        Args:
            message (str): Status text to display.
        """
        self.master.after(0, lambda: self.status_label.config(text=message))

    def disable_buttons(self) -> None:
        """Disables the main UI buttons (Record & Play)."""
        for btn in self.buttons:
            btn.config(state=tk.DISABLED)

    def enable_buttons(self) -> None:
        """Enables the main UI buttons (Record & Play)."""
        for btn in self.buttons:
            btn.config(state=tk.NORMAL)

    def start_recorder(self) -> None:
        """Starts macro recording on a separate thread."""
        self.disable_buttons()
        threading.Thread(
            target=self.recorder, daemon=True).start()

    def recorder(self) -> None:
        """
        Captures user input events and saves the resulting macro.

        This runs in a background thread to keep the GUI responsive.
        """
        try:
            recorder = MacroRecorder(status=self.update_status)

            for i in range(3, 0, -1):
                self.update_status(f"Starting in {i}...")
                sleep(1)

            self.update_status("Recording...")
            recorder.start_recording()

            self.master.after(0, self.save_recording, recorder.events)

        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Recording failed due to an unexpected error")
            self.master.after(
                0, lambda: messagebox.showerror(
                    "Error", "Recording failed. Check logs for details.")
            )
        finally:
            self.master.after(0, self.enable_buttons)
            self.master.after(1500, lambda: self.update_status("Idle"))

    def save_recording(self, events: list[dict]) -> None:
        """
        Prompts user for a filename and writes macro data to disk.

        Args:
            events (list[dict]): Recorded macro events.
        """
        save_dir = Path.cwd() / "recordings"
        save_dir.mkdir(exist_ok=True)

        filename = simpledialog.askstring("Save Recording", "Enter filename:")
        if filename:
            if not filename.endswith(".json"):
                filename += ".json"

            filepath = save_dir / filename
            save_file(filepath, events)
            self.update_status(f"Saved: {filename}")
        else:
            logger.info("Save cancelled.")

    def start_playback(self) -> None:
        """Launches a file selection dialog and begins playback."""
        self.disable_buttons()

        filepath = filedialog.askopenfilename(
            title="Select macro file to play",
            initialdir=Path.cwd() / "recordings",
            filetypes=[("JSON Files", "*.json")],
            defaultextension=".json",
        )

        if filepath:
            threading.Thread(target=self.playback, args=(
                filepath,), daemon=True).start()
        else:
            logger.info("Playback cancelled.")
            self.enable_buttons()
            self.update_status("Idle")

    def playback(self, filepath: str) -> None:
        """
        Loads and executes a macro file.

        Args:
            filepath (str): Absolute path to a JSON macro file.
        """
        self.current_macro = Path(filepath).name

        def status(msg: str) -> None:
            label = f"{msg}: {self.current_macro}" if self.current_macro else msg
            self.update_status(label)

        try:
            data: list[dict] | None = open_file(filepath)
            if not data:
                raise ValueError("File is empty or invalid JSON")

            player = MacroPlayer(status=status)
            self.update_status(f"Loading: {self.current_macro}")

            for i in range(3, 0, -1):
                status(f"Starting in {i}")
                sleep(1)

            status("Playing")
            player.start_playback(data)

            if player.playback_thread and player.playback_thread.is_alive():
                player.playback_thread.join()

            status("Finished")
            logger.info("Played: %s", filepath)

        except ValueError as e:
            logger.error("Error loading macro file: %s", e)
            self.master.after(
                0, lambda: messagebox.showerror(
                    "Error", f"Failed to load macro: {e}")
            )
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Playback failed unexpectedly")
            self.master.after(
                0, lambda: messagebox.showerror(
                    "Error", "Playback failed. Check logs for details.")
            )
        finally:
            self.master.after(0, self.enable_buttons)
            self.master.after(1500, lambda: self.update_status("Idle"))
            self.current_macro = None


def set_up_gui() -> None:
    """Starts the Tkinter main application loop."""
    window = tk.Tk()
    MacroGUI(window)
    window.mainloop()
