import logging
from gui import setUpGUI


def main():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)s - %(name)s - %(message)s')
    setUpGUI()


if __name__ == "__main__":
    main()
