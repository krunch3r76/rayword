# render_command_header.py
import curses


def render_command_header(cmd_window: curses.window, command: str):
    cmd_window.clear()
    cmd_window.addstr(0, 0, f"Executing: {command}\n")
    cmd_window.insstr(1, 0, "─" * (cmd_window.getmaxyx()[1]))
    cmd_window.refresh()
