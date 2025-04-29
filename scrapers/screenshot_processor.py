import re

import cv2
from pytesseract import pytesseract


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


class ScreenshotProcesser:

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
