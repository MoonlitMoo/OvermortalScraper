import cv2
import numpy as np

def locate_image(img1, img2, threshold: float):
    """ Locates top left of given image and returns it (None if not found).
    Expects preprocessed images.
    """
    res = cv2.matchTemplate(img1, img2, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    if max_val >= threshold:
        return max_loc, max_val
    return None


def locate_area(img1, img2, threshold: float):
    """ Returns area (x1, x2, y1, y2) of an image in pixel coordinates or None if not found.
    Expects preprocessed images.
    """
    result = locate_image(img1, img2, threshold)
    if result is None: return None
    y_len, x_len = img2.shape
    x, y = result[0]
    return x, x + x_len, y, y + y_len

