from .mywindow import ContextWindow
import curses
import logging


class PanelManager:
    # currently specialized for the context window
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.panels = []
        self.current_panel_index = 0

    def add_panel(self, upper_left_y, upper_left_x, height, width):
        panel = ContextWindow(self.stdscr, upper_left_y, upper_left_x, height, width)
        self.panels.append(panel)

    def add_line_to_current_panel(self, line):
        if self.panels:
            self.panels[self.current_panel_index].add_line(line)
            # self.panels[self.current_panel_index].refresh()

    def add_title_and_authors(self, title, authors):
        if self.panels:
            for line in title.splitlines():
                self.panels[self.current_panel_index].add_source(line)

            for line in authors.splitlines():
                self.panels[self.current_panel_index].add_source(line)

    def clear_current_panel(self):
        if self.panels:
            self.panels[self.current_panel_index].clear()

    def switch_panel(self, index):
        # logging.debug(
        #     f"THE INDEX IS: {index} and the len of panels is: {len(self.panels)}"
        # )
        if 0 <= index < len(self.panels):
            self.current_panel_index = index
            # self.panels[
            #     index
            # ].clear()  # Clear the new panel to reset the cursor position
            self.panels[index].refresh()

    def draw_panels(self):
        for panel in self.panels:
            panel.refresh()
        curses.panel.update_panels()
        curses.doupdate()

    def reset(self):
        for panel in self.panels:
            panel.clear()  # Clear the content of each panel
        self.panels = []
        self.current_panel_index = 0
        curses.panel.update_panels()
        curses.doupdate()

    @property
    def current_panel(self):
        return self.panels[self.current_panel_index]

    def scroll_up(self):
        self.panels[self.current_panel_index].scroll_up()

    def scroll_down(self):
        self.panels[self.current_panel_index].scroll_down()
