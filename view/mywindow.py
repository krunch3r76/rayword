# view/mywindow.py
import curses
import logging


class MyWindow:
    def __init__(
        self,
        stdscr: curses.window,
        upper_left_y: int = 0,
        upper_left_x: int = 0,
        height: int = None,
        width: int = None,
        boxed: bool = False,
    ):
        """
        Initialize the window with the given parameters.

        Parameters:
        - stdscr: The main curses window object.
        - upper_left_y: The upper-left y-coordinate of the window.
        - upper_left_x: The upper-left x-coordinate of the window.
        - height: The height of the window.
        - width: The width of the window.
        - boxed: Boolean indicating whether the window should have a border.
        """
        self._stdscr = stdscr
        self._upper_left_y = upper_left_y
        self._upper_left_x = upper_left_x
        screen_height, screen_width = self._stdscr.getmaxyx()
        self._height = (
            height if height is not None else screen_height - self._upper_left_y
        )
        self._width = width if width is not None else screen_width - self._upper_left_x
        available_lines, available_cols = self._viewable_height_and_width
        # logging.debug("WTF")
        # logging.debug(
        #     f"available_lines: {available_lines}, available_cols: {available_cols}"
        # )
        self._win = curses.newwin(
            available_lines, available_cols, self._upper_left_y, self._upper_left_x
        )
        self._boxed = boxed
        if self._boxed:
            self._win.box()

    @property
    def _viewable_height_and_width(self):
        """
        Calculate and return the viewable height and width of the window.

        Returns:
        - viewable_height: The height available for drawing.
        - viewable_width: The width available for drawing.
        """
        screen_height, screen_width = self._stdscr.getmaxyx()
        drawable_height = screen_height - self._upper_left_y
        drawable_width = screen_width - self._upper_left_x
        viewable_height = min(self._height, drawable_height)
        viewable_width = min(self._width, drawable_width)
        return viewable_height, viewable_width

    def refresh(self, clear=False):
        """
        Refresh the window, drawing a border if specified.
        """
        if clear:
            self.clear()
        if self._boxed:
            self._win.box()
        self._win.refresh()

    def clear(self):
        """
        Clear the window content.
        """
        self._win.clear()

    def resize_deep(self):
        """
        Clear and resize the window, then refresh it.
        """
        self.clear()
        available_lines, available_cols = self._viewable_height_and_width
        self._win.resize(available_lines, available_cols)
        self._win.touchwin()
        self._win.redrawwin()
        self.refresh()

    def resize(self):
        """
        Resize the window without clearing it.
        """
        available_lines, available_cols = self._viewable_height_and_width
        self._win.erase()
        self._win.resize(available_lines, available_cols)
        self.refresh()

    def _add_line_truncated(self, line, y_offset, x_offset=0, attr=curses.A_NORMAL):
        """
        Add a truncated line to the window at the specified offset with attributes.

        Parameters:
        - line: The line to be added.
        - y_offset: The y-coordinate offset.
        - x_offset: The x-coordinate offset.
        - attr: Text attributes (e.g., color).
        """
        max_height, max_width = self._viewable_height_and_width
        available_width = max_width - x_offset if x_offset is not None else max_width
        if y_offset > max_height - 1:
            raise Exception("Line written outside of height boundaries")
        truncated_line = line[:available_width]
        self._win.move(y_offset, x_offset)
        self._win.insstr(y_offset, x_offset, truncated_line, attr)
        # logging.debug(
        #     f"added: {truncated_line} with attr: {attr} at {y_offset},{x_offset}"
        # )

    def _add_line(
        self, line, y_offset, x_offset=0, attr=curses.A_NORMAL, truncated=True
    ):
        """
        Add a line to the window, either truncated or not.

        Parameters:
        - line: The line to be added.
        - y_offset: The y-coordinate offset.
        - x_offset: The x-coordinate offset.
        - attr: Text attributes (e.g., color).
        - truncated: Boolean indicating whether the line should be truncated.
        """
        line = line.rstrip()
        if truncated:
            self._add_line_truncated(line, y_offset, x_offset, attr)
        else:
            raise Exception("Non truncated lines not yet supported")


class TextEntryBox(MyWindow):
    def __init__(
        self,
        stdscr: curses.window,
        upper_left_y: int = 0,
        upper_left_x: int = 0,
        height: int = 2,
        width: int = None,
        boxed: bool = True,
    ):
        super().__init__(stdscr, upper_left_y, upper_left_x, height, width, boxed)
        self._textbuffer = ""
        self._stdscr.refresh()  # kludge for display

    def _add_line(self, line):
        self.clear()
        super()._add_line(line, self._upper_left_y + 1, self._upper_left_x + 1)

    def refresh(self):
        self._add_line(self._textbuffer)
        self._stdscr.refresh()
        super().refresh()
        # self._stdscr.refresh()

    def process_ascii(self, asciicode):
        self._textbuffer = self._textbuffer + chr(asciicode)
        self.refresh()

    def backspace(self):
        self._textbuffer = self._textbuffer[:-1]
        self.refresh()


