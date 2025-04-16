from screen import Screen, StateNotReached, ActionNotPerformed
from log import logger


class OvermortalAPI:

    def __init__(self):
        self.screen = Screen()

    def login(self):
        """ Logs into the game. """
        logger.info("Starting API")

        try:
            state = self.screen.wait_for_any_state(["login_start_screen", "login_notification_screen"])
        except StateNotReached:
            logger.exception("Failed to get to login screen")
            exit(0)

        # Tap bottom area to exit notification screen if there.
        if state == 1:
            self.screen.tap(self.screen.dimensions[0] * 0.5, self.screen.dimensions[1] * 0.9)
            try:
                self.screen.wait_for_state("login_start_screen")
            except StateNotReached:
                logger.exception("Failed to clear login notifications")
                exit(0)

        # Find the start button
        try:
            self.screen.tap_button("game_start_button")
        except ActionNotPerformed:
            logger.exception("Failed to press the start button")

        logger.info("Started the game")


api = OvermortalAPI()
api.login()
