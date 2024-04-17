#!/usr/bin/env python3
# start_indexing_color.py

from start_indexing.color_pairs import init_color_pairs
from start_indexing.parse_ansi_sequences import parse_ansi_sequences
from start_indexing.render_command_header import render_command_header
from start_indexing.windows import WrappedWindow, WrappedPad
import threading
from queue import Queue, Empty

commands = [
    "rm -rf app/output/*",
    "python3 main/update_or_insert_paths.py",
    "python3 main/prepare_unsearched_paths_json.py golem-cluster.yaml --batch-size 100",
    # "stdbuf -o0 'ray up golem-cluster.yaml --yes'",
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
import os
import logging

# Constants
CMD_WINDOW_HEIGHT = 2


# Set up logging
logging.basicConfig(
    filename="debug_log.txt",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


async def run_command(command, pad, pad_line, cmd_window):
    args = command.split()
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    line_buffer = ""
    try:
        while True:
            data = await proc.stdout.read(1024)
            if data:
                text = data.decode("utf-8", errors="ignore")
                logging.debug(f"Data read: {text}")
                for char in text:
                    if char == "\n":
                        if line_buffer:
                            pad_line[0] += 1
                            pad.move(pad_line[0], 0)
                            segments = parse_ansi_sequences(line_buffer)
                            for text, attr in segments:
                                pad.addstr(pad_line[0], pad.getyx()[1], text, attr)
                            line_buffer = ""
                    else:
                        line_buffer += char
            else:
                if proc.stdout.at_eof():
                    logging.debug("End of file reached.")
                    if line_buffer:  # Handle any remaining buffer
                        pad_line[0] += 1
                        pad.move(pad_line[0], 0)
                        segments = parse_ansi_sequences(line_buffer)
                        for text, attr in segments:
                            pad.addstr(pad_line[0], pad.getyx()[1], text, attr)
                    break
                else:
                    logging.debug("No data read, but not at EOF.")

            if proc.returncode is not None:
                logging.debug(f"Process exited with returncode {proc.returncode}.")
                break
            await asyncio.sleep(0.1)

    finally:
        # Ensure cleanup
        await proc.communicate()
        logging.debug("Process communicate completed.")

        # Ensure any remaining text in the buffer is processed
        if line_buffer:
            pad_line[0] += 1
            pad.move(pad_line[0], 0)
            segments = parse_ansi_sequences(line_buffer)
            for text, attr in segments:
                pad.addstr(pad_line[0], pad.getyx()[1], text, attr)


async def handle_user_input_and_auto_scroll(stdscr, pad, pad_line, exit_event):
    """Handle user input to scroll the pad display and auto-scroll until 'q' is pressed."""
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
                else:
                    # Already at the bottom, ensure auto-scrolling is active
                    auto_scroll_active = True
            elif ch == curses.KEY_UP:
                if current_line > 0:
                    current_line -= 1
                    auto_scroll_active = (
                        False  # User manually scrolled, stop auto-scrolling
                    )
            elif ch == ord("q"):
                exit_event.set()  # Set the exit event to signal the main loop to terminate
                break  # Exit the loop immediately
            elif ch == -1:  # No input
                # Auto-scroll to the bottom if new content is added and auto-scroll is active
                if auto_scroll_active:
                    current_line = max(
                        0, pad_line[0] - (curses.LINES - (CMD_WINDOW_HEIGHT + 1))
                    )

            # Refresh the pad if necessary
            if auto_scroll_active or ch in {curses.KEY_DOWN, curses.KEY_UP, -1}:
                pad.refresh(
                    current_line,
                    0,
                    CMD_WINDOW_HEIGHT + 1,
                    0,
                    curses.LINES - 1,
                    curses.COLS - 1,
                )

            await asyncio.sleep(0.05)  # Sleep briefly to reduce CPU usage
    finally:
        stdscr.nodelay(False)  # Restore blocking behavior


async def main_loop(stdscr, commands):
    cmd_window = WrappedWindow(CMD_WINDOW_HEIGHT, curses.COLS, 0, 0)
    pad = curses.newpad(10000, curses.COLS)
    pad_line = [0]
    exit_event = asyncio.Event()

    # Start user input handling task
    user_input_task = asyncio.create_task(
        handle_user_input_and_auto_scroll(stdscr, pad, pad_line, exit_event)
    )

    # Execute commands
    for command in commands:
        render_command_header(cmd_window, command)
        await run_command(command, pad, pad_line, cmd_window)
        cmd_window.refresh()

    # Wait until the user decides to exit
    await exit_event.wait()

    # Clean up
    user_input_task.cancel()

    # Optionally wait for the user input task to finish cleanly
    try:
        await user_input_task
    except asyncio.CancelledError:
        pass


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
