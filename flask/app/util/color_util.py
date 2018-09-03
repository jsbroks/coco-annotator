import random
import colorsys


def random_color_hls(hue=[0, 1], lightness=[0.35, 0.70], saturation=[0.60, 1]):
    h = random.uniform(hue[0], hue[1])
    l = random.uniform(lightness[0], lightness[1])
    s = random.uniform(saturation[0], saturation[1])
    return h, l, s


def random_color_rgb():
    h, l, s = random_color_hls()
    return [int(256*i) for i in colorsys.hls_to_rgb(h, l, s)]


def random_color_hex():
    rgb = random_color_rgb()
    return '#%02x%02x%02x' % (rgb[0], rgb[1], rgb[2])


def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hsl():
    pass

