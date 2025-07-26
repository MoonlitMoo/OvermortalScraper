import cv2
import numpy as np

from skimage.metrics import structural_similarity as ssim


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


def similar_images(img1, img2, threshold=0.8):
    """
    Compare two images using SSIM to detect similarity.
    """
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    similarity, _ = ssim(gray1, gray2, full=True)

    return similarity > threshold


def stitch_images(img1, img2, overlap, offset: int = 0):
    """ Stitches second image onto the first assuming they have an overlap. """
    template = img1[-overlap - offset:-offset]
    result = cv2.matchTemplate(img2, template, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(result)
    match_y = max_loc[1]
    img2_aligned = img2[match_y + overlap:]
    return np.vstack((img1[:-offset], img2_aligned))
