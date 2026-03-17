
"""
Main entry point for the app.

Sets up logging and launches the GUI.
"""

import logging
from gui import set_up_gui


def main():
    """
    Initializes logging and the app's GUI.
    """
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)s - %(name)s - %(message)s')
    set_up_gui()


if __name__ == "__main__":
    main()
