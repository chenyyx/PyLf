"""The core module"""
import math
import multiprocessing
import random

from PIL import Image as image
from PIL import ImageDraw as image_draw

from pylf import _page

# Chinese, English and other end chars
_DEFAULT_END_CHARS = set("，。》、？；：’”】｝、！％）" + ",.>?;:]}!%)" + "′″℃℉")

# While changing following constants, it is necessary to consider to rewrite the relevant codes.
_INTERNAL_MODE = 'L'  # The mode for internal computation
_WHITE = 255
_BLACK = 0
_AMP = 2  # Amplification for 4X SSAA.


def handwrite(text, template: dict, anti_aliasing: bool = True, worker: int = 0, seed: int = None) -> list:
    """Handwrite the text with the parameters in the template.

    Args:
        text: A char iterable.
        template: A dict containing following parameters.
            background: A Pillow's Image instance.
            box: A bounding box as a 4-tuple defining the left, upper, right, and lower pixel coordinate. The module
                uses a Cartesian pixel coordinate system, with (0,0) in the upper left corner. Note that this function
                do not guarantee the drawn texts will completely in the box.
            font: A Pillow's font instance. Note that this function do not use the size attribute of the font instance.
            font_size: A int as the average font size in pixel. Note that (box[3] - box[1]) and (box[2] - box[0]) both
                must be greater than font_size.
            color: A str with specific format. The format is given as 'rgb(red, green, blue)' where the color values are
                integers in the range 0 (inclusive) to 255 (inclusive). Default: 'rgb(0, 0, 0)'.
            word_spacing: A int as the average gap between two adjacent chars in pixel. Default: 0.
            line_spacing: A int as the average gap between two adjacent lines in pixel. Default: font_size // 5.
            font_size_sigma: A float as the sigma of the gauss distribution of the font size. Default: font_size / 256.
            word_spacing_sigma: A float as the sigma of the gauss distribution of the word spacing. Default:
                font_size / 256.
            line_spacing_sigma: A float as the sigma of the gauss distribution of the line spacing. Default:
                font_size / 256.
            is_half_char: A function judging whether or not a char only take up half of its original width. The function
                must take a char parameter and return a boolean value. Default: (lambda c: False).
            is_end_char: A function judging whether or not a char can NOT be in the beginning of the lines (e.g. '，',
                '。', '》', ')', ']'). The function must take a char parameter and return a boolean value. Default:
                (lambda c: c in _DEFAULT_END_CHARS).
            alpha: A tuple of two floats as the degree of the distortion in the horizontal and vertical direction in
                order. Both values must be between 0.0 (inclusive) and 1.0 (inclusive). Default: (0.1, 0.1).
        anti_aliasing: Whether or not turn on the anti-aliasing. Default: True.
        worker: A int as the number of worker. if worker is less than or equal to 0, the actual amount of worker would
            be the number of CPU in the computer adding worker. Default: 0.
        seed: A int as the seed of the internal random generators. Default: None.

    Returns:
        A list of drawn images with the same size and mode as the background image.

    Raises:
        ValueError: When the parameters are not be set properly.
    """
    page_setting = dict()
    page_setting['background'] = template['background']
    page_setting['box'] = template['box']
    page_setting['font_size'] = template['font_size']
    if 'word_spacing' in template: page_setting['word_spacing'] = template['word_spacing']
    if 'line_spacing' in template: page_setting['line_spacing'] = template['line_spacing']
    if 'font_size_sigma' in template: page_setting['font_size_sigma'] = template['font_size_sigma']
    if 'word_spacing_sigma' in template: page_setting['word_spacing_sigma'] = template['word_spacing_sigma']
    if 'line_spacing_sigma' in template: page_setting['line_spacing_sigma'] = template['line_spacing_sigma']

    template2 = dict()
    template2['page_settings'] = [page_setting, ]
    template2['font'] = template['font']
    if 'color' in template: template2['color'] = template['color']
    if 'is_half_char' in template: template2['is_half_char'] = template['is_half_char']
    if 'is_end_char' in template: template2['is_end_char'] = template['is_end_char']
    if 'alpha' in template: template2['alpha'] = template['alpha']

    return handwrite2(text, template2, anti_aliasing=anti_aliasing, worker=worker, seed=seed)


