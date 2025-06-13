import json
import time

import cv2
import jellyfish
import numpy as np

# os.environ["BOT_LOG_LEVEL"] = "DEBUG"

from log import logger
from screen import Screen
from image_functions import locate_area
from scrapers.screenshot_processor import ScreenshotProcesser, parse_text_number
from data_types import *


class CharacterScraper:
    """ From the character select screen, retrieves all stats of a character found within the "Compare BR" tab. """

    def __init__(self, own_character=False):
        self.screen = Screen(logger)
        self.processor = ScreenshotProcesser()
        self.own_character = own_character

    def get_start_loc(self, screenshot_path, template_path, x_offset):
        # Find location
        full_img = cv2.imread(screenshot_path)
        template_img = cv2.cvtColor(cv2.imread(f'resources/character_scraper/{template_path}.png'), cv2.COLOR_BGR2GRAY)

        text_area = locate_area(cv2.cvtColor(full_img, cv2.COLOR_BGR2GRAY), template_img, 0.9)
        if text_area is None:
            logger.debug(f"Failed to get image {template_path}")
            return None

        box_y_offset = -40

        centre_y = (text_area[2] + text_area[3]) / 2
        start_y = int(centre_y + box_y_offset)
        start_x = int(text_area[0] + x_offset)

        return start_x, start_y

    def get_value(self, screenshot_path, start_x, start_y, debug=False):
        box_width = 230
        box_height = 50

        search_area = (start_x, start_x + box_width, start_y - int(box_height / 2), start_y + int(box_height / 2))

        if debug:
            img = cv2.imread(screenshot_path)
            cv2.rectangle(img, (start_x, start_y - int(box_height / 2)),
                          (start_x + box_width, start_y + int(box_height / 2)), (0, 255, 0), 2)
            clip_min, clip_max = max(search_area[2] - 20, 0), min(search_area[3] + 20, img.shape[0])
            cv2.imshow("Search Area", img[clip_min:clip_max])
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        value = self.processor.extract_text_from_area(screenshot_path, area=search_area,
                                                      thresholding=False,
                                                      faint_text=not self.own_character)
        try:
            logger.debug(f"[get_value] Retrieved text '{value}' as '{parse_text_number(value)}")
            return parse_text_number(value)
        except ValueError:
            logger.debug(f"[get_value] Retrieved text '{value}' as '0'")
            return 0

    def scrape_item(self, x, y, data_enum, full_match=False, check_double_path=False):
        """ Scrapes an item for the name and turns it into an enumeration type.
        First opens it from the character screen.
        Generally separates out the last word as the name to check for most similar enumeration. Optionally can use full
        name. Can also check for double path and prefix this to the name.

        Parameters
        ----------
        x : int
            The x pixel coordinate of the item
        y : int
            The y pixel coordinate of the item
        data_enum
            An enum class the item should belong to
        full_match : bool, optional
            Whether to match full name against the enum, or just the last word.
        check_double_path : bool, optional
            Whether to check if the item is double path.

        Returns
        -------
        item
            An enum from the given enum class, or None if no matches.


        Notes
        -----
        If no matching enum is found, a debug image of the item is captured and logger is given a warning.
        """
        # Select item
        self.screen.tap(x, y)
        time.sleep(0.75)

        # Read text
        img = self.screen.update()
        name_bbox = (300, 1000, 250, 420)

        all_text = self.processor.extract_text_from_area(img, name_bbox, all_text=True)
        # Join all the text and rely on enhancement to split off the name
        full_name = ' '.join(all_text).split("+")[0].strip()

        # Look for double path in any of the full text we find
        if check_double_path:
            is_double_path = any(['DOUBLE PATH' in i.upper() for i in all_text])
        else:
            is_double_path = False

        # Trim if we only want the last word
        if not full_match:
            full_name = full_name.split(' ')[-1]

        # Add double path prefix
        if is_double_path:
            full_name = f"DOUBLE_PATH_{full_name}"

        # Look for most similar enum value
        test_name = full_name.replace(' ', '_').upper()
        item = None
        for enum in data_enum:
            if jellyfish.jaro_winkler_similarity(enum.value, test_name) > 0.9:
                item = enum.value
                break

        if item is None:
            # If missed, throw image into debug for later checking
            item = "NONE"
            logger.warning(f"Failed to parse '{full_name}' from capture '{all_text}' into a {data_enum}")
            self.screen.capture(f"debug/unknown_item_{all_text}.png")

        # Return back to main screen
        self.screen.tap(500, 1800)
        time.sleep(0.75)
        return item

    def scrape_name(self):
        # Open report screen by tapping more and report
        self.screen.tap(200, 1225)
        time.sleep(0.1)
        self.screen.tap(400, 990)
        time.sleep(0.1)
        # Capture text of name
        img = self.screen.update()
        all_text = self.processor.extract_text_from_area(
            img, (100, 950, 550, 650), all_text=True, use_name_reader=True)
        text = ' '.join(all_text).split("player:")[-1].lower().strip()
        logger.debug(f"Scraped name '{text}'")
        # Go back to home screen
        self.screen.tap(500, 1500)
        time.sleep(0.1)
        self.screen.tap(500, 1500)
        return {"name": text}

    def scrape_total_br(self):
        img = self.screen.update()
        value = self.processor.extract_text_from_area(img, (820, 1000, 250, 300))
        logger.debug(f"[scrape_total_br] Found '{value}' and parsed as '{parse_text_number(value)}'")
        return {"total_br": parse_text_number(value)}

    def scrape_relics(self):
        """ Scrapes the relics and curios that a Taoist is using.
        Defines the coordinates for each item and scrapes them individually.

        Returns
        -------
        values : dict
            A label : enum value dict of the 12 scraped items.
        """
        values = {}
        col1, col2 = 760, 900
        row1, row2, row3 = 500, 625, 700

        # Weapon
        logger.debug(f"Getting weapon")
        values["weapon"] = self.scrape_item(col1, row1, Weapon, check_double_path=True)
        # Armour
        logger.debug(f"Getting armour")
        values["armour"] = self.scrape_item(col1, row2, Armour, check_double_path=True)
        # Accessory
        logger.debug(f"Getting accessory")
        values["accessory"] = self.scrape_item(col1, row3, Accessory, check_double_path=True)

        # Curio
        for i, r in enumerate([row1, row2, row3]):
            logger.debug(f"Getting curio_{i+1}")
            values[f"curio_{i+1}"] = self.scrape_item(col2, r, Curio, full_match=True)

        # General relics
        i = 0
        for c in [col1, col2]:
            for r in [880, 1000, 1130]:
                i += 1
                logger.debug(f"Getting relic_{i}")
                values[f"relic_{i}"] = self.scrape_item(c, r, Relic)
        return values

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

        if not self.screen.find("character_scraper/br_state"):
            self.screen.tap(800, 1800)
            self.screen.wait_for_state("../character_scraper/br_state")

        path = "tmp/br_scrollshot.png"
        self.screen.capture_scrollshot(path, 200, 250,
                                       (820, 1300, 820, 1200), (0, 1080, 800, 1700))

        x, y_origin = self.get_start_loc(path, 'br/character', x_offset)
        # For each identifier (in order)
        values = {}
        for idx, i in enumerate(ids):
            y = y_origin + idx * 124
            try:
                val = self.get_value(path, x, y)
            except Exception as e:
                logger.error(f"Failed to find BR stat {i} at x={x}, y={y}")
                raise e
            if not val:
                values[i] = 0
            else:
                values[i] = val
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
               'paralysis_chance_boost', 'paralysis_chance_resist', 'paralysis_duration_boost',
               'paralysis_duration_resist', 'paralysis_duration_boost_2', 'paralysis_duration_reduction',
               'paralysis_chance_reduction', 'curio_dmg_taoist', 'curio_dmg_reduction', 'p_hit', 'p_eva', 'm_hit',
               'm_eva', 'dmg_bonus_monsters', 'monster_dmg_reduction', 'curio_dmg_monster', 'curio_dmg_pet',
               'taoist_dmg_projection', 'law_suppression_boost', 'law_suppression_resist',
               'mortal_ability_dmg_reduction', 'res_mortal_effects', 'spiritual_ability_dmg_reduction',
               'res_spiritual_effects', 'spiritual_paralysis_resist', 'spiritual_blind_resist',
               'spiritual_silence_resist', 'spiritual_curse_resist', 'sense', 'mspd', 'physique', 'agility',
               'manipulation', 'occult_figure', 'hp_regen', 'mp_regen', 'projection_resist_taoist_dmg']
        x_offset = 280 if self.own_character else 580

        if not self.screen.find("character_scraper/stat_state"):
            self.screen.tap(1000, 1800)
            self.screen.wait_for_state("../character_scraper/stat_state")

        path = "tmp/stat_scrollshot.png"
        self.screen.capture_scrollshot(path, 200, 250,
                                       (640, 1300, 640, 1200), (0, 1080, 800, 1700))

        x, y_origin = self.get_start_loc(path, 'stats/hp', x_offset)
        # For each identifier (in order)
        values = {}
        n_reset = 6
        for idx, i in enumerate(ids):
            logger.debug(f"[scrape_stats_stats] Finding value for '{i}'")
            # Update start value every n_reset items to prevent drift
            if idx % n_reset == 0:
                x, y_origin = self.get_start_loc(path, f'stats/{i}', x_offset)
            y = y_origin + (idx % n_reset) * 122
            try:
                val = self.get_value(path, x, y)
            except Exception as e:
                logger.error(f"Failed to find general stat {i} at x={x}, y={y}")
                raise e
            if not val:
                values[i] = 0
            else:
                values[i] = val
        return values

    def scrape(self):
        """ Scrapes """
        full_stats = {}
        logger.info("Starting character scrape")
        try:
            # Get character identifying information
            full_stats.update(self.scrape_name())
            # Get the relic items if looking at different character
            if not self.own_character:
                full_stats.update(self.scrape_relics())
                logger.info("Collected relic values")
            else:
                logger.info("Skipped relic values as looking at own character")
            # Open compare screen by clicking the button
            self.screen.tap_button("../character_scraper/compare_button")
            # Set screen masking and filtering
            self.screen.filter_notifications = True
            self.screen.green_select = (590, 1080, 800, 900)
            # Get the total BR
            full_stats.update(self.scrape_total_br())
            # Sweep through all the compare BR value
            full_stats.update(self.scrape_br_stats())
            logger.info("Collected BR values")
            # Sweep through all the compare STAT values
            full_stats.update(self.scrape_stat_stats())
            logger.info("Collected stat values")
        except Exception as e:
            self.screen.back()
            raise e
        logger.info("Finished character scrape")
        self.screen.back()
        return full_stats


