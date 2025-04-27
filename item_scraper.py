import numpy as np
import cv2

from screen import Screen


class ItemScraper:

    def __init__(self):
        self.screen = Screen()

    def iterate_list(self):
        pass

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


ItemScraper().debug_show_matches("resources/item_scraper/item_edge.png", threshold=0.7)
