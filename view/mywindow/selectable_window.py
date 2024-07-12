# selectablewindow.py

from .mywindow import MyWindow
import curses
import logging

from .line_buffered_window import MyWindowLineBuffered


class MyWindowSelectable(MyWindowLineBuffered):
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
        Initialize a selectable line-buffered window with the given parameters.

        Parameters:
        - stdscr: The main curses window object.
        - upper_left_y: The upper-left y-coordinate of the window.
        - upper_left_x: The upper-left x-coordinate of the window.
        - height: The height of the window.
        - width: The width of the window.
        - boxed: Boolean indicating whether the window should have a border.
        """
        super().__init__(stdscr, upper_left_y, upper_left_x, height, width, boxed)
        self._selected_line_index = -1

    def resize(self):
        """
        Resize the window while maintaining the current selection and line indices.
        """
        super().resize()

    def clearlines(self):
        """
        Clear all lines from the buffer and reset the current selection index.
        """
        super().clearlines()
        self._selected_line_index = -1

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
            corresponding_line_index = self._top_line_index + cursor
            if corresponding_line_index == self._selected_line_index:
                super()._add_line(line, cursor, attr=curses.A_REVERSE)
            else:
                super()._add_line(line, cursor)
        if self._boxed:
            self._win.box()
        self._win.refresh()

    def move_selection_down(self):
        """
        Move the selection down by one line.

        If the selection is at the bottom visible line, scroll down.
        """
        if self._selected_line_index == -1:
            self._selected_line_index = self._top_line_index
        elif self._selected_line_index < self._bottom_line_index:
            self._selected_line_index += 1
        else:
            if self._selected_line_index == self._bottom_line_index:
                if self._current_line_index < len(self._lines) - 1:
                    self._current_line_index += 1
                    self._selected_line_index += 1
        self.refresh()
        logging.debug(
            f"selected_line_index after keypress: {self._selected_line_index}, current_line_index: {self._current_line_index}, bottom_line_index: {self._bottom_line_index}, last index: {len(self._lines) - 1}\n"
        )

    def move_selection_up(self):
        """
        Move the selection up by one line.

        If the selection is at the top visible line, scroll up.
        """
        logging.debug(
            f"selected_line_index at keypress: {self._selected_line_index}, current_line_index: {self._current_line_index}, top_line_index: {self._top_line_index}"
        )
        if self._selected_line_index > 0:
            self._selected_line_index -= 1
            if self._selected_line_index < self._top_line_index:
                self._current_line_index -= 1
        else:
            self._selected_line_index = -1
        self.refresh()
