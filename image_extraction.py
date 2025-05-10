import cv2

from screen import Screen

screen = Screen(None)
OUTPUT_PATH = 'extracted.png'


def draw_grid(grid_size=100, line_color=(0, 255, 0), text_color=(0, 0, 255), thickness=1, file=None):
    """ Draws grid over current captured screenshot. """
    # Load image
    if file is None:
        img = screen.update()
    else:
        img = cv2.imread(file)
    height, width = img.shape[:2]

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    font_thickness = 1

    # Draw vertical lines and labels
    for x in range(0, width, grid_size):
        cv2.line(img, (x, 0), (x, height), line_color, thickness)
        cv2.putText(img, str(x), (x + 2, 24), font, font_scale, text_color, font_thickness)

    # Draw horizontal lines and labels
    for y in range(0, height, grid_size):
        cv2.line(img, (0, y), (width, y), line_color, thickness)
        cv2.putText(img, str(y), (2, y + 24), font, font_scale, text_color, font_thickness)

    cv2.imwrite("screen-gridded.png", img)


def extract_section(x1, x2, y1, y2, file=screen.CURRENT_SCREEN):
    """ Extract the section in gray scale. """
    img = cv2.cvtColor(cv2.imread(file), cv2.COLOR_BGR2GRAY)
    # Crop the "Event" region (manual pixel coords)
    crop = img[y1:y2, x1:x2]  # Example: img[60:95, 90:150]
    cv2.imwrite(OUTPUT_PATH, crop)


def debug_template_match():
    """ Checks if we can locate the extracted image from the screen """
    max_loc, max_val = screen._locate_image(OUTPUT_PATH)

    if max_loc:
        img = cv2.imread(screen.CURRENT_SCREEN, cv2.IMREAD_COLOR)
        template = cv2.imread(OUTPUT_PATH, cv2.IMREAD_COLOR)
        h, w = template.shape[:2]
        cv2.rectangle(img, max_loc, (max_loc[0] + w, max_loc[1] + h), (0, 255, 0), 2)

        scale = 0.5  # 50% size
        img = cv2.resize(img, None, fx=scale, fy=scale)
        cv2.imshow(f'Match Found (value={max_val:.3f})', img)
        cv2.waitKey(0)
    else:
        print("No match found.")


draw_grid()
extract_section(400, 670, 1520, 1670)
debug_template_match()
