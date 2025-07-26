import re
import time
import cv2

from core.log import logger
from core.screenshot_processor import ScreenshotProcessor
from core.screen import Screen


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


class ItemScraper:

    def __init__(self):
        self.screen = Screen(logger)

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
        self.screen.capture_filter_notifications(name=f"{save_name}_item{number}_t.png", green_mask=[200, 400, 100, 300])
        time.sleep(0.25)

        # 5. Swipe up
        self.screen.swipe_down(700, 300)
        time.sleep(0.25)

        # 6. Screenshot weapon bottom
        self.screen.capture_filter_notifications(name=f"{save_name}_item{number}_b.png", green_mask=[200, 400, 100, 300])
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
                self.screen.capture_filter_notifications(f"ability_{ability_type}_item{i}.png", green_mask=[200, 400, 100, 300])
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
                self.screen.capture_filter_notifications(f"pet_item{i}.png", green_mask=[150, 340, 300, 1700])
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
                self.screen.capture_filter_notifications(f"divinity_item{i + offset}.png", green_mask=[100, 1000, 200, 400])
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


ScreenshotProcessor().process_weapon("screencaps/weapon_item2")

# ItemScraper().iterate_list("resources/item_scraper/item_edge.png", "relic", 12)
# ItemScraper().save_item("relic", 19)
# ItemScraper().save_abilities("magicka")
# ItemScraper().save_pets()
# ItemScraper().save_divinities(60)
