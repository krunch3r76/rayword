# color_pairs.py

import curses


def init_color_pairs():
    curses.use_default_colors()
    for i, color in enumerate(
        [
            curses.COLOR_BLACK,
            curses.COLOR_RED,
            curses.COLOR_GREEN,
            curses.COLOR_YELLOW,
            curses.COLOR_BLUE,
            curses.COLOR_MAGENTA,
            curses.COLOR_CYAN,
            curses.COLOR_WHITE,
        ],
        start=1,
    ):
        curses.init_pair(i, color, -1)


def get_color_pair(ansi_code):
    if 30 <= ansi_code <= 37:
        return curses.color_pair(ansi_code - 29)  # Standard colors 1-8
    elif 90 <= ansi_code <= 97:
        return curses.color_pair(ansi_code - 81 + 8)  # Bright colors 9-16
    return curses.A_NORMAL


# def init_color_pairs():
#     curses.use_default_colors()
#     for i, color in enumerate(
#         [
#             curses.COLOR_BLACK,
#             curses.COLOR_RED,
#             curses.COLOR_GREEN,
#             curses.COLOR_YELLOW,
#             curses.COLOR_BLUE,
#             curses.COLOR_MAGENTA,
#             curses.COLOR_CYAN,
#             curses.COLOR_WHITE,
#         ],
#         start=1,
#     ):
#         curses.init_pair(i, color, -1)


# def get_color_pair(ansi_code):
#     if 30 <= ansi_code <= 37:
#         return curses.color_pair(ansi_code - 29)  # Standard colors 1-8
#     elif 90 <= ansi_code <= 97:
#         return curses.color_pair(ansi_code - 81 + 8)  # Bright colors 9-16
#     return curses.color_pair(0)  # Default color
