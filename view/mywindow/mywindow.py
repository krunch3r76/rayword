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
        padding=None,
        x_padding: int = 0,
        y_padding: int = 0,
    ):
        self._stdscr = stdscr
        self._upper_left_y = upper_left_y
        self._upper_left_x = upper_left_x
        screen_height, screen_width = self._stdscr.getmaxyx()
        self._height = (
            height if height is not None else screen_height - self._upper_left_y
        )
        self._width = width if width is not None else screen_width - self._upper_left_x
        self._boxed = boxed
        self._y_padding = y_padding
        self._x_padding = x_padding

        if padding is not None:
            self._y_padding, self._x_padding = padding, padding
        self._win = curses.newwin(
            *self._viewable_height_and_width,
            self._upper_left_y,
            self._upper_left_x,
        )

        if self._boxed:
            self._win.box()
        self.visible = True
        self.overlay_win = None

    @property
    def y_padding(self):
        # return y_padding plus 1 if boxed
        return self._y_padding + (1 if self._boxed else 0)
    
    @property
    def x_padding(self):
        # return x_padding plus 1 if boxed
        return self._x_padding + (1 if self._boxed else 0)

    @property
    def _viewable_height_and_width(self):
        """
        Calculate and return the viewable height and width of the window.

        This method takes into account the screen dimensions, the window's position,
        and its specified size to determine the actual viewable area.

        Returns:
            tuple: A tuple containing the viewable height and width.
        """
        screen_height, screen_width = self._stdscr.getmaxyx()
        max_drawable_height = screen_height - self._upper_left_y
        max_drawable_width = screen_width - self._upper_left_x
        viewable_height = min(self._height, max_drawable_height)
        viewable_width = min(self._width, max_drawable_width)
        return viewable_height, viewable_width

    @property
    def _actual_height_and_width(self):
        """
        Calculate and return the actual usable height and width of the window.

        This property takes into account the viewable dimensions, padding,
        and the boxed condition to determine the actual space available for content.

        Returns:
            tuple: A tuple containing the actual usable height and width.
        """
        viewable_height, viewable_width = self._viewable_height_and_width
        height_reduction = 2 * self.y_padding
        width_reduction = 2 * self.x_padding
        return (
            viewable_height - height_reduction,
            viewable_width - width_reduction,
        )


    def refresh(self, clear=False):
        if not self.visible:
            return
        if clear:
            self.clear()
        if self._boxed:
            self._win.box()
        self._win.refresh()

    def clear(self):
        self._win.clear()

    def resize_deep(self):
        self.clear()
        available_lines, available_cols = self._actual_height_and_width
        self._win.resize(available_lines, available_cols)
        self._win.touchwin()
        self._win.redrawwin()
        self.refresh()

    def resize(self):
        curses.update_lines_cols()
        available_lines, available_cols = self._viewable_height_and_width
        self._win.erase()
        self._win.resize(available_lines, available_cols)
        curses.napms(100)
        self.refresh()

    def _add_line_wrapped(self, line, y_offset, x_offset=0, attr=curses.A_NORMAL):
        max_height, max_width = self._viewable_height_and_width
        y_offset += self.y_padding
        # y_offset += 1 if self._boxed else 0
        x_offset += self.x_padding
        if y_offset >= max_height:
            raise ValueError("Line written outside of boundaries")
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
        max_height, max_width = self._viewable_height_and_width
        y_offset += self.y_padding
        # y_offset += 1 if self._boxed else 0
        x_offset += self.x_padding
        if y_offset > max_height or x_offset > max_width:
            raise ValueError(
                f"Line written outside of boundaries: y_offset: {y_offset}, x_offset: {x_offset} max_height: {max_height} max_width: {max_width}"
            )
        available_width = max_width - x_offset
        truncated_line = line[:available_width]
        self._win.move(y_offset, x_offset)
        self._win.insstr(truncated_line, attr)

    def _write_line(
        self, line, y_offset, x_offset=0, attr=curses.A_NORMAL, truncated=True
    ):
        line = line.rstrip()
        if truncated:
            self._add_line_truncated(line, y_offset, x_offset, attr)
        else:
            self._add_line_wrapped(line, y_offset, x_offset, attr)

    def add_line(self, segments, y_offset, wrapped=False):
        y_offset += self.y_padding
        # y_offset += 0 if self._boxed else 0
        if not isinstance(segments, list):
            segments = [
                (
                    segments,
                    curses.A_NORMAL,
                )
            ]
        x_offset = self.x_padding
        max_height, max_width = self._viewable_height_and_width
        if y_offset > max_height - 1 or x_offset > max_width - 1:
            return
            # raise ValueError(
            #     f"Line written outside of boundaries: y_offset: {y_offset}, x_offset: {x_offset} max_height: {max_height} max_width: {max_width}"
            # )
        for segment in segments:
            text, attr = segment
            self._add_line_segment(text, y_offset, x_offset, attr, not wrapped)
            x_offset += len(text)

    def _add_line_segment(
        self, line, y_offset, x_offset=0, attr=curses.A_NORMAL, truncated=True
    ):
        if not truncated:
            raise Exception("stylized text as wrapped not currently supported")
        max_height, max_width = self._viewable_height_and_width
        available_width = max_width - x_offset
        if available_width > 0:
            try:
                self._win.addstr(y_offset, x_offset, line[:available_width], attr)
            except Exception as e:
                logging.debug(
                    f"{e}\nuh oh, could not addstr at {y_offset}, {x_offset} available width: {available_width} line: {line[:available_width]}"
                )

    def hide(self):
        self.visible = False
        self.overlay_win = curses.newwin(
            self._height, self._width, self._upper_left_y, self._upper_left_x
        )
        self.overlay_win.clear()
        self.overlay_win.refresh()

    def show(self):
        self.visible = True
        if self.overlay_win:
            self.overlay_win.clear()
            self.overlay_win = None
        self.refresh()
