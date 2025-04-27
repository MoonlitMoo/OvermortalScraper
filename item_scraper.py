import time
import cv2
import numpy as np

from log import logger
from screen import Screen


class ItemScraper:

    def __init__(self):
        self.screen = Screen(logger)

    def capture_no_notifications(self, name: str = None, retries: int = 5, delay: float = 1.0):
        """
        Capture the current screen and ensure no green popups are present.

        Parameters
        ----------
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

    def iterate_list(self, template_path: str, save_name: str):
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

            logger.info(f"Selecting item {idx + 1} at ({click_x}, {click_y})")
            self.screen.tap(click_x, click_y)
            time.sleep(0.5)  # Small delay to load

            # 4. Screenshot weapon top
            self.screen.swipe_up(700, 300)
            self.capture_no_notifications(name=f"{save_name}_item{idx + 1}_t.png")
            time.sleep(0.25)

            # 5. Swipe up
            self.screen.swipe_down(700, 300)
            time.sleep(0.25)

            # 6. Screenshot weapon bottom
            self.capture_no_notifications(name=f"{save_name}_item{idx + 1}_b.png")
            time.sleep(0.25)

            # 7. Tap to exit item screen
            self.screen.tap(500, 1700)
            time.sleep(0.5)  # Small wait to return to list

        logger.info(f"Finished scraping all {save_name} items.")

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


ItemScraper().iterate_list("resources/item_scraper/item_edge.png", "weapon")
