import re

import cv2
import numpy as np
from pytesseract import pytesseract


def parse_text_number(text: str) -> float:
    """
    Parse a text like '1.38M' or '421.38K' and return the number as a float.

    Parameters
    ----------
    text : str
        Text containing two numbers separated by '+'.

    Returns
    -------
    float
        The sum of the two numbers.
    """
    # Regular expression to find numbers with optional 'K' or 'M'
    pattern = r'([\d\.]+)([TBMK]?)'
    match = re.match(pattern, text)

    if not match:
        raise ValueError(f"Could not parse numbers from: {text}")

    number, suffix = match.groups()
    num = float(number)
    match suffix:
        case 'T':
            num *= 1_000_000_000_000
        case 'B':
            num *= 1_000_000_000
        case 'M':
            num *= 1_000_000
        case 'K':
            num *= 1_000
    return num


class ScreenshotProcesser:

    def __init__(self):
        pass

    def extract_text_from_area(self, img: str | np.ndarray, area: tuple, psm: int = 6, thresholding: bool = True,
                               dilate: bool = False, debug: bool = False) -> str:
        """
        Extract text from a specific rectangular area of an image.

        Parameters
        ----------
        img : str | array
            Path to the input image file or image itself.
        area : tuple
            (x1, y1, x2, y2) specifying the crop rectangle.
        psm : int, optional
            Page Segmentation Mode for Tesseract (default 6 = block of text).
        thresholding : bool, optional
            Whether to apply thresholding before OCR (default True).
        dilate : bool, optional
            Whether to apply dilation before OCR (default True)
        debug : bool, optional
            To show the selected image / area

        Returns
        -------
        str
            Extracted text from the specified area.
        """
        # Load image if necessary
        if isinstance(img, str):
            img = cv2.imread(img)
        if not isinstance(img, np.ndarray):
            raise TypeError(f"Unknown img type {type(img)}")

        # Crop area
        x1, x2, y1, y2 = area
        crop = img[y1:y2, x1:x2]

        # Preprocess
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        if thresholding:
            _, proc = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        else:
            proc = gray

        if dilate:
            kernel = np.ones((2, 2), np.uint8)
            proc = cv2.dilate(proc, kernel, iterations=1)

        if debug:
            cv2.imshow("OCR Preprocess", proc)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

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
            basic_effects[effect] = sum(parse_text_number(val) for val in value.split(' '))

        print(f"Found title text {raw_title_text} -> {title_text}")
        print(f"Found basic text {raw_basic_text} -> {basic_effects}")
