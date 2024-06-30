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
        self._pmincol = 0
        self._padline = 0  # cursor 1-based indicating with line to which to write
        self._padline_at_keyup = 0
        self.__curcol = 0
        self._win = curses.newpad(nlines, ncols)
        self._current_line_offset = 0
        self._autoscroll_active = False
        self._padline_top = (
            1  # the viewable line number of the pad that is on the first row
        )
        self.refresh()

    @property
    def _curcol(self):
        return self.__curcol

    @_curcol.setter
    def _curcol(self, offset):
        self.__curcol = offset

    @property
    def _ncols(self):
        _, ncols = self._win.getmaxyx()
        return ncols

    @property
    def _pminrow(self):
        # Return the top row that would allow the row at _padline to be displayed at the bottom of the pad
        viewable_height, _ = self._viewable_height_and_width
        if self._padline > viewable_height:
            return self._padline - viewable_height
        else:
            return 0

    def clear(self):
        self._win.clear()

    def refresh(self):
        """

        notes: uses _padline_top only if the window has been scrolled
        """

        # toprow overrides self._pminrow
        def _compute_refresh_coordinates(topline):
            # Calculate the coordinates for a call to refresh
            if topline is not None:
                pminrow = topline
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

        topline = None

        if self._current_line_offset != 0:
            topline = self._padline_top
            # topline = self._pminrow - self._current_line_offset - 1

        coords = _compute_refresh_coordinates(topline)

        self._win.refresh(
            coords[0], coords[1], coords[2], coords[3], coords[4], coords[5]
        )

    @property
    def _viewable_height_and_width(self):
        """Calculate the viewable width and height for the pad"""
        screen_height, screen_width = self._stdscr.getmaxyx()
        drawable_height = screen_height - self._upper_left_y
        drawable_width = screen_width - self._upper_left_x
        viewable_height = min(self._height, drawable_height)
        viewable_width = min(self._width, drawable_width)
        return viewable_height, viewable_width

    def _advance_line_cursor(self):
        self._padline += 1

    def _write_segment(self, segment, truncate=False):
        """Write the text with the given attribute to the pad line cursor,
        returning the next segment that would not fit the effective window width."""

        if segment[0] == "":
            return

        text = segment[0]
        attr = segment[1]
        subsegment = None
        _, viewable_width = self._viewable_height_and_width

        # Always truncate if the line exceeds ncols
        if len(text) + self._curcol > self._ncols:
            fitted = text[: self._ncols - self._curcol]
            subsegment = (
                (text[self._ncols - self._curcol :], attr)
                if len(text) > self._ncols - self._curcol
                else None
            )
        else:
            fitted = text

        # Truncate to viewable width if the truncate flag is set
        if truncate and len(fitted) + self._curcol > viewable_width:
            fitted = fitted[: viewable_width - self._curcol]
            subsegment = None

        # Handle wrapping if the wrap flag is set and the text is not truncated
        if len(fitted) + self._curcol > viewable_width:
            indices_to_delimiters = [
                index for index, char in enumerate(fitted) if char == " "
            ]
            indices_to_delimiters.append(len(fitted))

            fitting_indices = [
                i for i in indices_to_delimiters if i <= viewable_width - self._curcol
            ]

            if fitting_indices:
                index_to_last_space_for_fit = max(fitting_indices)
                remaining = fitted[index_to_last_space_for_fit + 1 :]
                fitted = fitted[:index_to_last_space_for_fit]
                subsegment = (remaining, attr) if remaining else None
            else:
                remaining = fitted[viewable_width - self._curcol :]
                fitted = fitted[: viewable_width - self._curcol]
                subsegment = (remaining, attr) if remaining else None

        if fitted:
            self._win.addstr(
                self._padline - 1, self._pmincol + self._curcol, fitted, attr
            )
            self._curcol += len(fitted)

        return subsegment

    def add_line(self, line, attribute_segmenter=parse_ansi_sequences):
        line = line.rstrip("\r\n")  # Normalize
        self._advance_line_cursor()
        if line == "":
            return

        logging.debug(f"adding line: {repr(line)}")

        if attribute_segmenter is None:
            segments = [(line, None)]
        else:
            segments = attribute_segmenter(line)

        logging.debug(f"adding segments: {segments}")
        self._curcol = 0
        for segment in segments:
            if segment[0] == "":
                continue
            subsegment = self._write_segment(segment)
            logging.debug(f"got subsegment: {subsegment}")
            while subsegment is not None:
                self._curcol = 0
                self._advance_line_cursor()
                logging.debug(f"adding subsegment: {subsegment}")
                subsegment = self._write_segment(subsegment)

    def scroll_up(self):
        # if self._current_line_offset == 0:
        #     self._padline_at_keyup = self._padline
        # viewable_height, _ = self._viewable_height_and_width
        self._padline_top = self._pminrow - self._current_line_offset - 1
        if self._padline_top >= 1:
            if self._autoscroll_active:
                self._padline_at_keyup = self._current_line_offset
            self._current_line_offset += 1
            self._autoscroll_active = False
        # self.refresh(self._pminrow - self._current_line_offset)

    def scroll_down(self):
        if self._current_line_offset > 0:
            logging.debug("> 0")
            self._current_line_offset -= 1
            self._padline_top += 1
            if self._current_line_offset <= self._padline_at_keyup:
                logging.debug(
                    f"padline: {self._padline} >=? padline_at_keyup: {self._padline_at_keyup}"
                )
                if (
                    not self._autoscroll_active
                    and self._padline >= self._padline_at_keyup
                ):
                    self.auto_scroll_active = True
                    logging.debug(
                        f"AUTOSCROLL, current line offset: {self._current_line_offset}"
                    )
                else:
                    self._current_line_offset = self._padline - self._padline_at_keyup
            self.refresh()
            # self.refresh(self._pminrow - self._current_line_offset)
        else:
            self.refresh()

        # self.refresh()


