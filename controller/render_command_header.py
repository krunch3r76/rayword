# render_command_header.py
import curses


def render_command_header(cmd_window, command: str, failed=False):
    cmd_window.clear()
    if not failed:
        cmd_window.add_wrapped_text(f"Executing: {command}")
    else:
        cmd_window.add_wrapped_text(f"FAILED: {command}")
    cmd_window.insert_wrapped_text(1, 0, "─" * (cmd_window.max_x))
    cmd_window.refresh()
