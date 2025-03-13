# context_window.py

from ..mywindow.mywindow import MyWindow
from ..mywindow.line_buffered_window import MyWindowLineBufferedWrapped
from ..mywindow.source_window import SourceWindow
import logging

"""
    window for displaying the result of a text extraction

    ----------------------------------------
    |                                # / # |
    | <text>                               |
    |---------------------------------------
    | <source>                             |
    | <authors                             |
    ----------------------------------------
"""


class ContextWindow:
    """
    +count_window: MyWindow
    +text_window: MyWindowLineBufferedWrapped
    +source_window: SourceWindow
    """

    def __init__(self, stdscr, upper_left_y, upper_left_x, height, width):
        self.stdscr = stdscr
        self.upper_left_y = upper_left_y
        self.upper_left_x = upper_left_x

        HEIGHT_STATUS_LINE = 1
        HEIGHT_SOURCE_WINDOW = 4
        HEIGHT_TEXT_WINDOW = height - HEIGHT_STATUS_LINE - HEIGHT_SOURCE_WINDOW
        try:
            # count_window
            self.count_window = MyWindow(
                self.stdscr,
                upper_left_y,
                upper_left_x,
                height=HEIGHT_STATUS_LINE,
                width=width,
                x_padding=1,
                boxed=False,
            )
        except Exception as e:
            logging.debug(f"{e}")
            raise e
        self.count_window.refresh()
        # text_window
        self.text_window = MyWindowLineBufferedWrapped(
            self.stdscr,
            upper_left_y + HEIGHT_STATUS_LINE,
            upper_left_x,
            width=width,
            height=HEIGHT_TEXT_WINDOW,
            padding=1,
            boxed=True,
            scrolling=True,
        )

        # source_window
        self.source_window = SourceWindow(
            self.stdscr,
            upper_left_y + HEIGHT_STATUS_LINE + HEIGHT_TEXT_WINDOW + 0,
            upper_left_x,
            height=HEIGHT_SOURCE_WINDOW,
            width=width,
            x_padding=1,
            boxed=True,
        )

    def hide(self):
        self.count_window.hide()
        self.text_window.hide()
        self.source_window.hide()   

    def add_source(self, line):
        self.source_window.add_line(line)

    def add_line(self, line):
        self.text_window.add_line(line)

    def clear(self):
        self.count_window.clear()
        self.text_window.clear_buffer()
        self.text_window.clear()
        self.source_window.clear_buffer()
        self.source_window.clear()
        # TODO source_window

    def refresh(self):
        self.count_window.refresh()
        self.text_window.refresh()
        self.source_window.refresh()

    def scroll_up(self):
        self.text_window.scroll_up()

    def scroll_down(self):
        self.text_window.scroll_down()
