import time

from screen import Screen

screen = Screen()


def login(timeout: int = 30):
    """ Logs into the game. """
    start_time = time.perf_counter()

    while not screen.check_state("login_screen.png") and not screen.find_button("game_start.png"):
        if time.perf_counter() - start_time > timeout:
            print(f"Timed out during notifications after {timeout:.2f}s")
            break
        time.sleep(0.1)
        screen.update()
    else:
        print(f"At login screen (after {time.perf_counter() - start_time:.2f}s)")

    # Tap bottom area to exit notification screen.
    dimensions = screen.dimensions()
    screen.tap(dimensions[0] * 0.5, dimensions[1] * 0.9)

    # Find the start button
    screen.click_button("game_start.png")

login()
