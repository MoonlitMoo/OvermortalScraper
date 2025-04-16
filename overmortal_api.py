import time
from datetime import datetime
import shutil

from log import logger
from locations import HomeLocation, TownLocation
from screen import Screen, StateNotReached, ActionNotPerformed


class OvermortalAPI:

    def __init__(self):
        self.screen = Screen()

    def debug_screencap(self, debug_name: str):
        timestamp = datetime.now().strftime("%Y%m%d-%H-%M-%S")
        shutil.copy(self.screen.CURRENT_SCREEN, f"screencaps/{debug_name}_{timestamp}.png")

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

    def go_to_home_location(self, location: HomeLocation):
        """
        Navigates to a specified location from the home screen.

        This method ensures the app is on the home screen by attempting to detect the
        home screen state. If not detected, it tries to navigate back up to five times.
        Once the home screen is confirmed, it taps the button corresponding to the given
        location.

        Parameters
        ----------
        location : HomeLocation

        Raises
        ------
        Exception
            If the method fails to reach the home screen after multiple attempts,
            it may raise an exception from `wait_for_state` or fail to navigate as expected.
        """
        _iter = 0
        on_home_screen = False
        # Make sure we are on the home screen before attempting to navigate.
        while _iter < 5 and not on_home_screen:
            _iter += 1
            try:
                on_home_screen = self.screen.wait_for_state("locations/home", timeout=1)
            except StateNotReached as e:
                # Try to press the back button up to 5 times
                logger.debug(f"Not on home screen while trying to go to home location, attempting back button (iter {_iter})")
                if _iter < 5:
                    self.screen.back()
                else:
                    raise e

        template_path = location.value
        logger.info(f"Navigating to home location {location.name}")
        self.screen.tap_button(template_path)

    def go_to_town_location(self, location: TownLocation):
        """
        Navigates to a specified location from the town screen.

        Parameters
        ----------
        location : HomeLocation

        Raises
        ------
        Exception
           If the method fails to reach the home screen after multiple attempts,
           it may raise an exception from `wait_for_state` or fail to navigate as expected.
        """

        template_path = location.value

        try:
            self.go_to_home_location(HomeLocation.TOWN)
        except ActionNotPerformed as e:
            logger.warning(f"Failed to navigate to town for {location.name}")
            raise e

        logger.info(f"Navigating to town location {location.name}")
        self.screen.tap_button(template_path)

    def attempt_spire(self):
        logger.info("Attempting the spire")

        path = "locations/town/demon_spire/"
        has_failed = False
        iterations = 0
        try:
            self.go_to_town_location(TownLocation.DEMON_SPIRE)
            # Try to collect ability knowledge, short timeout
            try:
                self.screen.tap_button(f"{path}/collect_ak", timeout=1)
                logger.info("Collected ability knowledge in Demon Spire")
            except:
                logger.debug("No ability knowledge to collect in Demon Spire")

            # Challenge the spire
            while not has_failed and iterations < 80:
                logger.debug("Challenging monster")
                iterations += 1
                self.screen.tap_button(f"{path}/challenge")
                state = self.screen.wait_for_any_state([f"{path}/victory", f"{path}/rewards"], timeout=60)
                match state:
                    case 0:
                        logger.debug("Succeeded monster attempt")
                        self.screen.tap(400, 1300)
                    case 1:
                        self.screen.tap(400, 1300)
                        time.sleep(0.5)
                        self.screen.tap(400, 1300)
                        logger.debug("Succeeded monster attempt")
                    case 2:
                        logger.debug("Failed monster attempt")
                        has_failed = True
                    case _:
                        has_failed = True
                        logger.warning("Unknown state in demon spire, saving debug screencap")
        except:
            logger.exception("Failed to attempt the spire, saving debug screenshot")
            self.debug_screencap(f"demonspire")
        logger.info(f"Stopping attempting the spire after {iterations} attempt(s)")


api = OvermortalAPI()
# api.login()
api.attempt_spire()
