# log_window.py

import curses
from view.parse_ansi_sequences import parse_ansi_sequences
import logging


class MyPad:
    def __init__(
        self,
        stdscr,
        upper_left_y,
        upper_left_x,
        height,
        width,
        nlines=10000,
        ncols=1000,
    ):
        self._stdscr = stdscr
        self._upper_left_y = upper_left_y
        self._upper_left_x = upper_left_x
        self._height = height
        self._width = width

        # self._pminrow = 0
        self._pmincol = 0
        self._padline = 0  # cursor 1-based indicating with line to which to write
        self._padcol = 0
        self._win = curses.newpad(nlines, ncols)
        self.refresh()

    @property
    def _pminrow(self):
        # return the top row that would allow the row at _padline to be displayed at the bottom
        # of the pad
        viewable_height, viewable_width = self._calculate_viewable_width_and_height()
        if self._padline > viewable_height:
            return self._padline - viewable_height
        else:
            return 0

    def refresh(self, topline=None):
        # toprow overrides self._pminrow
        def _compute_refresh_coordinates(topline):
            # calculate the coordinates for a call to refresh
            if topline is not None:
                pminrow = topline - 1
            else:
                pminrow = self._pminrow
            return (
                pminrow,
                self._pmincol,
                self._upper_left_y,
                self._upper_left_x,
                self._upper_left_y + self._height - 1,
                self._upper_left_x + self._width - 1,
            )

        # logging.debug(f"refresh coords: {_compute_refresh_coordinates()}")
        coords = _compute_refresh_coordinates(topline)
        # logging.debug(f"refreshing using {coords}")
        self._win.refresh(
            coords[0], coords[1], coords[2], coords[3], coords[4], coords[5]
        )

    def _calculate_viewable_width_and_height(self):
        """not relevant to pads but useful in general for windows"""
        screen_height, screen_width = self._stdscr.getmaxyx()
        drawable_height = screen_height - self._upper_left_y
        drawable_width = screen_width - self._upper_left_x
        viewable_height = min(self._height, drawable_height)
        viewable_width = min(self._width, drawable_width)
        return viewable_height, viewable_width

    # @property _max_height_and_width(self):
    #     """return the defined width or available width, whichever is least"""

    # def scrollup(self):
    #     self._pinminrow += 1
    #     if self._pinminrow > nlines - 1:
    #         raise Exception("Cannot scroll past buffer")

    def _advance_line_cursor(self):
        self._padline += 1

    def _write_and_wrap_segment(self, segment):
        """write the text with the given attribute to the pad line cursor
        returning the next segment that would not fit the effective window width"""

        if segment[0] == "":
            return

        def find_indices_to_spaces(text) -> list:
            return [index for index, char in enumerate(text) if char == " "]

        def find_highest_less_than(indices, threshold):
            try:
                return max(i for i in indices if i < threshold)
            except ValueError:
                pass
            return None

        # error check that segment is the right type?

        text = segment[0]
        attr = segment[1]
        subsegment = None
        fitted = None
        if len(text) + self._padcol > self._width:
            indices_to_delimiters = find_indices_to_spaces(text)
            if len(indices_to_delimiters) > 0:
                index_to_last_space_for_fit = find_highest_less_than(
                    indices_to_delimiters, self._width - 1 - self._padcol
                )
                if index_to_last_space_for_fit is not None:
                    logging.debug(
                        f"index to last sapce for fit: {index_to_last_space_for_fit}"
                    )
                    fitted = text[:index_to_last_space_for_fit]
                    remaining = text[index_to_last_space_for_fit + 1 :]
                    if len(remaining) > 0:
                        subsegment = (
                            remaining,
                            attr,
                        )
                else:
                    fitted = text[: self._width]
                    remaining = text[self._width + 1 :]
                    if len(remaining.strip()) > 0:
                        subsegment = (
                            remaining.lstrip(),
                            attr,
                        )
            else:
                fitted = text
        else:
            fitted = text
        # logging.debug(f"fitted is of type {type(fitted)} and fitted is {repr(fitted)}")
        self._win.addstr(self._padline - 1, self._pmincol + self._padcol, fitted, attr)
        self._padcol += len(fitted)
        return subsegment

    def add_line(self, line, attribute_segmenter=parse_ansi_sequences):
        line = line.rstrip("\r\n")  # normalize
        self._advance_line_cursor()
        if line == "''":
            return

        logging.debug(f"adding line: {repr(line)}")

        segment = None
        if attribute_segmenter is None:
            segments = [
                (
                    line,
                    None,
                )
            ]
        else:
            segments = attribute_segmenter(line)

        logging.debug(f"adding segments: {segments}")
        self._padcol = 0
        for segment in segments:
            if segment[0] == "":
                continue
            subsegment = self._write_and_wrap_segment(segment)
            while subsegment is not None:
                self._padcol = 0
                self._advance_line_cursor()
                logging.debug(f"adding subsegment: {subsegment}")
                # self.move(self._padline, 0)
                subsegment = self._write_and_wrap_segment(subsegment)

        # debug
        # self.refresh()

    # def move(self, *args):
    #     logging.debug(f"moving to padline: {self._padline}")
    #     self._win.move(*args)


class LogWindow(MyPad):
    def __init__(
        self,
        stdscr,
        upper_left_y,
        upper_left_x,
        height,
        width,
        nlines=10000,
        ncols=1000,
    ):
        super().__init__(
            stdscr, upper_left_y, upper_left_x, height, width, nlines, ncols
        )
