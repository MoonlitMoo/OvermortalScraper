import json
import os
import time

import cv2
import numpy as np

from image_functions import similar_images, stitch_images, locate_area

os.environ["BOT_LOG_LEVEL"] = "DEBUG"

from log import logger
from scrapers.screenshot_processor import ScreenshotProcesser, parse_text_number
from screen import Screen


class CharacterScraper:
    """ From the character select screen, retrieves all stats of a character found within the "Compare BR" tab. """

    def __init__(self, own_character=False):
        self.screen = Screen(logger)
        self.processer = ScreenshotProcesser()
        self.own_character = own_character

    def dynamic_scroll_capture(self, name: str, scroll_params, max_scrolls=20, debug: bool = False):
        """
        Automatically scroll through a panel, capture screenshots, and stitch them.

        Parameters
        ----------
        name : str
            What to save the stitched image as
        scroll_params : tuple
            The (x1, x2, y1, y2, duration) values to define the scroll
        max_scrolls : int
            Safety cap for infinite scrolling bugs.
        debug : bool
            Show debug plots during running

        Returns
        -------
        ndarray
            The stitched image.
        """
        stitched = None
        previous_crop = None
        scroll_count = 0

        while scroll_count < max_scrolls:
            # Update and gety the new image
            self.screen.update()
            full_img = self.screen.colour()

            x1, x2, y1, y2 = (0, 1080, 800, 1700)
            crop = full_img[y1:y2, x1:x2]
            overlap, offset = 100, 250

            if previous_crop is not None and similar_images(previous_crop, crop):
                logger.debug("Stopping scroll: new region is visually the same as previous.")
                break

            if debug and stitched is not None:
                scale = 0.5  # 50% size
                img = cv2.resize(stitched, None, fx=scale, fy=scale)
                cv2.imshow("Pre-stitch", img)

            # Stitch current crop
            if stitched is None:
                stitched = crop
            else:
                stitched = stitch_images(stitched, crop, overlap, offset)

            if debug:
                scale = 0.5  # 50% size
                img = cv2.resize(stitched, None, fx=scale, fy=scale)
                cv2.imshow("Post-stitch", img)
                cv2.waitKey(0)
                cv2.destroyAllWindows()

            previous_crop = crop
            scroll_count += 1

            logger.debug(f"Captured scroll segment {scroll_count}")
            self.screen.swipe(*scroll_params)
            time.sleep(0.2)

        cv2.imwrite(name, stitched)
        logger.debug(f"Saved full scroll region as {name}")

    def get_value(self, template_path: str, screenshot_path: str, x_offset: int) -> float:
        """ Takes an image of the description and uses the location to find the corresponding enemy value.

        Parameters
        ----------
        template_path : str
            The text image to search for
        screenshot_path : str
            The image to search text within
        x_offset : int
            The pixel offset between left side of image and start of search box.

        Returns
        -------
        float
            Parsed value for the text in the image.

        Notes
        -----
        Box for numbers are the same size and y-offset for each stat, so we set it here.
        X offset between image and value is different per page, so taken as an argument.
        Try and find the text area which we know exactly relative to the value, so we can set the search value relative.
        Then we try parse the value in the image, setting to 0 if none found.
        """
        box_width = 230
        box_height = 50
        box_y_offset = -40

        # Find location
        full_img = cv2.cvtColor(cv2.imread(screenshot_path), cv2.COLOR_BGR2GRAY)
        template_img = cv2.cvtColor(cv2.imread(f'resources/character_scraper/{template_path}.png'), cv2.COLOR_BGR2GRAY)

        text_area = locate_area(full_img, template_img, 0.9)
        if text_area is None:
            logger.debug("Couldn't find the text during get_value")
            return None

        # The search area should start at text_x + x_offset, with y being the centre of text image + y offset
        centre_y = (text_area[2] + text_area[3]) / 2
        start_y = int(centre_y + box_y_offset)
        start_x = int(text_area[0] + x_offset)
        search_area = (start_x, start_x + box_width, start_y - int(box_height / 2), start_y + int(box_height / 2))

        # Grab the value
        value = self.processer.extract_text_from_area(self.screen.colour(), area=search_area, psm=7,
                                                      thresholding=False, faint_text=False)
        try:
            return parse_text_number(value)
        except ValueError:
            logger.debug(f"Skipped parsing {value}")
            return None

    def scrape_br_stats(self):
        """ Scrapes the BR stat page for all the values, returning them in a dictionary.
        Checks we are on BR stat page before iterating through all the possible stats to get the image (top to bottom).

        Returns
        -------
        dict
            key: value for all the BR stats.
        """
        ids = ['character', 'technique', 'relic', 'ability', 'curio', 'pet', 'zodiac', 'law', 'immortal', 'daemonfae',
               'field', 'samsara', 'divinity', 'miniworld']
        x_offset = 220 if self.own_character else 500

        _iter = 0
        while not self.screen.find("character_scraper/br_state") and _iter < 5:
            _iter += 1
            self.screen.tap(800, 1800)
            time.sleep(0.5)

        if _iter >= 5:
            logger.warning(f"Failed to get to BR stats after {_iter} attempts")
            return {}

        self.dynamic_scroll_capture("tmp/br_scrollshot.png", (820, 1300, 820, 1100))

        # For each identifier (in order)
        values = {}
        for i in ids:
            val = self.get_value(f"br/{i}", "tmp/br_scrollshot.png", x_offset)
            if not val:
                logger.debug(f"No value for BR stat {i}")
                values[i] = 0
            else:
                values[i] = val
                logger.debug(f"Retrieved BR stat {i} = {val:.3e}")
        return values

    def scrape_stat_stats(self):
        """ Scrapes the stats page for all the values, returning them in a dictionary.
        Checks we are on general stat page before iterating through all the possible stats to get the image
        (top to bottom).

        Returns
        -------
        dict
            key: value for all the stats.
        """
        ids = ['hp', 'mp', 'p_attack', 'p_def', 'm_attack', 'm_def', 'ability_dmg_taoist',
               'ability_dmg_reduction', 'relic_dmg_taoist', 'relic_dmg_reduction', 'dmg_demonic_taoist',
               'demonic_taoist_dmg_reduction', 'dmg_divine_taoist', 'divine_taoist_dmg_reduction', 'p_pen', 'p_block',
               'm_pen', 'm_block', 'crit_multiplier', 'crit_block', 'crit_dmg', 'crit', 'crit_res', 'resilience',
               'control_chance_boost', 'control_chance_resist', 'control_dur_amp', 'control_dur_res',
               'control_dur_boost', 'control_dur_reduction', 'control_resist_chance_reduction', 'curio_dmg_taoist',
               'curio_dmg_reduction', 'p_hit', 'p_eva', 'm_hit', 'm_eva', 'dmg_bonus_monsters', 'monster_dmg_reduction',
               'curio_dmg_monster', 'curio_dmg_pet', 'taoist_dmg_projection', 'law_suppression_boost',
               'law_suppression_resist', 'mortal_ability_dmg_reduction', 'res_mortal_effects',
               'spiritual_ability_dmg_reduction', 'res_spiritual_effects', 'spiritual_paralysis_resist',
               'spiritual_blind_resist', 'spiritual_silence_resist', 'spiritual_curse_resist', 'sense', 'mspd',
               'physique', 'agility', 'manipulation', 'occult_figure', 'hp_regen', 'mp_regen',
               'projection_resist_taoist_dmg']
        x_offset = 280 if self.own_character else 580

        _iter = 0
        while not self.screen.find("character_scraper/stat_state") and _iter < 5:
            _iter += 1
            self.screen.tap(1000, 1800)
            time.sleep(0.5)

        if _iter >= 5:
            logger.warning(f"Failed to get to stats after {_iter} attempts")
            return {}

        # For each identifier (in order)
        values = {}
        for i in ids:
            val = self.get_value(f"character_scraper/stats/{i}", x_offset, 640)
            if not val:
                logger.debug(f"No value for stat {i}")
                values[i] = 0
            else:
                values[i] = val
                logger.debug(f"Retrieved stat {i} = {val:.3e}")
        return values

    def scrape(self):
        # Open screen by clicking the button
        full_stats = {}
        try:
            self.screen.tap_button("../character_scraper/compare_button")
            logger.info("Opened Stats")
            # Set screen masking and filtering
            self.screen.filter_notifications = True
            self.screen.green_select = (590, 1080, 700, 900)
            # Sweep through all the compare BR value
            full_stats.update(self.scrape_br_stats())
            logger.info("Collected BR values")
            # Sweep through all the compare STAT values
            # full_stats.update(self.scrape_stat_stats())
            # logger.info("Collected stat values")
            # Compile into a database.
        except Exception as e:
            self.screen.back()
            raise e
        self.screen.back()
        return full_stats


with open('moonlitmoo.json', 'r') as file:
    exact = json.load(file)

times = []
error = []
for i in range(1):
    s_time = time.perf_counter()
    stats = CharacterScraper(own_character=True).scrape()
    times.append(time.perf_counter() - s_time)
    # print("Found stats:")
    # for k, v in stats.items():
    #     print(f"\t{k}: {v:.3e}")

    print("Differing items")
    wrong = 0
    for k, v in stats.items():
        if exact[k] == 0 and v != exact[k]:
            wrong += 1
            print(f"Found {k}: {v}, previously {exact[k]}")
        elif exact[k] != 0 and abs(v / exact[k] - 1) > 0.01:  # Check within 1%
            wrong += 1
            print(f"Found {k}: {v}, previously {exact[k]} off by {v / exact[k] * 100:3.1f}%")
    print(f"Test {i} incorrect {wrong / len(stats) * 100:3.1f}%")
    error.append(wrong / len(stats))

print(f"Average error {np.average(error) * 100:3.1f}% with std {np.std(error)*100:1.2f}%")
print(f"Average time {np.average(times):3.1f}s with std {np.std(error):2.2f}s%")
