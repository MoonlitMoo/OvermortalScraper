import re
import time

import cv2
import jellyfish
import numpy as np

from models.cultivation import CultivationMinorStage
from screen import Screen
from service.char_scraper_service import CharacterScraperService
from scrapers.screenshot_processor import ScreenshotProcesser, parse_text_number
from image_functions import locate_area


class CharacterScraper:
    """ From the character select screen, retrieves all stats of a character found within the "Compare BR" tab.

    Attributes
    ----------
    screen : Screen
        The instance to interact with emulator with.
    service : CharacterScraperService
        Interact with database for this scraper specific needs.
    processor : ScreenshotProcesser
        OCR processor for screenshots.
    self.logger : self.logger
        The self.logger to output to
    own_character : bool
        Toggle for scraping own stats from Compare BR
    SIMILARITY_THRESHOLD : float
       Constant to use for OCR similarity metrics between words.
    """

    def __init__(self, screen: Screen, service: CharacterScraperService, processor: ScreenshotProcesser,
                 logger, own_character: bool = False):
        self.screen = screen
        self.service = service
        self.processor = processor
        self.logger = logger
        self.own_character = own_character
        self.SIMILARITY_THRESHOLD = 0.85

    def get_start_loc(self, screenshot_path, template_path, x_offset):
        """ Gets location of button given the search condition.

        Parameters
        ----------
        screenshot_path : str
            The image path to load and search
        template_path : str
            The image to search for
        x_offset : int
            Offset to apply to x coordinate
        """
        # Find location
        full_img = cv2.imread(screenshot_path)
        template_img = cv2.cvtColor(cv2.imread(f'resources/character_scraper/{template_path}.png'), cv2.COLOR_BGR2GRAY)

        text_area = locate_area(cv2.cvtColor(full_img, cv2.COLOR_BGR2GRAY), template_img, 0.9)
        if text_area is None:
            self.logger.debug(f"Failed to get image '{template_path}'")
            return None

        box_y_offset = -40

        centre_y = (text_area[2] + text_area[3]) / 2
        start_y = int(centre_y + box_y_offset)
        start_x = int(text_area[0] + x_offset)

        return start_x, start_y

    def get_value(self, screenshot_path, start_x, start_y, debug=False):
        """ Gets the value from a saved image and search location. """
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
            self.logger.advdebug(f"Retrieved text '{value}' as '{parse_text_number(value)}")
            return parse_text_number(value)
        except ValueError:
            self.logger.advdebug(f"Retrieved text '{value}' as '0'")
            return 0

    def validate_string(self, value: str, valid_strings: list, str_desc: str):
        """ Returns a valid string from the given list. Uses closest match if not exact.
        Gives warning if closest match is not close.

        Parameters
        ----------
        value : str
            String to validate
        valid_strings : list of str
            The valid strings to match to
        str_desc : str
            A string describing what the value represents.

        Returns
        -------
        str
        """
        if value in valid_strings:
            return value, 1

        similarities = [jellyfish.jaro_winkler_similarity(a, value) for a in valid_strings]
        index = similarities.index(max(similarities))
        if max(similarities) < self.SIMILARITY_THRESHOLD:
            self.logger.warning(f"Unknown {str_desc} '{value}'")
        self.logger.debug(f"Unknown {str_desc} '{value}' "
                          f"using '{valid_strings[index]}' with similarity {similarities[index]:.3f}")
        return valid_strings[index], max(similarities)

    def scrape_item(self, x: int, y: int, valid_names: list, item_type: str, full_match=False, check_double_path=False):
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
        valid_names : list
            A list of accepted names the item should belong to
        item_type : str
            Description of item type
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
        If no matching enum is found, a debug image of the item is captured and self.logger is given a warning.
        """
        # Select item
        self.screen.tap(x, y)
        time.sleep(0.75)

        # Read text
        img = self.screen.update()
        name_bbox = (300, 1000, 250, 420)

        all_text = self.processor.extract_text_from_area(img, name_bbox, all_text=True)
        # Join all the text and rely on enhancement to split off the name
        # Otherwise (no enhancement) just assume that the first found value is probably correct
        if "+" in ' '.join(all_text):
            full_name = ' '.join(all_text).split("+")[0].strip()
        else:
            full_name = all_text[0]

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
        valid_names = valid_names if isinstance(valid_names, list) else [e.value for e in valid_names]
        item, sim = self.validate_string(test_name, valid_names, item_type)
        if sim < self.SIMILARITY_THRESHOLD:
            self.screen.capture(f"debug/unknown_item_{test_name}.png", update=False)

        # Return back to main screen
        self.screen.tap(500, 1800)
        self.screen.wait_for_state("../buttons/character_screen/pet")
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
        # Open report screen by tapping more and report buttons
        self.screen.tap(200, 1225)
        time.sleep(0.1)
        if not self.screen.tap_button("character_screen/report"):
            self.logger.warning("Failed to get to report screen")
            return {}
        time.sleep(0.1)
        # Capture text of name
        img = self.screen.update()
        all_text = self.processor.extract_text_from_area(
            img, (100, 950, 550, 650), all_text=True, use_name_reader=True)
        # Sanitise the name
        text = ' '.join(all_text).split("player:")[-1].lower().strip().encode(errors='replace').decode()
        # Go back to home screen
        self.screen.tap(500, 1500)
        time.sleep(0.1)
        self.screen.tap(500, 1500)
        self.logger.info(f"Scraped name '{text}'")
        return {"name": text}

    def scrape_pets(self):
        """ Scrapes equipped pet name and level. """
        self.screen.tap_button("character_screen/pet")
        self.screen.wait_for_state("character_screen/pet_formation")

        # Iterate through the locations
        results = {}
        cols = [190, 445, 700]
        width = 190
        reference_colours = [
            ("common", (215, 215, 215)),
            ("uncommon", (103, 185, 96)),
            ("rare", (83, 151, 199)),
            ("epic", (163, 82, 203)),
            ("legendary", (255, 189, 26)),
            ("mythic", (239, 41, 50)),
        ]
        # Invert image to get dark text with light border.
        img = self.screen.update()
        inverted_img = cv2.bitwise_not(img)
        valid_pets = self.service.get_pet_names()
        # Zip the column to the formation array position
        for x, i in zip(cols, ("front", "left", "right")):
            # Send to upper to match db
            val = self.processor.extract_text_from_area(inverted_img, (x, x + width, 1080, 1110)).upper()
            val, _ = self.validate_string(val, valid_pets, "PET")
            # Calculate the closest colour to get rarity
            colour = img[1190, x + int(width / 2)][::-1]  # Reverse since BGR by default
            colour_distance = [
                (label, np.linalg.norm(colour - np.array(ref_rgb)))
                for label, ref_rgb in reference_colours
            ]
            rarity = min(colour_distance, key=lambda x: x[1])[0].upper()
            results[f"pet_{i}_id"] = self.service.get_pet_id(val)
            results[f"pet_{i}_rarity"] = rarity
            self.logger.advdebug(f"Found {val} of rarity {rarity}")

        self.logger.debug("Finished scraping")
        # Exit pet screen and wait until we can see the button again
        self.screen.tap(500, 1500)
        self.screen.wait_for_state("../buttons/character_screen/pet")
        return results

    def scrape_total_br(self):
        """ Get the total BR from the compare BR screen.
        Assumes screen is open when scraping.

        Returns
        -------
        dict
            {total_br : value} pair
        """
        # Make sure we are on compare br screen
        if not self.screen.find("character_scraper/br_state"):
            self.screen.tap(800, 1800)
            self.screen.wait_for_state("../character_scraper/br_state")
        img = self.screen.update()
        value = self.processor.extract_text_from_area(img, (820, 1000, 250, 300))
        self.logger.debug(f"Found '{value}' and parsed as '{parse_text_number(value)}'")
        self.logger.info(f"Finished")
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
            self.logger.error("Failed to find character details")
            return {}
        detail_x, detail_y_offset = 900, 20
        self.screen.tap(detail_x, character_y + detail_y_offset)
        self.screen.wait_for_state("character_screen/cultivation_exp")

        result = {}
        # Get the 4 cultivation levels and go back
        img = self.screen.update()
        cultivation_x = (250, 490) if self.own_character else (700, 1000)
        stage_names = self.service.get_cultivation_stages()
        minor_stage_names = [v.value for v in CultivationMinorStage]
        # Iterate through the different cultivation blocks
        for y, name in zip([1010, 1100, 1185, 1270], ["magicka", "corporia", "swordia", "ghostia"]):
            area = (*cultivation_x, y - 40, y + 40)
            text = ' '.join(self.processor.extract_text_from_area(
                img, area, all_text=True, faint_text=self.own_character))
            # Get the stage
            stage = text.split(' ')[0].upper()
            stage, _ = self.validate_string(stage, stage_names, "CULTIVATION_STAGE")
            stage_id = self.service.get_cultivate_stage_id(stage)
            minor_stage = None
            # If not novice, try minor stage on all text blocks
            if stage_id != 1:
                text_parts = [t.upper() for t in text.split(' ')]
                for ms in minor_stage_names:
                    if ms in text_parts:
                        minor_stage = ms
                        break
                if minor_stage is None:
                    self.logger.warning(f"Missing minor stage for {stage}")

            result[f"{name}_stage_id"] = stage_id
            result[f"{name}_minor_stage"] = minor_stage
        self.screen.tap(100, 1800)

        # Scroll to Daemonfae and open details
        daemonfae_y, _iter = None, 0
        while not daemonfae_y and _iter < 5:
            try:
                self.screen.update()
                _, daemonfae_y = self.get_start_loc(self.screen.CURRENT_SCREEN, 'br/daemonfae', 0)
            except:
                self.screen.swipe(820, 1300, 820, 1000)
                self.screen.tap(820, 1300)  # Stop the scroll
                _iter += 1
        self.screen.tap(detail_x, daemonfae_y + detail_y_offset)
        self.screen.wait_for_state("character_screen/daemonfae_exp")

        # Read stage + alignment
        img = self.screen.update()
        daemonfae_area = (250, 490, 960, 1050) if self.own_character else (700, 1000, 960, 1050)
        text = ' '.join(self.processor.extract_text_from_area(
            img, daemonfae_area, all_text=True, faint_text=self.own_character))
        self.logger.debug(f"Read daemonfae text '{text}'")
        # Match e.g., "Demon IV (Late)" or "Divinity 5 (Early)"
        pattern = r'\b([A-Za-z]+)\s+([IVX]+|\d+)\s*\(\s*(early|middle|late)\s*\)'
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            raise ValueError(f"Could not parse daemonfae alignment string {text}.")

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
        alignment = alignment if alignment.upper() != "DIVINITY" else "DIVINE"
        result.update({
            "alignment": alignment.upper(),
            "daemonfae_stage": stage,
            "daemonfae_minor_stage": minor_stage.upper()
        })
        self.screen.tap(100, 1800)
        time.sleep(.25)
        self.logger.debug(f"Parsed levels '{result}'")
        self.logger.info("Finished scraping")
        return result

    def scrape_abilities(self):
        """ Retrieves equipped abilities from the compare BR screen

        Returns
        -------
        dict
            key: value for all levels
        """
        # Make sure we are on compare br screen
        if not self.screen.find("character_scraper/br_state"):
            self.screen.tap(800, 1800)
            self.screen.wait_for_state("../character_scraper/br_state")
        # Find the ability details and click it
        self.screen.update()
        try:
            _, character_y = self.get_start_loc(self.screen.CURRENT_SCREEN, 'br/ability', 0)
        except Exception:
            self.logger.error("Failed to find character details")
            return {}
        detail_x, detail_y_offset = 900, 20
        self.screen.tap(detail_x, character_y + detail_y_offset)
        self.screen.wait_for_state("character_screen/ability_equipped")

        # Read all the 6 abilities
        results = {}
        rows = [540, 705, 860]
        cols = [1005, 1215]
        x_len, y_len = 160, 95
        # Colour invert so that the light words with dark border -> dark words with light border
        img = self.screen.update()
        img = cv2.bitwise_not(img)
        i = 0
        valid_abilities = self.service.get_ability_names()
        for x in rows:
            for y in cols:
                # Tends to work best with thresholding, sending to lower case to match db
                val = ' '.join(self.processor.extract_text_from_area(img, (x, x + x_len, y, y + y_len),
                                                                     all_text=True, thresholding=True)).lower()
                val, _ = self.validate_string(val, valid_abilities, "ABILITY")
                results[f"ability_{i}_id"] = self.service.get_ability_id(val)
                i += 1
        # Hit back button
        self.screen.tap(100, 1800)
        time.sleep(.25)
        self.logger.info("Finished scraping")
        return results

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
        self.logger.debug(f"Getting weapon")
        values["weapon_id"] = self.service.get_relic_id(
            self.scrape_item(
                col1, row1, self.service.get_relic_names("WEAPON"), "RELIC_WEAPON", check_double_path=True),
            "WEAPON"
        )
        # Armour
        self.logger.debug(f"Getting armour")
        values["armour_id"] = self.service.get_relic_id(
            self.scrape_item(
                col1, row2, self.service.get_relic_names("ARMOR"), "RELIC_ARMOR", check_double_path=True),
            "ARMOR"
        )
        # Accessory
        self.logger.debug(f"Getting accessory")
        values["accessory_id"] = self.service.get_relic_id(
            self.scrape_item(
                col1, row3, self.service.get_relic_names("ACCESSORY"), "RELIC_ACCESSORY", check_double_path=True),
            "ACCESSORY"
        )

        # Curio
        curios = self.service.get_curio_names()
        for i, r in enumerate([row1, row2, row3]):
            self.logger.debug(f"Getting curio_{i + 1}")
            values[f"curio_{i + 1}_id"] = self.service.get_curio_id(
                self.scrape_item(col2, r, curios, "CURIO", full_match=True))

        # General relics
        general_relics = self.service.get_relic_names("GENERAL")
        i = 0
        for c in [col1, col2]:
            for r in [880, 1000, 1130]:
                i += 1
                self.logger.debug(f"Getting relic_{i}")
                values[f"relic_{i}_id"] = self.service.get_relic_id(
                    self.scrape_item(c, r, general_relics, "GENERAL_RELIC"), "GENERAL")
        self.logger.info("Finished scraping relics")
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

        self.logger.debug("Starting scrollshot")
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
                self.logger.error(f"Failed to find BR stat {i} at x={x}, y={y}")
                raise e
            if not val:
                values[i] = 0
            else:
                values[i] = val
        self.logger.info("Finished scraping")
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

        self.logger.debug("Starting scrollshot")
        path = "tmp/stat_scrollshot.png"
        self.screen.capture_scrollshot(path, 200, 250,
                                       (640, 1300, 640, 1200), (0, 1080, 800, 1700))

        x, y_origin = self.get_start_loc(path, 'stats/hp', x_offset)
        # For each identifier (in order)
        values = {}
        n_reset = 6
        for idx, i in enumerate(ids):
            self.logger.advdebug(f"Finding value for '{i}'")
            # Update start value every n_reset items to prevent drift
            if idx % n_reset == 0:
                x, y_origin = self.get_start_loc(path, f'stats/{i}', x_offset)
            y = y_origin + (idx % n_reset) * 122
            try:
                val = self.get_value(path, x, y)
            except Exception as e:
                self.logger.error(f"Failed to find general stat {i} at x={x}, y={y}")
                raise e
            if not val:
                values[i] = 0
            else:
                values[i] = val
        self.logger.debug("Finished scraping")
        return values

    def scrape(self):
        """ Scrapes full character stats """
        full_stats = {}
        self.logger.info("Starting character scrape")
        try:
            if not self.own_character:
                # Get character identifying information
                # Get the relic items if looking at different character
                full_stats.update(self.scrape_name())
                full_stats.update(self.scrape_relics())
                full_stats.update(self.scrape_pets())
            else:
                self.logger.info("Skipped relic and name values as looking at own character")
            # Open compare screen by clicking the button
            time.sleep(0.25)
            if not self.screen.tap_button("character_screen/compare_button"):
                self.logger.warning("Failed to click compare br button")
                return {}
            # Set screen masking and filtering
            self.screen.filter_notifications = True
            self.screen.green_select = (590, 1080, 800, 900)
            # Get the total BR
            full_stats.update(self.scrape_total_br())
            # Get the cultivation and daemonfae
            full_stats.update(self.scrape_cultivation())
            # Get equipped abilities
            full_stats.update(self.scrape_abilities())
            # Sweep through all the compare BR value
            full_stats.update(self.scrape_br_stats())
            # Sweep through all the compare STAT values
            full_stats.update(self.scrape_stat_stats())
        except Exception as e:
            self.screen.back()
            raise e
        self.logger.info("Finished character scrape")
        self.screen.back()
        return full_stats