def handwrite2(text, template2: dict, anti_aliasing: bool = True, worker: int = 0, seed: int = None) -> list:
    """The 'periodic' version of handwrite. See also handwrite.

    Args:
        text: A char iterable.
        template2: A dict containing following parameters.
            page_settings: A list of dict containing the following parameters. Each of these dict will be applied
                cyclically to each page.
                background: A Pillow's Image instance.
                box: A bounding box as a 4-tuple defining the left, upper, right and lower pixel coordinate. The module
                    uses a Cartesian pixel coordinate system, with (0,0) in the upper left corner. This function do not
                    guarantee the drawn texts will completely in the box.
                font_size: A int as the average font size in pixel. Note that (box[3] - box[1]) and (box[2] - box[0])
                    both must be greater than font_size.
                word_spacing: A int as the average gap between two adjacent chars in pixel. Default: 0.
                line_spacing: A int as the average gap between two adjacent lines in pixel. Default: font_size // 5.
                font_size_sigma: A float as the sigma of the gauss distribution of the font size. Default:
                    font_size / 256.
                word_spacing_sigma: A float as the sigma of the gauss distribution of the word spacing. Default:
                    font_size / 256.
                line_spacing_sigma: A float as the sigma of the gauss distribution of the line spacing. Default:
                    font_size / 256.
            font: A Pillow's font instance. Note that this function do not use the size attribute of the font object.
            color: A str with specific format. The format is given as 'rgb(red, green, blue)' where the color values are
                integers in the range 0 (inclusive) to 255 (inclusive). Default: 'rgb(0, 0, 0)'.
            is_half_char: A function judging whether or not a char only take up half of its original width. The function
                must take a char parameter and return a boolean value. Default: (lambda c: False).
            is_end_char: A function judging whether or not a char can NOT be in the beginning of the lines (e.g. '，',
                '。', '》', ')', ']'). The function must take a char parameter and return a boolean value. Default:
                (lambda c: c in _DEFAULT_END_CHARS).
            alpha: A tuple of two floats as the degree of the distortion in the horizontal and vertical direction in
                order. Both values must be between 0.0 (inclusive) and 1.0 (inclusive). Default: (0.1, 0.1).
        anti_aliasing: Whether or not turn on the anti-aliasing. Default: True.
        worker: A int as the number of worker. if worker is less than or equal to 0, the actual amount of worker would
            be the number of CPU in the computer adding worker. Default: 0.
        seed: A int as the seed of the internal random generators. Default: None.

    Returns:
        A list of drawn images with the same size and mode as the corresponding background images.

    Raises:
        ValueError: When the parameters are not be set properly.
    """
    page_settings = template2['page_settings']
    for page_setting in page_settings:
        font_size = page_setting['font_size']
        page_setting.setdefault('word_spacing', 0)
        page_setting.setdefault('line_spacing', font_size // 5)
        page_setting.setdefault('font_size_sigma', font_size / 256)
        page_setting.setdefault('word_spacing_sigma', font_size / 256)
        page_setting.setdefault('line_spacing_sigma', font_size / 256)

    return _handwrite(text, page_settings, template2['font'], template2.get('color', 'rgb(0, 0, 0)'),
                      template2.get('is_half_char', lambda c: False),
                      template2.get('is_end_char', lambda c: c in _DEFAULT_END_CHARS),
                      template2.get('alpha', (0.1, 0.1)), anti_aliasing,
                      worker if worker > 0 else multiprocessing.cpu_count() + worker, seed)


def _handwrite(text: str, page_settings: list, font, color: str, is_half_char, is_end_char, alpha: tuple,
               anti_aliasing: bool, worker: int, seed: int) -> list:
    """Do the real stuffs for handwriting simulating."""
    pages = _draw_text(text, page_settings, font, is_half_char, is_end_char, anti_aliasing, seed)
    if not pages: return pages
    renderer = _Renderer(page_settings, color, alpha, anti_aliasing, seed)
    with multiprocessing.Pool(min(worker, len(pages))) as pool:
        images = pool.map(renderer, pages)
    return images


def _draw_text(text: str, page_settings: list, font, is_half_char, is_end_char, anti_aliasing: bool, seed: int) -> list:
    """Draws the text randomly in black images with white color. Note that (box[3] - box[1]) and (box[2] - box[0]) both
    must be greater than corresponding font_size.
    """
    # Avoid dead loops
    for page_setting in page_settings:
        if not page_setting['box'][3] - page_setting['box'][1] > page_setting['font_size']:
            raise ValueError("(box[3] - box[1]) must be greater than corresponding font_size.")
        if not page_setting['box'][2] - page_setting['box'][0] > page_setting['font_size']:
            raise ValueError("(box[2] - box[0]) must be greater than corresponding font_size.")

    rand = random.Random(x=seed)
    length = len(page_settings)
    chars = iter(text)
    pages = []
    try:
        char = next(chars)
        index = 0
        while True:
            (size, box, font_size, word_spacing, line_spacing, font_size_sigma, line_spacing_sigma,
             word_spacing_sigma) = _parse_page_setting(page_settings[index % length], anti_aliasing)
            left, upper, right, lower = box
            page = _page.Page(_INTERNAL_MODE, size, _BLACK, index)
            draw = page.draw
            y = upper
            try:
                while y < lower - font_size:
                    x = left
                    while True:
                        if char == '\n':
                            char = next(chars)
                            break
                        if x >= right - font_size and not is_end_char(char): break
                        actual_font_size = max(int(rand.gauss(font_size, font_size_sigma)), 0)
                        xy = (x, int(rand.gauss(y, line_spacing_sigma)))
                        font = font.font_variant(size=actual_font_size)
                        offset = _draw_char(draw, char, xy, font)
                        x_step = word_spacing + offset * (0.5 if is_half_char(char) else 1)
                        x += int(rand.gauss(x_step, word_spacing_sigma))
                        char = next(chars)
                    y += line_spacing + font_size
                pages.append(page)
            except StopIteration:
                pages.append(page)
                raise StopIteration()
            index += 1
    except StopIteration:
        return pages


def _parse_page_setting(page_setting: dict, anti_aliasing: bool) -> tuple:
    """A helper function of _draw_text"""
    size = (tuple(i * _AMP for i in page_setting['background'].size)
            if anti_aliasing else page_setting['background'].size)
    box = tuple(i * _AMP for i in page_setting['box']) if anti_aliasing else page_setting['box']
    font_size = page_setting['font_size'] * _AMP if anti_aliasing else page_setting['font_size']
    word_spacing = page_setting['word_spacing'] * _AMP if anti_aliasing else page_setting['word_spacing']
    line_spacing = page_setting['line_spacing'] * _AMP if anti_aliasing else page_setting['line_spacing']
    font_size_sigma = page_setting['font_size_sigma'] * _AMP if anti_aliasing else page_setting['font_size_sigma']
    word_spacing_sigma = (page_setting['word_spacing_sigma'] * _AMP
                          if anti_aliasing else page_setting['word_spacing_sigma'])
    line_spacing_sigma = (page_setting['line_spacing_sigma'] * _AMP
                          if anti_aliasing else page_setting['line_spacing_sigma'])
    return size, box, font_size, word_spacing, line_spacing, font_size_sigma, line_spacing_sigma, word_spacing_sigma


def _draw_char(draw, char: str, xy: tuple, font) -> int:
    """Draws a single char with the parameters and white color, and returns the offset."""
    draw.text(xy, char, fill=_WHITE, font=font)
    return font.getsize(char)[0]


class _Renderer(object):
    """A function-like object rendering the foreground that was drawn text and returning rendered image."""

    def __init__(self, page_settings: list, color: str, alpha: tuple, anti_aliasing: bool, seed: int):
        self._page_settings = page_settings
        self._color = color
        self._alpha = alpha
        self._anti_aliasing = anti_aliasing
        self._rand = random.Random()
        self._seed = seed

    def __call__(self, page: _page.Page):
        if self._seed is None:
            self._rand.seed()  # avoid different processes sharing the same random state
        else:
            self._rand.seed(a=self._seed + page.index)
        self._perturb(page)
        if self._anti_aliasing: self._downscale(page)
        return self._merge(page)

    def _perturb(self, page: _page.Page) -> None:
        """'perturbs' the image and generally makes the glyphs from same chars, if any, seems different. Note that
        self._alpha[0] and self._alpha[1] both must be between 0 (inclusive) and 1 (inclusive).
        """
        if not 0 <= self._alpha[0] <= 1: raise ValueError("alpha[0] must be between 0 (inclusive) and 1 (inclusive).")
        if not 0 <= self._alpha[1] <= 1: raise ValueError("alpha[1] must be between 0 (inclusive) and 1 (inclusive).")

        wavelength = 2 * self._page_settings[page.index % len(self._page_settings)]['font_size']
        if wavelength == 0: return
        alpha_x, alpha_y = self._alpha
        matrix = page.matrix

        for i in range((page.width + wavelength) // wavelength + 1):
            x0 = self._rand.randrange(-wavelength, page.width)
            for j in range(max(0, -x0), min(wavelength, page.width - x0)):
                offset = int(alpha_x * wavelength / (2 * math.pi) * (1 - math.cos(2 * math.pi * j / wavelength)))
                self._slide_x(matrix, x0 + j, offset, page.height)

        for i in range((page.height + wavelength) // wavelength + 1):
            y0 = self._rand.randrange(-wavelength, page.height)
            for j in range(max(0, -y0), min(wavelength, page.height - y0)):
                offset = int(alpha_y * wavelength / (2 * math.pi) * (1 - math.cos(2 * math.pi * j / wavelength)))
                self._slide_y(matrix, y0 + j, offset, page.width)

    @staticmethod
    def _slide_x(matrix, x: int, offset: int, height: int) -> None:
        """Slides one given column."""
        for i in range(height - offset):
            matrix[x, i] = matrix[x, i + offset]
        for i in range(height - offset, height):
            matrix[x, i] = _BLACK

    @staticmethod
    def _slide_y(matrix, y: int, offset: int, width: int) -> None:
        """Slides one given row."""
        for i in range(width - offset):
            matrix[i, y] = matrix[i + offset, y]
        for i in range(width - offset, width):
            matrix[i, y] = _BLACK

    @staticmethod
    def _downscale(page: _page.Page) -> None:
        """Downscales the image for 4X SSAA."""
        page.image = page.image.resize(size=(page.width // _AMP, page.height // _AMP), resample=image.BOX)

    def _merge(self, page: _page.Page):
        """Merges the foreground and the background and returns merged raw image."""
        res = self._page_settings[page.index % len(self._page_settings)]['background'].copy()
        draw = image_draw.Draw(res)
        draw.bitmap(xy=(0, 0), bitmap=page.image, fill=self._color)
        return res