class MyWindowLineBuffered(MyWindow):
    def __init__(
        self,
        stdscr: curses.window,
        upper_left_y: int = 0,
        upper_left_x: int = 0,
        height: int = None,
        width: int = None,
        boxed: bool = False,
    ):
        """
        Initialize a line-buffered window with the given parameters.

        Parameters:
        - stdscr: The main curses window object.
        - upper_left_y: The upper-left y-coordinate of the window.
        - upper_left_x: The upper-left x-coordinate of the window.
        - height: The height of the window.
        - width: The width of the window.
        - boxed: Boolean indicating whether the window should have a border.
        """
        logging.debug("hello")
        super().__init__(stdscr, upper_left_y, upper_left_x, height, width, boxed)
        self._lines = []
        self.__current_line_index = -1  # the bottom-most virtual line (cursor)
        self.__selected_line_index = -1
        self._scrolling = False

    @property
    def _selected_line_index(self):
        return self.__selected_line_index

    @_selected_line_index.setter
    def _selected_line_index(self, newindex):
        # logging.debug(f"Setting _selected_line_index to {newindex}")
        self.__selected_line_index = newindex

    def resize(self):
        """
        Placeholder for resize functionality.
        """
        pass

    @property
    def _bottom_line_index(self):
        # index to visible bottom line given fixed dimensions
        viewable_height, _ = self._viewable_height_and_width
        if not self.__current_line_index < viewable_height:
            invisible_portion = self._height - viewable_height
            return self.__current_line_index - invisible_portion
        else:
            return self.__current_line_index

    @property
    def _top_line_index(self):
        # index to visible top line give fixed dimensions
        viewable_height, _ = self._viewable_height_and_width
        if not self.__current_line_index < viewable_height:
            return self._bottom_line_index - (viewable_height - 1)
        else:
            return 0

    def clearlines(self):
        self._lines = []
        self.__current_line_index = -1
        self.__selected_line_index = -1

    def clear(self):
        super().clear()

    def refresh(self):
        """
        Draw the buffered lines truncated with applicable highlighting.

        Notes:
        - Draws all lines from the top to the line designated as the bottom line (__current_line_index).
        - Draws as far as can be given the viewable height and width.
        """

        self.clear()

        for cursor, line in enumerate(
            self._lines[self._top_line_index : self._bottom_line_index + 1]
        ):
            corresponding_line_index = self._top_line_index + cursor
            if corresponding_line_index == self._selected_line_index:
                super()._add_line(line, cursor, attr=curses.A_REVERSE)
            else:
                super()._add_line(line, cursor)

        super().refresh()

    def add_line(self, line):
        """
        Add a new line to the buffer and update the current line index.

        Parameters:
        - line: The line to be added to the buffer.
        """
        self._lines.append(line)
        if self._scrolling:
            self.__current_line_index += 1
        else:
            viewable_height, _ = self._viewable_height_and_width
            self.__current_line_index = min(viewable_height - 1, len(self._lines) - 1)

    def move_selection_down(self):
        # logging.debug(
        #     f"selected_line_index at time of keypress: {self._selected_line_index}, current_line_index = {self.__current_line_index}, bottom_line_index = {self._bottom_line_index}"
        # )
        if self._selected_line_index == -1:
            self._selected_line_index = self._top_line_index
        elif (
            self._selected_line_index < self._bottom_line_index
        ):  # cannot scroll past lower bound
            self._selected_line_index += 1
        else:  # at bottom line
            if self._selected_line_index == self._bottom_line_index:
                self._selected_line_index += 1
                if self.__current_line_index < len(self._lines) - 1:
                    self.__current_line_index += 1
                else:
                    self._selected_line_index -= (
                        1  # backtrack cannot scroll past bottom
                    )
                # if self._selected_line_index > self._bottom_line_index:
                #     self.__current_line_index += 1
        self.refresh()
        logging.debug(
            f"selected_line_index after time of keypress: {self._selected_line_index}, current_line_index = {self.__current_line_index}, bottom_line_index = {self._bottom_line_index}, last index: {len(self._lines)-1}\n"
        )

    def move_selection_up(self):
        logging.debug(
            f"selected_line_index at time of keypress: {self._selected_line_index}, current_line_index = {self.__current_line_index}, top_line_index = {self._top_line_index}"
        )
        if self._selected_line_index > 0:  # cannot scroll past upper bound
            self._selected_line_index -= 1
            if self._selected_line_index < self._top_line_index:
                self.__current_line_index -= 1
                if self._top_line_index == -1:
                    self.__current_line_index += (
                        1  # exception, cannot scroll up past top line
                    )
        else:
            self._selected_line_index = -1
        self.refresh()
        # logging.debug(
        #     f"selected_line_index after time of keypress: {self._selected_line_index}, current_line_index = {self.__current_line_index}, top_line_index = {self._top_line_index}\n"
        # )
