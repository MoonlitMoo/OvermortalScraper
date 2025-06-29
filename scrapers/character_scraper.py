import re
import time

import cv2
import jellyfish

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
        """ Retrieves the name of the taoist.
        Uses the name found in the report screen as doesn't have a changeable background and won't be interfered with by
        the sect name.

        Returns
        -------
        dict
            {Name : value} pairing
        """
        # Open report screen by tapping more and report
        self.screen.tap(200, 1225)
        time.sleep(0.1)
        self.screen.tap(400, 990)
        time.sleep(0.1)
        # Capture text of name
        img = self.screen.update()
        all_text = self.processor.extract_text_from_area(
            img, (100, 950, 550, 650), all_text=True, use_name_reader=True)
        # Sanitise the name
        text = ' '.join(all_text).split("player:")[-1].lower().strip().encode(errors='replace').decode()
        logger.debug(f"Scraped name '{text}'")
        # Go back to home screen
        self.screen.tap(500, 1500)
        time.sleep(0.1)
        self.screen.tap(500, 1500)
        logger.info("[SCRAPE_NAME] Scraped name")
        return {"name": text}

    def scrape_total_br(self):
        """ Get the total BR from the compare BR screen.
        Assumes screen is open when scraping.

        Returns
        -------
        dict
            {total_br : value} pair
        """
        img = self.screen.update()
        value = self.processor.extract_text_from_area(img, (820, 1000, 250, 300))
        logger.debug(f"[SCRAPE_TOTAL_BR] Found '{value}' and parsed as '{parse_text_number(value)}'")
        logger.info(f"[SCRAPE_TOTAL_BR] Finished")
        return {"total_br": parse_text_number(value)}

    def scrape_cultivation(self):
        """ Retrieves cultivation and daemonfae levels from the two details screens.
        Pulls the stage and minor stage (early, middle, late) for cultivation. Same for daemonfae, but also gets the
        alignment.

        Returns
        -------
        dict
            key: value for all levles
        """
        # Make sure we are on compare br screen
        if not self.screen.find("character_scraper/br_state"):
            self.screen.tap(800, 1800)
            self.screen.wait_for_state("../character_scraper/br_state")
        # Find the character details and click it
        self.screen.update()
        try:
            _, character_y = self.get_start_loc(self.screen.CURRENT_SCREEN, 'br/character', 0)
        except Exception:
            logger.error("[SCRAPE_CULTIVATION] Failed to find character details")
            return {}
        detail_x, detail_y_offset = 900, 20
        self.screen.tap(detail_x, character_y + detail_y_offset)
        time.sleep(0.25)

        result = {}
        # Get the 4 cultivation levels and go back
        img = self.screen.update()
        cultivation_area = (250, 490, 950, 1300) if self.own_character else (700, 1000, 950, 1300)
        text = ' '.join(self.processor.extract_text_from_area(
            img, cultivation_area, all_text=True, faint_text=self.own_character))
        label_to_name = {"M": "magicka", "C": "corporia", "S": "swordia", "G": "ghostia"}
        for level in CultivationLevel:
            if level == CultivationLevel.NOVICE:
                # Match: e.g., "Novice (G)" — no stage required
                pattern = rf'\b({re.escape(level.value)})\s*\(\s*([A-Z])\s*\)'
            else:
                # Match: e.g., "Voidbreak (M) Early"
                pattern = rf'\b({re.escape(level.value)})\s*\(\s*([A-Z])\s*\)\s*(early|middle|late)'
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                level_str, label = groups[0], groups[1].upper()
                stage = groups[2].lower() if len(groups) > 2 else None

                if label in label_to_name:
                    name = label_to_name[label]
                    result[f"{name}_stage"] = CultivationLevel[level_str.upper()].value
                    result[f"{name}_minor_stage"] = stage.upper() if stage else None
        self.screen.tap(100, 1800)
        time.sleep(.25)

        # Scroll to Daemonfae and open details
        daemonfae_y, _iter = None, 0
        while not daemonfae_y and _iter < 5:
            try:
                self.screen.update()
                _, daemonfae_y = self.get_start_loc(self.screen.CURRENT_SCREEN, 'br/daemonfae', 0)
            except:
                self.screen.swipe(820, 1300, 820, 1000)
                _iter += 1
                time.sleep(1)
        self.screen.tap(detail_x, daemonfae_y + detail_y_offset)
        time.sleep(.25)
        logger.debug(f"[SCRAPE_CULTIVATION] Found daemonfae location {detail_x}, {daemonfae_y + detail_y_offset}")
        # Read stage + alignment
        img = self.screen.update()
        daemonfae_area = (250, 490, 960, 1050) if self.own_character else (700, 1000, 960, 1050)
        text = ' '.join(self.processor.extract_text_from_area(
            img, daemonfae_area, all_text=True, faint_text=self.own_character))
        logger.debug(f"[SCRAPE_CULTIVATION] Read daemonfae text '{text}'")
        # Match e.g., "Demon IV (Late)" or "Divinity 5 (Early)"
        pattern = r'\b([A-Za-z]+)\s+([IVX]+|\d+)\s*\(\s*(early|middle|late)\s*\)'
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            raise ValueError("Could not parse daemonfae alignment string.")

        alignment, stage_raw, minor_stage = match.groups()
        # Convert stage to integer (roman or numeric)
        roman_to_int = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}
        stage_raw_upper = stage_raw.upper()
        if stage_raw_upper in roman_to_int:
            stage = roman_to_int[stage_raw_upper]
        elif stage_raw.isdigit():
            stage = int(stage_raw)
        else:
            raise ValueError(f"Unrecognized stage value: {stage_raw}")
        result.update({
            "alignment": alignment.upper(),
            "daemonfae_stage": stage,
            "daemonfae_minor_stage": minor_stage.upper()
        })
        self.screen.tap(100, 1800)
        time.sleep(.25)
        logger.debug(f"Parsed levels '{result}'")
        return {}

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
            logger.debug(f"Getting curio_{i + 1}")
            values[f"curio_{i + 1}"] = self.scrape_item(col2, r, Curio, full_match=True)

        # General relics
        i = 0
        for c in [col1, col2]:
            for r in [880, 1000, 1130]:
                i += 1
                logger.debug(f"Getting relic_{i}")
                values[f"relic_{i}"] = self.scrape_item(c, r, Relic)
        logger.info("[SCRAPE_RELICS] Finished scraping relics")
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

        logger.debug("[SCRAPE_BR_STATS] Starting scrollshot")
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
        logger.info("[SCRAPE_BR_STATS] Finished scraping")
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

        logger.debug("[SCRAPE_STAT_STATS] Starting scrollshot")
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
        logger.debug("[SCRAPE_STAT_STATS] Finished scraping")
        return values

    def scrape(self):
        """ Scrapes full character stats """
        full_stats = {}
        logger.info("[SCRAPE] Starting character scrape")
        try:
            if not self.own_character:
                # Get character identifying information
                # Get the relic items if looking at different character
                full_stats.update(self.scrape_name())
                full_stats.update(self.scrape_relics())
            else:
                logger.info("[SCRAPE] Skipped relic and name values as looking at own character")
            # Open compare screen by clicking the button
            self.screen.tap_button("../character_scraper/compare_button")
            # Set screen masking and filtering
            self.screen.filter_notifications = True
            self.screen.green_select = (590, 1080, 800, 900)
            # Get the total BR
            full_stats.update(self.scrape_total_br())
            # Get the cultivation and daemonfae
            full_stats.update(self.scrape_cultivation())
            # Sweep through all the compare BR value
            full_stats.update(self.scrape_br_stats())
            # Sweep through all the compare STAT values
            full_stats.update(self.scrape_stat_stats())
        except Exception as e:
            self.screen.back()
            raise e
        logger.info("[SCRAPE] Finished character scrape")
        self.screen.back()
        return full_stats
