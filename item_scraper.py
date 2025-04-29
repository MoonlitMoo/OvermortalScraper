import re
import time
import cv2
import matplotlib.pyplot as plt
import numpy as np
import seaborn
from pytesseract import pytesseract

from log import logger
from screen import Screen


class ItemScraper:

    def __init__(self):
        self.screen = Screen(logger)

    def capture_no_notifications(self, name: str = None, retries: int = 5, delay: float = 1.0,
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
        for attempt in range(retries):
            self.screen.update()
            img = self.screen.colour()

            # Convert to HSV for better color detection
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # Define green color range (tweak if needed)
            lower_green = np.array([50, 50, 50])
            upper_green = np.array([90, 255, 255])

            # Create a mask for green areas
            mask = cv2.inRange(hsv, lower_green, upper_green)
            mask[green_mask[2]:green_mask[3], green_mask[0]:green_mask[1]] = 0  # Skip any pictures

            green_pixels = cv2.countNonZero(mask)
            total_pixels = img.shape[0] * img.shape[1]
            green_ratio = green_pixels / total_pixels

            logger.debug(f"[Screen] Attempt {attempt + 1}: Green coverage = {green_ratio:.6f}")

            if green_ratio < 0.001:  # Less than 0.1% green pixels → accept
                if name is None:
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    name = f"screenshot_{timestamp}.png"
                cv2.imwrite(f'screencaps/{name}', img)
                logger.debug(f"[Screen] Saved clean screenshot: {name}")
                return True
            else:
                logger.debug("[Screen] Green detected, retrying...")
                time.sleep(delay)

        logger.warning("[Screen] Failed to get clean screenshot after retries.")
        return False

    def iterate_list(self, template_path: str, save_name: str, offset=0):
        """
        Iterate through each weapon/item on the list, open details,
        capture screenshots before and after scrolling, and save them.
        """
        logger.info(f"Starting to iterate list of {save_name}")

        # Step 1: Detect matches
        matches_first = self.screen.find_all_images(template_path, threshold=0.8)
        time.sleep(2)
        matches_second = self.screen.find_all_images(template_path, threshold=0.8)

        # Step 2: Use the detection with most matches
        matches = matches_first if len(matches_first) >= len(matches_second) else matches_second

        logger.info(f"Detected {len(matches)} items to scrape.")

        # Step 3-8: Process each item
        for idx in range(len(matches)):
            # 3. Click at position (500, match_y + 60)
            match_pos = matches[idx][0]  # (x, y)
            _, match_y = match_pos
            click_x = 500
            click_y = match_y + 60

            logger.info(f"Selecting item {idx + 1 + offset} at ({click_x}, {click_y})")
            self.screen.tap(click_x, click_y)
            time.sleep(0.5)  # Small delay to load

            self.save_item(save_name, idx + 1 + offset)

            # 7. Tap to exit item screen
            self.screen.tap(500, 1700)
            time.sleep(0.5)  # Small wait to return to list

        logger.info(f"Finished scraping all {save_name} items.")

    def save_item(self, save_name, number):
        """ Saves the current item. """
        # 4. Screenshot weapon top
        self.screen.swipe_up(700, 300)
        self.capture_no_notifications(name=f"{save_name}_item{number}_t.png")
        time.sleep(0.25)

        # 5. Swipe up
        self.screen.swipe_down(700, 300)
        time.sleep(0.25)

        # 6. Screenshot weapon bottom
        self.capture_no_notifications(name=f"{save_name}_item{number}_b.png")
        time.sleep(0.25)

    def save_abilities(self, ability_type):
        """ Saves the items from the ability screen """
        x_loc = [300, 600, 900]
        y_loc = [520, 750]
        logger.info(f"Starting {ability_type} saving")
        i = 0
        for x in x_loc:
            for y in y_loc:
                i += 1
                logger.debug(f"Selecting item {i} at {x}, {y}")
                self.screen.tap(x, y)
                time.sleep(0.5)
                self.capture_no_notifications(f"ability_{ability_type}_item{i}.png")
                logger.debug(f"Exiting ability screen")
                self.screen.tap(500, 1700)
                time.sleep(0.5)

    def save_pets(self):
        """ Saves the items from the pet formation screen """
        x_loc = [200, 400, 600, 900]
        y_loc = [900, 1400]
        logger.info(f"Starting pet info saving")
        i = 0
        for y in y_loc:
            for x in x_loc:
                i += 1
                if i > 6:
                    break
                logger.debug(f"Selecting pet {i} at {x}, {y}")
                self.screen.tap(x, y)  # Select pet
                time.sleep(0.5)  # Select info
                self.screen.tap_button("../item_scraper/info_button")
                time.sleep(0.5)
                self.capture_no_notifications(f"pet_item{i}.png", green_mask=[150, 340, 300, 1700])
                logger.debug(f"Exiting Pet screen")
                self.screen.tap(500, 1800)
                time.sleep(0.5)
        logger.info(f"Finished pet info saving")

    def save_divinities(self, offset=0):
        """ Saves the items from the pet formation screen """
        x_loc = [200, 400, 500, 700, 900]
        y_loc = [800, 1350]
        logger.info(f"Starting divinity info saving")
        i = 0
        for y in y_loc:
            for x in x_loc:
                i += 1
                logger.debug(f"Selecting divinity {i} at {x}, {y}")
                self.screen.tap(x, y)  # Select divinity
                time.sleep(0.5)
                self.capture_no_notifications(f"divinity_item{i + offset}.png", green_mask=[100, 1000, 200, 400])
                logger.debug(f"Exiting Divinity screen")
                self.screen.tap(500, 1800)
                time.sleep(0.5)
        logger.info(f"Finished divinity info saving")

    def debug_show_matches(self, template_path: str, threshold: float = 0.8, radius: int = 20,
                           window_name: str = "Matches"):
        """
        Find all matches for a template and display the matches visually for debugging.

        Parameters
        ----------
        template_path : str
            Path to the template image (for dimensions if needed).
        threshold : float, optional
            Matching threshold (default is 0.8).
        radius : int, optional
            Radius of the circle to draw around matches.
        window_name : str, optional
            Name of the window when displaying matches.
        """
        # 1. Find all matches
        matches = self.screen.find_all_images(template_path, threshold=threshold)

        # 2. Update screen capture to color version
        self.screen.update()
        screen_img = self.screen.colour()  # Work with color image if available

        # 3. Draw circles on all matches
        for (x, y), score in matches:
            cv2.circle(screen_img, (x, y), radius, (0, 255, 0), 2)

        # 4. Display
        cv2.imshow(window_name, screen_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def parse_and_sum(text: str) -> float:
        """
        Parse a text like '1.38M +1.7M' or '421.38K +518.29K' and return the sum as a float.

        Parameters
        ----------
        text : str
            Text containing two numbers separated by '+'.

        Returns
        -------
        float
            The sum of the two numbers.
        """
        # Remove spaces
        text = text.replace(' ', '')

        # Regular expression to find numbers with optional 'K' or 'M'
        pattern = r'([\d\.]+)([MK]?)'
        matches = re.findall(pattern, text)

        if not matches or len(matches) < 2:
            raise ValueError(f"Could not parse two numbers from: {text}")

        total = 0.0
        for number, suffix in matches:
            num = float(number)
            if suffix == 'M':
                num *= 1_000_000
            elif suffix == 'K':
                num *= 1_000
            total += num

        return total


def parse_and_sum(text: str) -> float:
    """
    Parse a text like '1.38M +1.7M' or '421.38K +518.29K' and return the sum as a float.

    Parameters
    ----------
    text : str
        Text containing two numbers separated by '+'.

    Returns
    -------
    float
        The sum of the two numbers.
    """
    # Remove spaces
    text = text.replace(' ', '')

    # Regular expression to find numbers with optional 'K' or 'M'
    pattern = r'([\d\.]+)([MK]?)'
    matches = re.findall(pattern, text)

    if not matches or len(matches) < 2:
        raise ValueError(f"Could not parse two numbers from: {text}")

    total = 0.0
    for number, suffix in matches:
        num = float(number)
        if suffix == 'M':
            num *= 1_000_000
        elif suffix == 'K':
            num *= 1_000
        total += num
    return total


class ScreenshotProcesser():

    def __init__(self):
        pass

    def extract_text_from_area(self, image_path: str, area: tuple, psm: int = 6, thresholding: bool = True) -> str:
        """
        Extract text from a specific rectangular area of an image.

        Parameters
        ----------
        image_path : str
            Path to the input image file.
        area : tuple
            (x1, y1, x2, y2) specifying the crop rectangle.
        psm : int, optional
            Page Segmentation Mode for Tesseract (default 6 = block of text).
        thresholding : bool, optional
            Whether to apply thresholding before OCR (default True).

        Returns
        -------
        str
            Extracted text from the specified area.
        """
        # Load image
        img = cv2.imread(image_path)

        # Crop area
        x1, x2, y1, y2 = area
        crop = img[y1:y2, x1:x2]

        # Preprocess
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        if thresholding:
            _, proc = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        else:
            proc = gray

        # OCR config
        custom_config = f'--oem 3 --psm {psm}'
        text = pytesseract.image_to_string(proc, config=custom_config)

        return text.strip()

    def extract_text_from_lines(self, image_path, first_line, line_height, num_lines, psm, thresholding: bool = True):
        lines = []
        for i in range(num_lines):
            # Adjust area y1, y2 down by the line height
            area = first_line
            area[2] += line_height * i
            area[3] += line_height * i
            lines.append(self.extract_text_from_area(image_path, area, psm, thresholding))
        return lines

    def process_weapon(self, image_path):
        # Define crop areas (x1, x2, y1, y2) based on your screenshots
        title_area = (300, 900, 250, 320)
        basic_effects_area = (100, 800, 510, 700)

        # Extract from top image
        raw_title_text = self.extract_text_from_area(f"{image_path}_t.png", title_area, 7)
        raw_basic_text = self.extract_text_from_area(f"{image_path}_t.png", basic_effects_area, 6)

        title_text = raw_title_text.split("+")[0].strip()
        basic_effects = {}
        for line in raw_basic_text.split("\n"):
            effect, value = line.split(":")
            basic_effects[effect] = parse_and_sum(value)

        print(f"Found title text {raw_title_text} -> {title_text}")
        print(f"Found basic text {raw_basic_text} -> {basic_effects}")


ScreenshotProcesser().process_weapon("screencaps/weapon_item2")

# ItemScraper().iterate_list("resources/item_scraper/item_edge.png", "relic", 12)
# ItemScraper().save_item("relic", 19)
# ItemScraper().save_abilities("magicka")
# ItemScraper().save_pets()
# ItemScraper().save_divinities(60)
