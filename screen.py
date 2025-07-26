import subprocess
import time
from typing import List

import cv2
import numpy as np

from image_functions import locate_image, stitch_images, similar_images


class StateNotReached(Exception):
    pass


class ActionNotPerformed(Exception):
    pass


class Screen:
    CURRENT_SCREEN = "./tmp/screen.png"
    THRESHOLD = 0.9
    TIMEOUT = 15
    POLL_INTERVAL = 0.1

    dimensions = None, None

    def __init__(self, logger, bluestacks_host: str = "emulator-5554"):
        self.logger = logger
        self.filter_notifications = False
        self.green_mask = (0, 0, 0, 0)
        self.green_select = (0, 1080, 700, 900)

        try:
            # Check connected devices
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
            devices_output = result.stdout

            if bluestacks_host not in devices_output:
                print("BlueStacks not found in connected devices. Attempting to connect...")
                connect_result = subprocess.run(["adb", "connect", "127.0.0.1:5555"], capture_output=True, text=True)
                if "connected" in connect_result.stdout.lower():
                    print("Successfully connected to BlueStacks.")
                else:
                    print(f"Failed to connect: {connect_result.stdout.strip()}")
                    exit(1)
        except Exception as e:
            print(f"Error while checking/connecting ADB: {e}")

        self.update()
        y, x, _ = cv2.imread(self.CURRENT_SCREEN).shape
        self.dimensions = x, y

    def colour(self):
        """ Returns current screen image in colour. """
        return cv2.imread(self.CURRENT_SCREEN)

    def grayscale(self):
        """ Returns current screen image in grayscale. """
        return cv2.cvtColor(cv2.imread(self.CURRENT_SCREEN), cv2.COLOR_BGR2GRAY)

    def capture(self, name: str = None, update: bool = True):
        """
        Capture the current screen in colour and save it to a file.

        Parameters
        ----------
        name : str, optional
            Filename to save the screenshot. If None, uses a timestamped filename.
        update : bool, optional
            Whether to update before saving.
        """
        if update:
            self.update()  # Make sure the latest screen is fetched
        img = self.colour()  # Get the colour version of the screen

        if name is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            name = f"screenshot_{timestamp}.png"

        if cv2.imwrite(f'screencaps/{name}', img):
            self.logger.info(f"Saved screenshot: {name}")
        else:
            self.logger.warning(f"Failed to save screenshot: {name}")

    def capture_filter_notifications(self, name: str = None, retries: int = 5, delay: float = 1.0,
                                     green_mask=[200, 400, 100, 300]):
        """
        Capture the current screen and ensure no green popups are present.

        Parameters
        ----------
        green_mask
        name : str, optional
            Filename to save the screenshot. If None, use a timestamped filename.
        retries : int, optional
            Maximum number of attempts to get a clean screenshot (default 5).
        delay : float, optional
            Delay between retries in seconds (default 1.0s).

        Returns
        -------
        bool
            True if successful, False if green couldn't be avoided after retries.
        """
        if self.update_filter_notifications(retries, delay, green_mask):
            if name is None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                name = f"screenshot_{timestamp}.png"
            cv2.imwrite(f'screencaps/{name}', self.colour())
            self.logger.info(f"Saved clean screenshot: {name}")
        return False

    def capture_scrollshot(self, file: str, overlap: int, offset: int, scroll_params, crop_area=None, max_shots: int = 50):
        stitched = None
        prev_img = None
        similar_count = 0

        for i in range(max_shots):
            # Get the screenshot
            self.update()
            img = self.colour()

            # Trim if we are sub-selecting a region
            if crop_area:
                x1, x2, y1, y2 = crop_area
                img = img[y1:y2, x1:x2]

            # Stitch images together if we can
            if prev_img is not None:
                # Break if we have found similar images three times in a row+
                if similar_images(prev_img, img):
                    if similar_count > 2:
                        self.logger.advdebug("No change detected, stopping.")
                        break
                    else:
                        similar_count += 1
                else:
                    similar_count = 0
                stitched = stitch_images(stitched, img, overlap, offset)
            else:
                stitched = img

            prev_img = img
            self.swipe(*scroll_params)
            time.sleep(.2)

        cv2.imwrite(file, stitched)

    def _update(self):
        subprocess.run(["adb", "shell", "screencap", "-p", "/sdcard/screen.png"], stdout=subprocess.DEVNULL)
        subprocess.run(["adb", "pull", "/sdcard/screen.png", self.CURRENT_SCREEN],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def update(self):
        """ Updates saved screen image and returns it """
        if self.filter_notifications:
            self.update_filter_notifications()
        else:
            self._update()
        return cv2.imread(self.CURRENT_SCREEN)

    def update_filter_notifications(self, retries: int = 5, delay: float = 1.0,
                                    green_mask: tuple = None, debug: bool = False):
        if green_mask is None:
            green_mask = self.green_mask

        for attempt in range(retries):
            self._update()
            img = self.colour()

            # Convert to HSV for better color detection
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # Define green color range (tweak if needed)
            lower_green = np.array([50, 50, 50])
            upper_green = np.array([90, 255, 255])

            # Create a mask for green areas
            mask = cv2.inRange(hsv, lower_green, upper_green)
            mask[green_mask[2]:green_mask[3], green_mask[0]:green_mask[1]] = 0  # Skip any pictures

            # Crop to notification area
            crop = mask[self.green_select[2]:self.green_select[3], self.green_select[0]:self.green_select[1]]

            green_pixels = cv2.countNonZero(crop)
            total_pixels = crop.shape[0] * crop.shape[1]
            green_ratio = green_pixels / total_pixels

            if debug:
                self.logger.advdebug(f"Attempt {attempt + 1}: Green coverage = {green_ratio:.6f}")
                cv2.imshow("Green locations", crop)
                cv2.waitKey(0)
                cv2.destroyAllWindows()

            if green_ratio < 0.001:  # Less than 0.1% green pixels → accept
                return True
            else:
                self.logger.advdebug("Notification detected, retrying...")
                time.sleep(delay)

        self.logger.advdebug(f"Failed to get clean screen after {retries} retries.")
        return False

    def _load_template_image(self, template_path):
        img = cv2.imread(template_path)
        if img is None:
            raise FileNotFoundError(template_path)
        return img

    def _locate_image(self, template_path: str, threshold: float = THRESHOLD):
        """ Returns max location and threshold value of found location. """
        self.update()
        screen = self.grayscale()
        template = cv2.cvtColor(self._load_template_image(template_path), cv2.COLOR_BGR2GRAY)
        return locate_image(screen, template, threshold)

    def find_all_images(self, template_path: str, threshold: float = THRESHOLD, max_results: int = 10,
                        debug: bool = False):
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
        debug : bool, default=false
            Whether to show debug image
        Returns
        -------
        List[Tuple[Tuple[int, int], float]]
            List of (position, match_value) tuples.
        """
        self.update()
        screen = self.grayscale()
        template = cv2.cvtColor(self._load_template_image(template_path), cv2.COLOR_BGR2GRAY)

        res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)

        # Find all locations above the threshold
        match_locations = np.where(res >= threshold)

        matches = []
        for (y, x) in zip(*match_locations):  # Note cv2 gives (y, x)
            match_val = res[y, x]
            matches.append(((x, y), match_val))

        # Sort matches by match value, descending
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

        if debug:
            y_size, x_size = template.shape
            screen = self.colour()
            # Draw final matches in green
            for pos, score in final_matches:
                x, y = pos
                top_left = (x, y)
                bottom_right = (x + x_size, y + y_size)
                cv2.rectangle(screen, pt1=top_left, pt2=bottom_right, color=(0, 255, 0), thickness=2)
            height, width = screen.shape[:2]
            cv2.imshow("Debug find_all_images", cv2.resize(screen, (width // 2, height // 2)))
            cv2.waitKey(0)
        return final_matches

    def find_area(self, template_path: str, threshold: float = THRESHOLD) -> (int, int):
        """ Returns area (x1, x2, y1, y2) of an image in pixel coordinates or None if not found. """
        result = self._locate_image(f'resources/{template_path}.png', threshold)
        if result is None: return None
        y_len, x_len, _ = self._load_template_image(f'resources/{template_path}.png').shape
        x, y = result[0]
        return x, x + x_len, y, y + y_len

    def find(self, template_path: str, threshold: float = THRESHOLD) -> (int, int):
        """ Returns location of image in pixel coordinates or None if not found. """
        result = self._locate_image(f'resources/{template_path}.png', threshold)
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
        button_area = None

        # Find the button
        start_time = time.time()
        while time.time() - start_time < timeout and button_area is None:
            button_area = self.find_area(f'buttons/{template_path}', threshold)
            time.sleep(poll_interval)

        # Raise if failed
        if button_area is None:
            raise ActionNotPerformed(f"Failed to press button {template_path}")

        # Click centre of button
        self.tap((button_area[0] + button_area[1]) / 2, (button_area[2] + button_area[3]) / 2)
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
