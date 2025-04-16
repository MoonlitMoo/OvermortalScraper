from screen import Screen

screen = Screen()


class StateNotReached(Exception):
    pass


class ActionNotPerformed(Exception):
    pass


class OvermortalAPI:

    def login(self):
        """ Logs into the game. """
        found, state = screen.wait_for_any_state(["login_start_screen", "login_notification_screen"])

        if not found:
            raise StateNotReached("Failed to get to login screen")

        # Tap bottom area to exit notification screen if there.
        if state == 1:
            screen.tap(screen.dimensions[0] * 0.5, screen.dimensions[1] * 0.9)
            found = screen.wait_for_state("login_start_screen")
            if not found:
                raise StateNotReached("Failed to clear login notifications")

        # Find the start button
        if not screen.tap_button("game_start_button"):
            raise ActionNotPerformed("Failed to press the start button")

        print("STARTED THE GAME")


api = OvermortalAPI()
api.login()
