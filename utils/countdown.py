from time import sleep


def countdown_timer():
    print("Starting in . . . ", end="", flush=True)
    for i in range(3, 0, -1):
        print(f"{i} . . . ", end=" ", flush=True)
        sleep(1)
    print("\nGo \n")
