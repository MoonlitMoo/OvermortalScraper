import os
import time

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

    def get_value(self, template_path: str, x_offset: int, scroll_x: int) -> float:
        """ Takes an image of the description and uses the location to find the corresponding enemy value.

        Parameters
        ----------
        template_path : str
            The text image to search for
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
        If we can't find it, then we scroll down a bit and retry.
        Then we try parse the value in the image, setting to 0 if none found.
        """
        box_width = 230
        box_height = 50
        box_y_offset = -40
        # Find location
        text_area = self.screen.find_area(template_path)

        # If we haven't found it, scroll down and try again
        _iter = 0
        while text_area is None and _iter < 5:
            _iter += 1
            self.screen.swipe(scroll_x, 1200, scroll_x, 1100)
            time.sleep(0.2)
            logger.debug(f"Scolled down to find {template_path}")
            text_area = self.screen.find_area(template_path)

        if text_area is None:
            return None

        # The search area should start at text_x + x_offset, with y being the centre of text image + y offset
        centre_y = (text_area[2] + text_area[3]) / 2
        start_y = int(centre_y + box_y_offset)
        start_x = int(text_area[0] + x_offset)
        search_area = (start_x, start_x + box_width, start_y - int(box_height / 2), start_y + int(box_height / 2))
        # Grab the value
        value = self.processer.extract_text_from_area(self.screen.colour(), area=search_area, psm=7, debug=True)
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

        # For each identifier (in order)
        values = {}
        for i in ids:
            val = self.get_value(f"character_scraper/br/{i}", x_offset, 820)
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
        try:
            self.screen.tap_button("../character_scraper/compare_button")
            logger.info("Opened Stats")
            # Set screen masking and filtering
            self.screen.filter_notifications = True
            self.screen.green_select = (590, 1080, 700, 900)
            # Sweep through all the compare BR value
            # self.scrape_br_stats()
            # logger.info("Collected BR values")
            # Sweep through all the compare STAT values
            self.scrape_stat_stats()
            logger.info("Collected stat values")
            # Compile into a database.
        except Exception as e:
            self.screen.back()
            raise e
        self.screen.back()


CharacterScraper(own_character=False).scrape()
