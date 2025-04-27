import subprocess
import time
from typing import List

import cv2
import numpy as np


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

    def __init__(self, logger):
        self.logger = logger
        self.update()
        y, x, _ = cv2.imread(self.CURRENT_SCREEN).shape
        self.dimensions = x, y

    def colour(self):
        """ Returns current screen image in colour. """
        return cv2.imread(self.CURRENT_SCREEN)

    def grayscale(self):
        """ Returns current screen image in grayscale. """
        return cv2.cvtColor(cv2.imread(self.CURRENT_SCREEN), cv2.COLOR_BGR2GRAY)

    def capture(self, name: str = None):
        """
        Capture the current screen in colour and save it to a file.

        Parameters
        ----------
        name : str, optional
            Filename to save the screenshot. If None, uses a timestamped filename.
        """
        self.update()  # Make sure the latest screen is fetched
        img = self.colour()  # Get the colour version of the screen

        if name is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            name = f"screenshot_{timestamp}.png"

        cv2.imwrite(f'screencaps/{name}', img)
        self.logger.info(f"[Screen] Saved screenshot: {name}")

    def update(self):
        """ Updates saved screen image """
        subprocess.run(["adb", "shell", "screencap", "-p", "/sdcard/screen.png"], stdout=subprocess.DEVNULL)
        subprocess.run(["adb", "pull", "/sdcard/screen.png", self.CURRENT_SCREEN],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

    import cv2
    import numpy as np

    def find_all_images(self, template_path: str, threshold: float = THRESHOLD, max_results: int = 10):
        """
        Find all locations where the template matches above a given threshold.

        Parameters
        ----------
        template_path : str
            Path to the template image.
        threshold : float, optional
            Matching threshold (default is THRESHOLD).
        max_results : int, optional
            Maximum number of matches to return (default is 10).

        Returns
        -------
        List[Tuple[Tuple[int, int], float]]
            List of (position, match_value) tuples.
        """
        self.update()
        screen = self.grayscale()
        template = cv2.cvtColor(cv2.imread(template_path), cv2.COLOR_BGR2GRAY)

        res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)

        # Find all locations above the threshold
        match_locations = np.where(res >= threshold)

        matches = []
        for (y, x) in zip(*match_locations):  # Note cv2 gives (y, x)
            match_val = res[y, x]
            matches.append(((x, y), match_val))

        # Sort matches by match value, descending (optional)
        matches = sorted(matches, key=lambda x: -x[1])

        # Remove very close duplicates
        final_matches = []
        taken = np.zeros_like(res)
        for (pos, score) in matches:
            x, y = pos
            if not taken[y, x]:
                final_matches.append((pos, score))
                # Mask an area around the selected match
                cv2.circle(taken, center=(x, y), radius=20, color=True,
                           thickness=-1)  # 20px radius prevents very close repeats
            if len(final_matches) >= max_results:
                break

        return final_matches

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

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        """
        Perform a swipe gesture from (x1, y1) to (x2, y2).

        Parameters
        ----------
        x1 : int
            Start x-coordinate.
        y1 : int
            Start y-coordinate.
        x2 : int
            End x-coordinate.
        y2 : int
            End y-coordinate.
        duration_ms : int, optional
            Duration of the swipe in milliseconds (default is 300 ms).
        """
        cmd = f"adb shell input swipe {x1} {y1} {x2} {y2} {duration_ms}"
        subprocess.run(cmd.split(), check=True)

    def swipe_up(self, amount: int = 300, duration_ms: int = 300):
        width, height = self.dimensions
        x = width // 2
        y_start = height // 2 - amount // 2
        y_end = height // 2 + amount // 2
        self.swipe(x, y_start, x, y_end, duration_ms)

    def swipe_down(self, amount: int = 300, duration_ms: int = 300):
        width, height = self.dimensions
        x = width // 2
        y_start = height // 2 + amount // 2
        y_end = height // 2 - amount // 2
        self.swipe(x, y_start, x, y_end, duration_ms)

    def back(self):
        """ Sends the Android 'Back' command to ADB device. """
        subprocess.run(["adb", "shell", "input", "keyevent", "KEYCODE_BACK"], check=True)
