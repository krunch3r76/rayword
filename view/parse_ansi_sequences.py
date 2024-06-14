# parse_ansi_sequences.py
import re
import curses
from .color_pairs import get_color_pair
import logging

# Regex for ANSI escape sequences
ANSI_ESCAPE_REGEX = re.compile(r"\x1B\[(\d+(?:;\d+)*)m")


def parse_ansi_sequences(text: str):
    segments = []
    current_attr = curses.A_NORMAL
    last_pos = 0

    for match in ANSI_ESCAPE_REGEX.finditer(text):
        start, end = match.span()
        if text[last_pos:start] != "''":
            segments.append((text[last_pos:start], current_attr))
            last_pos = end

            params = match.group(1)
            if "?" in params:  # This indicates a cursor control sequence
                continue  # Skip processing this sequence or handle it differently if needed
            params = map(int, params.split(";"))
            for code in params:
                if code == 0:  # Reset
                    current_attr = curses.A_NORMAL
                elif 30 <= code <= 37 or 90 <= code <= 97:
                    current_attr = get_color_pair(code)

    if text[last_pos:] != "''":
        segments.append((text[last_pos:], current_attr))
    # logging.debug(f"segments: {segments}")
    return segments


# def parse_ansi_sequences(text: str):
#     segments = []
#     current_attr = curses.A_NORMAL
#     last_pos = 0

#     for match in ANSI_ESCAPE_REGEX.finditer(text):
#         start, end = match.span()
#         segments.append((text[last_pos:start], current_attr))
#         last_pos = end

#         params = map(int, match.group(1).split(";"))
#         for code in params:
#             if code == 0:  # Reset
#                 current_attr = curses.A_NORMAL
#             elif 30 <= code <= 37 or 90 <= code <= 97:
#                 current_attr = get_color_pair(code)

#     segments.append((text[last_pos:], current_attr))
#     return segments