if __name__ == "__main__":
    own_char = False
    ref_file = 'moonlitmoo.json' if own_char else 'lieunhuvan.json'

    with open(ref_file, 'r') as file:
        exact = json.load(file)

    times = []
    error = []
    for i in range(10):
        s_time = time.perf_counter()
        stats = CharacterScraper(own_character=own_char).scrape()
        times.append(time.perf_counter() - s_time)

        print("Differing items")
        wrong = 0
        for k, v in stats.items():
            if k not in exact:
                print(f'Missing exact value for {k}: {v}')
                continue
            if isinstance(v, str):
                if exact[k] != v:
                    wrong += 1
                    print(f"Found {k}: {v}, previously {exact[k]}")
                continue
            if exact[k] == 0 and v != exact[k]:
                wrong += 1
                print(f"Found {k}: {v}, previously {exact[k]}")
            elif exact[k] != 0 and abs(v / exact[k] - 1) > 0.01:  # Check within 1%
                wrong += 1
                print(f"Found {k}: {v}, previously {exact[k]} off by {v / exact[k] * 100 - 100:3.1f}%")
        for k, _ in exact.items():
            if k not in stats:
                print(f"Missing scraped value for {k}")
        print(f"Test {i} incorrect {wrong / len(stats) * 100:3.1f}%")
        error.append(wrong / len(stats))

    print(f"Average error {np.average(error) * 100:3.1f}% with std {np.std(error) * 100:1.2f}%")
    print(f"Average time {np.average(times):3.1f}s with std {np.std(error):2.2f}s%")
