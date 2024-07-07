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
        - stdscr (curses.window): The main curses window object.
        - upper_left_y (int): The upper-left y-coordinate of the window. Default is 0.
        - upper_left_x (int): The upper-left x-coordinate of the window. Default is 0.
        - height (int, optional): The height of the window. If None, it uses the remaining screen height.
        - width (int, optional): The width of the window. If None, it uses the remaining screen width.
        - boxed (bool): Boolean indicating whether the window should have a border. Default is False.
        """
        self._stdscr = stdscr
        self._upper_left_y = upper_left_y
        self._upper_left_x = upper_left_x
        screen_height, screen_width = self._stdscr.getmaxyx()
        self._height = (
            height if height is not None else screen_height - self._upper_left_y
        )
        self._width = width if width is not None else screen_width - self._upper_left_x
        self._boxed = boxed

        self._win = curses.newwin(
            *self._actual_height_and_width,
            self._upper_left_y,
            self._upper_left_x,
        )

        if self._boxed:
            self._win.box()

    @property
    def _viewable_height_and_width(self):
        """
        Calculate and return the viewable height and width of the window,
        accounting for borders if the window is boxed.

        Returns:
        - tuple: A tuple containing the viewable height and width.
        """
        screen_height, screen_width = self._stdscr.getmaxyx()
        drawable_height = screen_height - self._upper_left_y
        drawable_width = screen_width - self._upper_left_x
        viewable_height = min(self._height, drawable_height)
        viewable_width = min(self._width, drawable_width)

        if self._boxed:
            viewable_height -= 2
            viewable_width -= 2

        return viewable_height, viewable_width

    @property
    def _actual_height_and_width(self):
        """
        Calculate and return the actual height and width of the window,
        accounting for borders if the window is boxed.

        Returns:
        - tuple: A tuple containing the actual height and width.
        """
        viewable_height, viewable_width = self._viewable_height_and_width
        if self._boxed:
            return viewable_height + 2, viewable_width + 2
        else:
            return viewable_height, viewable_width

    def refresh(self, clear=False):
        """
        Refresh the window, optionally clearing it first.

        Parameters:
        - clear (bool): If True, clear the window before refreshing. Default is False.
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
        Deeply resize the window by clearing it, resizing it,
        redrawing its content, and then refreshing it.
        """
        self.clear()
        available_lines, available_cols = self._actual_height_and_width
        self._win.resize(available_lines, available_cols)
        self._win.touchwin()
        self._win.redrawwin()
        self.refresh()

    def resize(self):
        """
        Resize the window without clearing its content.
        """
        available_lines, available_cols = self._actual_height_and_width
        self._win.erase()
        self._win.resize(available_lines, available_cols)
        self.refresh()

    def _add_line_wrapped(self, line, y_offset, x_offset=0, attr=curses.A_NORMAL):
        """
        Add a wrapped line to the window at the specified offset with attributes.

        Parameters:
        - line (str): The line to be added.
        - y_offset (int): The y-coordinate offset.
        - x_offset (int): The x-coordinate offset. Default is 0.
        - attr (int): Text attributes (e.g., color). Default is curses.A_NORMAL.

        Raises:
        - ValueError: If the line is written outside of boundaries.
        """
        max_height, max_width = self._viewable_height_and_width

        if y_offset >= max_height:
            raise ValueError("Line written outside of boundaries")

        if self._boxed:
            y_offset += 1
            x_offset += 1

        words = line.split()
        current_line = ""
        current_y = y_offset

        for word in words:
            if len(current_line) + len(word) + 1 <= max_width - x_offset:
                if current_line:
                    current_line += " "
                current_line += word
            else:
                self._win.move(current_y, x_offset)
                self._win.insstr(current_line, attr)
                current_line = word
                current_y += 1
                if current_y >= max_height:
                    raise ValueError("Line written outside of boundaries")

        if current_line:
            self._win.move(current_y, x_offset)
            self._win.insstr(current_line, attr)

    def _add_line_truncated(self, line, y_offset, x_offset=0, attr=curses.A_NORMAL):
        """
        Add a truncated line to the window at the specified offset with attributes.

        Parameters:
        - line (str): The line to be added.
        - y_offset (int): The y-coordinate offset.
        - x_offset (int): The x-coordinate offset. Default is 0.
        - attr (int): Text attributes (e.g., color). Default is curses.A_NORMAL.

        Raises:
        - ValueError: If the line is written outside of boundaries.
        """
        max_height, max_width = self._viewable_height_and_width

        if y_offset >= max_height or x_offset >= max_width:
            raise ValueError("Line written outside of boundaries")

        if self._boxed:
            y_offset += 1
            x_offset += 1

        available_width = max_width - x_offset
        truncated_line = line[:available_width]
        self._win.move(y_offset, x_offset)
        self._win.insstr(truncated_line, attr)

    def _add_line(
        self, line, y_offset, x_offset=0, attr=curses.A_NORMAL, truncated=True
    ):
        """
        Add a line to the window, either truncated or not.

        Parameters:
        - line (str): The line to be added.
        - y_offset (int): The y-coordinate offset.
        - x_offset (int): The x-coordinate offset. Default is 0.
        - attr (int): Text attributes (e.g., color). Default is curses.A_NORMAL.
        - truncated (bool): Boolean indicating whether the line should be truncated. Default is True.
        """
        line = line.rstrip()
        if truncated:
            self._add_line_truncated(line, y_offset, x_offset, attr)
        else:
            self._add_line_wrapped(line, y_offset, x_offset, attr)