# class MyPadBuffered(MyPad):
#     """a subclass that implements an internal buffer and line selection"""

#     def __init__(
#         self,
#         stdscr,
#         upper_left_y,
#         upper_left_x,
#         height,
#         width,
#         nlines=10000,
#         ncols=1000,
#     ):
#         super().__init__(
#             stdscr, upper_left_y, upper_left_x, height, width, nlines, ncols
#         )
#         self._linebuffer = []

#     def add_line(self, line, attribute_segmenter=parse_ansi_sequences):
#         self._linebuffer.append(line)
#         super().add_line(line, attribute_segmenter)

#     def _write_segment(self, segment, truncate=True):
#         super().add_line(segment, truncate)


class MyPadWrapped(MyPad):
    # a version of mypad that implements wrapping logic

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

    def _write_segment(self, segment, truncate=False):
        """Write the text with the given attribute to the pad line cursor,
        returning the next segment that would not fit the effective window width."""

        if segment[0] == "":
            return

        text = segment[0]
        attr = segment[1]
        subsegment = None
        _, viewable_width = self._viewable_height_and_width

        # Always truncate if the line exceeds ncols
        if len(text) + self._curcol > self._ncols:
            fitted = text[: self._ncols - self._curcol]
            subsegment = (
                (text[self._ncols - self._curcol :], attr)
                if len(text) > self._ncols - self._curcol
                else None
            )
        else:
            fitted = text

        # Truncate to viewable width if the truncate flag is set
        if truncate and len(fitted) + self._curcol > viewable_width:
            fitted = fitted[: viewable_width - self._curcol]
            subsegment = None

        # Handle wrapping if the wrap flag is set and the text is not truncated
        if len(fitted) + self._curcol > viewable_width:
            indices_to_delimiters = [
                index for index, char in enumerate(fitted) if char == " "
            ]
            indices_to_delimiters.append(len(fitted))

            fitting_indices = [
                i for i in indices_to_delimiters if i <= viewable_width - self._curcol
            ]

            if fitting_indices:
                index_to_last_space_for_fit = max(fitting_indices)
                remaining = fitted[index_to_last_space_for_fit + 1 :]
                fitted = fitted[:index_to_last_space_for_fit]
                subsegment = (remaining, attr) if remaining else None
            else:
                remaining = fitted[viewable_width - self._curcol :]
                fitted = fitted[: viewable_width - self._curcol]
                subsegment = (remaining, attr) if remaining else None

        if fitted:
            self._win.addstr(
                self._padline - 1, self._pmincol + self._curcol, fitted, attr
            )
            self._curcol += len(fitted)

        return subsegment


class LogWindow(MyPadWrapped):
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

    def _write_segment(self, segment):
        return super()._write_segment(segment, truncate=False)


# def main(stdscr):
#     curses.curs_set(0)
#     stdscr.clear()
#     stdscr.refresh()

#     log_win = LogWindow(stdscr, 0, 0, 20, 80)
#     lines = ["This is line {}".format(i) for i in range(1, 25)]
#     for line in lines:
#         log_win.add_line(line, attribute_segmenter=parse_ansi_sequences)
#     log_win.refresh()

#     stdscr.getch()

# if __name__ == "__main__":
#     curses.wrapper(main)
