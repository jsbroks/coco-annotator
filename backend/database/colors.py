import colorsys
import random


def random_color():
    """Return a random, reasonably saturated colour as a hex string."""
    h = random.random()
    s = random.uniform(0.5, 0.9)
    v = random.uniform(0.6, 0.95)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))
