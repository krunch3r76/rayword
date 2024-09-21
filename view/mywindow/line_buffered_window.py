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
    def _top_line_index(self):
        """
        Calculate and return the index of the top visible line.

        Adjusts for the height of the window and the boxed condition.

        Returns:
        - int: The index of the top visible line.
        """
        # actual_height, _ = self._actual_height_and_width
        return max(0,self._current_line_index)

    @property
    def _bottom_line_index(self):
        """
        Calculate and return the index of the bottom visible line.

        Adjusts for the height of the window and the boxed condition.

        Returns:
        - int: The index of the bottom visible line.
        """
        actual_height, _ = self._actual_height_and_width
        return self._top_line_index + actual_height - 1
        if self._current_line_index >= actual_height:
            return self._current_line_index
        else:
            return min(actual_height - 1, len(self._lines) - 1)

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
            super()._write_line(line, cursor)
        if self._boxed:
            self._win.box()
        self._win.refresh()
        # super().refresh()

    def clear_buffer(self):
        self._lines = []

    def clear(self):
        """
        Clear all lines from the buffer and reset the current line index.
        """
        # self._lines = []
        self._current_line_index = -1
        super().clear()

    def add_line(self, line):
        """
        Add a new line to the buffer and update the current line index.

        Parameters:
        - line: The line to be added to the buffer.
        """
        logging.debug(f"----adding line: {line}, current line index: {self._current_line_index}")
        self._lines.append(line)
        # if self._scrolling:
        #     self._current_line_index += 1
        # else:
        viewable_height, _ = self._viewable_height_and_width
        # self._current_line_index = min(viewable_height - 1, len(self._lines) - 1)


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

    def clear_buffer(self):
        self.wrapped_lines = []
        self._lines = []

    def clear(self):
        """
        erase the visible content and reset the current line index
        """
        super().clear()
        self._current_line_index = -1
    

    def _wrap_lines(self):
        """
        Wrap lines to fit within the viewable width of the window.
        """
        # max_width = self._viewable_height_and_width[1]
        max_width = self._actual_height_and_width[1]
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

        logging.debug(f"wrapped lines: {self._wrapped_lines}")

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
            raise Exception(
                "breakpoint for only scrolling, please remove this exception for proper workflow"
            )
            viewable_height, _ = self._viewable_height_and_width
            self._current_line_index = min(
                viewable_height - 1, len(self._wrapped_lines) - 1
            )
    
    def _write_line(self, line, y_offset, x_offset=0, attr=curses.A_NORMAL):
        """
        Add a line to the window at the specified offset with attributes.

        Parameters:
        - line (str): The line to be added.
        - y_offset (int): The y-coordinate offset.
        - x_offset (int): The x-coordinate offset. Default is 0.
        - attr (int): Text attributes (e.g., color). Default is curses.A_NORMAL.
        """
        _, max_width = self._actual_height_and_width
        y_offset += self.y_padding
        x_offset += self.x_padding

        viewable_height, _ = self._viewable_height_and_width
        effective_y_padding = self.y_padding
        max_y_offset = viewable_height - effective_y_padding - 1

        if y_offset > max_y_offset:
            logging.debug(f"Line written outside of boundaries y_offset: {y_offset} where max_y_offset is: {max_y_offset}")
            logging.debug(f"---line: {line}")
            self.log_window_dimensions()
            raise Exception("Line written outside of boundaries")

        try:
            self._win.move(y_offset, x_offset)
            # logging.debug(f"writing line: {line} to y-offset {y_offset}")
            self._win.insstr(line, attr)
        except:
            logging.debug(f"COULD NOT ADD LINE: {line}")
            # kludge, include logic to not draw lines that would not fit
            pass

    def log_window_dimensions(self):
        """
        Log the dimensions and properties of the window for debugging purposes.
        """
        viewable_height, viewable_width = self._viewable_height_and_width
        actual_height, actual_width = self._actual_height_and_width
        
        effective_y_padding = self.y_padding
        effective_x_padding = self.x_padding
        
        y_start = effective_y_padding
        y_end = viewable_height - effective_y_padding - 1
        
        logging.debug(f"Window Dimensions:")
        logging.debug(f"  Viewable: {viewable_height}x{viewable_width}")
        logging.debug(f"  Actual: {actual_height}x{actual_width}")
        logging.debug(f"  Boxed: {self._boxed}")
        logging.debug(f"  Y Padding: {self._y_padding}")
        logging.debug(f"  X Padding: {self._x_padding}")
        logging.debug(f"  Effective Y Padding: {effective_y_padding}")
        logging.debug(f"  Effective X Padding: {effective_x_padding}")
        logging.debug(f"  Y Offset Range: {y_start} to {y_end}")


    @property
    def _top_line_index(self):
        """
        Calculate and return the index of the top visible line.

        Adjusts for the height of the window and the boxed condition.

        Returns:
        - int: The index of the top visible line.
        """
        # actual_height, _ = self._actual_height_and_width
        candidate = max(0,self._current_line_index)
        if len(self._wrapped_lines) -1 < candidate:
            return len(self._wrapped_lines) -1
        else:
            return candidate


    @property
    def _bottom_line_index(self):
        """
        Calculate and return the index of the bottom visible line.

        Adjusts for the height of the window and the boxed condition.

        Returns:
        - int: The index of the bottom visible line.
        """
        actual_height, _ = self._actual_height_and_width
        return self._top_line_index + actual_height - 1
        # return self._current_line_index + actual_height - 1
        if self._current_line_index >= actual_height:
            return self._current_line_index
        else:
            return min(actual_height - 1, len(self._wrapped_lines) - 1)

    def refresh(self, scrolling=False):
        """
        Refresh the window, drawing the wrapped lines.
        """
        if scrolling:
            line_index = self._current_line_index
            self.clear()
            self._current_line_index = line_index
        else:
            self.clear()

        logging.debug(f"top line index: {self._top_line_index} and bottom line index: {self._bottom_line_index}")
        for y_offset, line in enumerate(
            self._wrapped_lines[self._top_line_index : self._bottom_line_index + 1]
        ):
            logging.debug(f"writing line: {line} to y-offset {y_offset}")
            self._write_line(line, y_offset)
        if self._boxed:
            self._win.box()
        self._win.refresh()



    def scroll_up(self):
        """
        Scroll the view up by one line.
        """
        logging.debug(f"current line index: {self._current_line_index}")
        if self._current_line_index > 0:
            self._current_line_index -= 1
            self.refresh(True)

    def scroll_down(self):
        """
        Scroll the view down by one line.
        """
        if self._current_line_index < 0:
            self._current_line_index = 0
        
        actual_height, _ = self._actual_height_and_width
        max_scroll_index = len(self._wrapped_lines) - actual_height

        if self._top_line_index >= max_scroll_index:
            return

        # if self._current_line_index >= max_scroll_index:
        #     return

        self._current_line_index += 1
        self.refresh(True)

        # logging.debug(
        #     f"current line index: {self._current_line_index} < {len(self._wrapped_lines)}"
        # )
