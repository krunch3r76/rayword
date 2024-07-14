import logging
import curses
from .mywindow import MyWindow


class MyWindowLineBuffered(MyWindow):
    def __init__(
        self,
        stdscr: curses.window,
        upper_left_y: int = 0,
        upper_left_x: int = 0,
        height: int = None,
        width: int = None,
        boxed: bool = False,
        scrolling: bool = False,
        padding: int = 0,
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
        super().__init__(
            stdscr, upper_left_y, upper_left_x, height, width, boxed, padding
        )
        self._lines = []
        self._current_line_index = -1
        self._scrolling = scrolling

    @property
    def _bottom_line_index(self):
        """
        Calculate and return the index of the bottom visible line.

        Adjusts for the height of the window and the boxed condition.

        Returns:
        - int: The index of the bottom visible line.
        """
        viewable_height, _ = self._viewable_height_and_width
        if self._current_line_index >= viewable_height:
            invisible_portion = self._height - viewable_height
            invisible_portion -= self.padding * 2
            return self._current_line_index - invisible_portion
        else:
            return self._current_line_index

    @property
    def _top_line_index(self):
        """
        Calculate and return the index of the top visible line.

        Adjusts for the height of the window and the boxed condition.

        Returns:
        - int: The index of the top visible line.
        """
        viewable_height, _ = self._viewable_height_and_width
        if self._current_line_index >= viewable_height:
            return self._bottom_line_index - (viewable_height - 1)
        else:
            return 0

    def refresh(self):
        """
        Refresh the window, drawing the buffered lines and highlighting the selected line.

        Draws all lines from the top to the line designated as the bottom line.
        Highlights the selected line with the reverse attribute.
        """
        self.clear()
        for cursor, line in enumerate(
            self._lines[self._top_line_index : self._bottom_line_index + 1]
        ):
            super()._add_line(line, cursor)
        if self._boxed:
            self._win.box()
        super().refresh()

    def clearlines(self):
        """
        Clear all lines from the buffer and reset the current line index.
        """
        self._lines = []
        self._current_line_index = -1

    def clear(self):
        """
        Clear the window content.
        """
        super().clear()

    def add_line(self, line):
        """
        Add a new line to the buffer and update the current line index.

        Parameters:
        - line: The line to be added to the buffer.
        """
        self._lines.append(line)
        if self._scrolling:
            self._current_line_index += 1
        else:
            viewable_height, _ = self._viewable_height_and_width
            self._current_line_index = min(viewable_height - 1, len(self._lines) - 1)


class MyWindowLineBufferedWrapped(MyWindowLineBuffered):
    def __init__(
        self,
        stdscr: curses.window,
        upper_left_y: int = 0,
        upper_left_x: int = 0,
        height: int = None,
        width: int = None,
        boxed: bool = False,
        scrolling: bool = False,
        padding: int = 0,
    ):
        """
        Initialize a line-buffered window with wrapped line handling.

        Parameters:
        - stdscr: The main curses window object.
        - upper_left_y: The upper-left y-coordinate of the window.
        - upper_left_x: The upper-left x-coordinate of the window.
        - height: The height of the window.
        - width: The width of the window.
        - boxed: Boolean indicating whether the window should have a border.
        - scrolling: Boolean indicating whether the window should support scrolling.
        """
        super().__init__(
            stdscr, upper_left_y, upper_left_x, height, width, boxed, scrolling, padding
        )
        self._wrapped_lines = []

    def _wrap_lines(self):
        """
        Wrap lines to fit within the viewable width of the window.
        """
        max_width = self._viewable_height_and_width[1]
        self._wrapped_lines = []
        for line in self._lines:
            words = line.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 <= max_width:
                    if current_line:
                        current_line += " "
                    current_line += word
                else:
                    self._wrapped_lines.append(current_line)
                    current_line = word
            if current_line:
                self._wrapped_lines.append(current_line)

    def add_line(self, line):
        """
        Add a new line to the buffer and update the wrapped lines.

        Parameters:
        - line: The line to be added to the buffer.
        """
        self._lines.append(line)
        self._wrap_lines()
        if self._scrolling:
            self._current_line_index = len(self._wrapped_lines) - 1
        else:
            viewable_height, _ = self._viewable_height_and_width
            self._current_line_index = min(
                viewable_height - 1, len(self._wrapped_lines) - 1
            )

    @property
    def _bottom_line_index(self):
        """
        Calculate and return the index of the bottom visible line for wrapped lines.
        """
        viewable_height, _ = self._viewable_height_and_width
        return self._current_line_index

        # if self._current_line_index >= viewable_height:
        #     invisible_portion = len(self._wrapped_lines) - viewable_height
        #     invisible_portion -= 2 * self.padding
        #     return self._current_line_index - invisible_portion
        # else:
        #     return self._current_line_index

    @property
    def _top_line_index(self):
        """
        Calculate and return the index of the top visible line for wrapped lines.
        """
        viewable_height, _ = self._viewable_height_and_width
        if self._current_line_index >= viewable_height:
            return self._bottom_line_index - (viewable_height - 1)
        else:
            return 0

    def refresh(self):
        """
        Refresh the window, drawing the wrapped lines.
        """
        self.clear()
        for i, line in enumerate(
            self._wrapped_lines[self._top_line_index : self._bottom_line_index + 1]
        ):
            self._add_line(line, i)
        if self._boxed:
            self._win.box()
        self._win.refresh()

    def _add_line(self, line, y_offset, x_offset=0, attr=curses.A_NORMAL):
        """
        Add a line to the window at the specified offset with attributes.

        Parameters:
        - line (str): The line to be added.
        - y_offset (int): The y-coordinate offset.
        - x_offset (int): The x-coordinate offset. Default is 0.
        - attr (int): Text attributes (e.g., color). Default is curses.A_NORMAL.
        """
        max_height, max_width = self._viewable_height_and_width

        if y_offset >= max_height:
            raise ValueError("Line written outside of boundaries")

        y_offset += self.y_padding
        x_offset += self.x_padding

        self._win.move(y_offset, x_offset)
        self._win.insstr(line, attr)

    def scroll_up(self):
        """
        Scroll the view up by one line.
        """
        logging.debug(f"current line index: {self._current_line_index}")
        if self._current_line_index > 0:
            if self._current_line_index >= self._viewable_height_and_width[0]:
                self._current_line_index -= 1
                self.refresh()

    def scroll_down(self):
        """
        Scroll the view down by one line.
        """
        logging.debug(
            f"current line index: {self._current_line_index} < {len(self._wrapped_lines)}"
        )
        if self._current_line_index < len(self._wrapped_lines) - 1:
            self._current_line_index += 1
            self.refresh()

        logging.debug(
            f"current line index: {self._current_line_index} < {len(self._wrapped_lines)}"
        )
