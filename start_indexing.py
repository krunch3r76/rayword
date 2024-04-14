#!/usr/bin/env python3
# start_indexing_color.py

from start_indexing.color_pairs import init_color_pairs
from start_indexing.parse_ansi_sequences import parse_ansi_sequences
from start_indexing.render_command_header import render_command_header

commands = [
    "rm -rf app/output/*",
    "python main/update_or_insert_paths.py",
    "python main/prepare_unsearched_paths_json.py golem-cluster.yaml --batch-size 100",
    "unbuffer ray up golem-cluster.yaml --yes",
    "ray rsync-up golem-cluster.yaml ./app/input/ /root/app/input/",
    "ray submit golem-cluster.yaml ./rayword.py --enable-console-logging",
    "ray rsync-down golem-cluster.yaml /root/app/output/ ./app/output",
    "python main/import_ray_results.py",
    "ray down golem-cluster.yaml --yes",
]

import asyncio
import curses
import re

# Constants
CMD_WINDOW_HEIGHT = 2


async def run_command(command, pad, pad_line, cmd_window):
    """Run a single command asynchronously and update the curses pad with output."""
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    line_buffer = ""
    try:
        while proc.returncode is None:
            try:
                data = await asyncio.wait_for(proc.stdout.read(1), timeout=0.1)
                if not data:
                    continue
                char = data.decode("utf-8", errors="ignore")
                if char == "\n":
                    pad_line[0] += 1
                    pad.move(pad_line[0], 0)
                    segments = parse_ansi_sequences(line_buffer)
                    for text, attr in segments:
                        pad.addstr(pad_line[0], pad.getyx()[1], text, attr)
                    line_buffer = ""
                else:
                    line_buffer += char
                # pad.refresh(
                #     0,
                #     0,
                #     CMD_WINDOW_HEIGHT + 1,
                #     0,
                #     curses.LINES - 1,
                #     curses.COLS - 1,
                # )
            except asyncio.TimeoutError:
                continue
    finally:
        if proc.returncode is None:
            await proc.wait()
        await proc.communicate()


async def handle_user_input_and_auto_scroll(stdscr, pad, pad_line):
    """Handle user input to scroll the pad display and auto-scroll."""
    current_line = 0
    auto_scroll_active = True  # Start with auto-scrolling enabled

    stdscr.nodelay(True)  # Set getch to non-blocking

    try:
        while True:
            ch = stdscr.getch()
            if ch == curses.KEY_DOWN:
                if current_line < pad_line[0] - curses.LINES + CMD_WINDOW_HEIGHT + 1:
                    current_line += 1
                    auto_scroll_active = (
                        False  # User manually scrolled, stop auto-scrolling
                    )
                    pad.refresh(
                        current_line,
                        0,
                        CMD_WINDOW_HEIGHT + 1,
                        0,
                        curses.LINES - 1,
                        curses.COLS - 1,
                    )
                else:
                    auto_scroll_active = True
            elif ch == curses.KEY_UP:
                if current_line > 0:
                    current_line -= 1
                    auto_scroll_active = (
                        False  # User manually scrolled, stop auto-scrolling
                    )
                    pad.refresh(
                        current_line,
                        0,
                        CMD_WINDOW_HEIGHT + 1,
                        0,
                        curses.LINES - 1,
                        curses.COLS - 1,
                    )
            elif ch == ord("q"):
                break
            elif ch == -1:  # No input
                if auto_scroll_active and current_line != pad_line[0] - (
                    curses.LINES - (CMD_WINDOW_HEIGHT + 1)
                ):
                    # Update scroll to the bottom if new content is added beyond the screen view
                    current_line = pad_line[0] - (
                        curses.LINES - (CMD_WINDOW_HEIGHT + 1)
                    )
                    pad.refresh(
                        current_line,
                        0,
                        CMD_WINDOW_HEIGHT + 1,
                        0,
                        curses.LINES - 1,
                        curses.COLS - 1,
                    )

            # Refresh only if necessary
            # if auto_scroll_active or ch != -1:
            #     pad.refresh(
            #         current_line,
            #         0,
            #         CMD_WINDOW_HEIGHT + 1,
            #         0,
            #         curses.LINES - 1,
            #         curses.COLS - 1,
            #     )

            await asyncio.sleep(0.05)  # Sleep briefly to reduce CPU usage
    finally:
        stdscr.nodelay(False)  # Restore blocking behavior


async def main_loop(stdscr, commands):
    """Main loop to execute commands and manage UI."""
    cmd_window = curses.newwin(CMD_WINDOW_HEIGHT, curses.COLS, 0, 0)
    pad = curses.newpad(1000, curses.COLS)
    pad_line = [0]

    # Start user input handling task
    user_input_task = asyncio.create_task(
        handle_user_input_and_auto_scroll(stdscr, pad, pad_line)
    )

    # Execute commands
    for command in commands:
        render_command_header(cmd_window, command)
        await run_command(command, pad, pad_line, cmd_window)
        cmd_window.refresh()

    # Clean up
    user_input_task.cancel()


def main():
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    curses.start_color()
    init_color_pairs()

    try:
        asyncio.run(main_loop(stdscr, commands))
    finally:
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()


if __name__ == "__main__":
    main()
