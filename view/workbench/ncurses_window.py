# File: golemspi/view/ncurses_window.py
import curses
import io
import textwrap

from utils.mylogger import file_logger


def calc_margins(
    scr: curses._curses.window, y_offset: int, x_offset: int, height: int, width: int
) -> tuple:
    """
    Calculate and return the margins for placing a window on a parent screen

    arguments:
        scr: the window upon which margins are calculated e.g. the whole screen
        y_offset: vertical grid coordinate of top left corner (relative to viewable screen)
        x_offset: horizontal grid coordinate of top left corner (relative to viewable screen)
        height: number of grid rows window shall occupy
        width: number of grid columns window shall occupy

    returns: margins bottom, right, top, left

    raises: ValueError: If the new window exceeds the dimensions of the parent window
    notes: top and left margins are the same as the y and x offset relative to the top left of
    the underlying "screen", typically the window itself in a non nested context
    """
    max_y, max_x = scr.getmaxyx()
    if y_offset + height > max_y or x_offset + width > max_x:
        raise ValueError("New window exceeds dimensions of parent window.")

    margin_bottom = max_y - (height + y_offset)
    margin_top = y_offset
    margin_left = x_offset
    margin_right = max_x - (width + x_offset)

    return margin_top, margin_right, margin_bottom, margin_left


class _NcursesWindow:
    """
    attributes:
        _window: the instantiated curses window
        _resizing: whether the window is being resized
        _win_height: viewable height
        _win_width: viewable width
    """

    def __init__(self, margin_top, margin_right, margin_bottom, margin_left) -> tuple:
        self._margin_top, self._margin_right, self._margin_left, self._margin_bottom = (
            margin_top,
            margin_right,
            margin_bottom,
            margin_left,
        )
        self._margin_top = margin_top
        self._margin_right = margin_right
        self._margin_left = margin_left
        self._margin_bottom = margin_bottom
        self._window = None
        _NcursesWindow.reconstruct(self)
        self._resizing = False

    @property
    def _yx(self):
        """return upper left corner"""
        return self._margin_top, self._margin_left

    def _set_dimensions(self):
        """compute and set viewable height and width"""
        # Get the total number of lines and columns
        total_lines, total_cols = curses.LINES, curses.COLS

        # Compute the window size based on the margins
        self._win_height = total_lines - self._margin_top - self._margin_bottom
        self._win_width = total_cols - self._margin_left - self._margin_right

    def reconstruct(self):
        """construct a new wrapped window while deconstructing any existing wrapped window"""
        if self._window is not None:
            self._window.clear()
            self._window.refresh()
            del self._window

        self._set_dimensions()

        # Create the window with the computed size
        self._window = curses.newwin(
            self._win_height, self._win_width, self._margin_top, self._margin_left
        )
        # self._window.resize(curses.LINES, curses.COLS)
        self._window.resize(self._win_height, self._win_width)

    def insstr_truncated(self, row, col, text, attr=None):
        """insert a string on a row at the specified column offset cutting off any text that would overwrite
        the width"""
        window = self._window
        # Determine the available space for writing
        if row > self._height - 1:
            raise ValueError("attempted to write to row outside of window boundaries")

        available_space = self._win_width - col
        if available_space == 0:
            return 0

        # Truncate the text if necessary
        truncated_text = text[:available_space]

        # Write the text, applying the attribute if provided
        if attr is not None:
            window.insstr(row, col, truncated_text, attr)
        else:
            window.insstr(row, col, truncated_text)
        # Return the length of the text that was actually written
        return len(truncated_text)


class NcursesWindowLineBuffered(_NcursesWindow):
    """window with a buffer and internal representation of wrapped lines

    attributes:
        _linesUnwrapped (list): unwrapped lines
        _linesWrapped (list): wrapped lines

    """

    def __init__(self, margin_top, margin_right, margin_bottom, margin_left) -> tuple:
        self._margin_top, self._margin_right, self._margin_left, self._margin_bottom = (
            margin_top,
            margin_right,
            margin_bottom,
            margin_left,
        )
        super().__init__(margin_top, margin_right, margin_bottom, margin_left)
        self._linesUnwrapped = []
        self._linesWrapped = []
        self._rowDisplayedToOffset = dict()
        self._internal_offset = -1

    def append_line(self, line):
        self._linesUnwrapped.append(line)

    def _read_wrapped_reversed(self, offset: int = None):
        """generate wrapped lines in reverse from given internal offset"""
        if offset is None or offset == -1:
            offset = len(self._linesUnwrapped) - 1

        while offset >= 0:
            wrapped = textwrap.wrap(self._linesUnwrapped[offset], self._width)

            yield offset, wrapped
            offset -= 1

    def _recompose_lines(self):
        """reads as many lines in reverse that when wrapped would fit in the window's linecount"""
        # notes, may later include logic to read from where the last wrapped line was displayed
        # before (or after) for scrolling
        self._lines = []
        max_lines = self._height
        remaining_lines = max_lines

        for offset, wrapped_lines in self._read_wrapped_reversed(self._internal_offset):
            if remaining_lines <= 0:
                break

            # Determine how many lines we can still fit
            num_lines_to_add = min(len(wrapped_lines, remaining_lines))

            for line in reversed(wrapped_lines[-num_lines_to_add:]):
                self._lines.insert(0, line)
                self._rowDisplayedToOffset[remaining_lines - 1] = offset
