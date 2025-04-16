import subprocess
import time
from typing import List

import cv2


class StateNotReached(Exception):
    pass


class ActionNotPerformed(Exception):
    pass


class Screen:
    CURRENT_SCREEN = "./screen.png"
    THRESHOLD = 0.9
    TIMEOUT = 15
    POLL_INTERVAL = 0.1

    dimensions = None, None

    def __init__(self):
        self.update()
        y, x, _ = cv2.imread(self.CURRENT_SCREEN).shape
        self.dimensions = x, y

    def colour(self):
        """ Returns current screen image in colour. """
        return cv2.imread(self.CURRENT_SCREEN)

    def grayscale(self):
        """ Returns current screen image in grayscale. """
        return cv2.cvtColor(cv2.imread(self.CURRENT_SCREEN), cv2.COLOR_BGR2GRAY)

    def update(self):
        """ Updates saved screen image """
        subprocess.run(["adb", "shell", "screencap", "-p", "/sdcard/screen.png"])
        subprocess.run(["adb", "pull", "/sdcard/screen.png", self.CURRENT_SCREEN])
        return cv2.imread(self.CURRENT_SCREEN)

    def _locate_image(self, template_path: str, threshold: float = THRESHOLD):
        """ Returns max location and threshold value of found location. """
        self.update()
        screen = self.grayscale()
        template = cv2.cvtColor(cv2.imread(template_path), cv2.COLOR_BGR2GRAY)
        res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val >= threshold:
            return max_loc, max_val
        return None

    def back(self):
        """ Sends the Android 'Back' command to ADB device. """
        subprocess.run(["adb", "shell", "input", "keyevent", "KEYCODE_BACK"], check=True)

    def find_button(self, template_path: str, threshold: float = THRESHOLD) -> (int, int):
        """ Returns location of button in pixel coordinates or None if not found. """
        result = self._locate_image(f'resources/buttons/{template_path}.png', threshold)
        return None if result is None else result[0]

    def wait_for_state(self, template_path: str, threshold: float = THRESHOLD, timeout: float = TIMEOUT,
                       poll_interval: float = POLL_INTERVAL) -> bool:
        """ Returns true when state is found.

        Parameters
        ----------
        template_path : str
            Image path matching state to find
        threshold : float
            conf interval
        timeout : float
            Max seconds to wait for state
        poll_interval : float
            Seconds to wait between screen updates

        Returns
        -------
        bool
            If state was acquired/found.
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            result = self._locate_image(f'resources/state/{template_path}.png', threshold)
            if result is not None:
                return True
            time.sleep(poll_interval)
        raise StateNotReached(f"Failed to find state {template_path}")

    def wait_for_any_state(self, template_paths: List[str], threshold: float = THRESHOLD, timeout: float = TIMEOUT,
                           poll_interval: float = POLL_INTERVAL) -> int:
        """ Returns true and what state when any state in given list is found.

        Parameters
        ----------
        template_paths : list of str
            Image paths matching state to find
        threshold : float
            conf interval
        timeout : float
            Max seconds to wait for state
        poll_interval : float
            Seconds to wait between screen updates

        Returns
        -------
        bool
            If state was acquired/found.
        int
            Index of found state
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            for i, path in enumerate(template_paths):
                result = self._locate_image(f'resources/state/{path}.png', threshold)
                if result is not None:
                    return i
            time.sleep(poll_interval)
        raise StateNotReached(f"Failed to find any of state {template_paths}")

    def tap(self, x, y):
        """ Taps screen at given coordinates """
        subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)])

    def tap_button(self, template_path: str, threshold: float = THRESHOLD, timeout: float = TIMEOUT,
                   poll_interval: float = POLL_INTERVAL) -> bool:
        """ Clicks selected button with a timeout"""
        but_y, but_x, _ = cv2.imread(f'resources/buttons/{template_path}.png').shape
        loc = None

        # Find the button
        start_time = time.time()
        while time.time() - start_time < timeout and loc is None:
            loc = self.find_button(template_path, threshold)
            time.sleep(poll_interval)

        # Raise if failed
        if loc is None:
            raise ActionNotPerformed(f"Failed to press button {template_path}")

        # Click centre of button
        self.tap(loc[0] + but_x / 2, loc[1] + but_y / 2)
        return True
