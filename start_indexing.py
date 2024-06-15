#!/usr/bin/env python3
# start_indexing_color.py

import asyncio
import curses
import logging
import subprocess
import time


# from start_indexing.render_command_header import render_command_header
from view.color_pairs import init_color_pairs
from view.windows import WrappedWindow, WrappedPad
from view.cmd_window import CmdWindow
from view.log_window import LogWindow

# import threading
# from queue import Queue, Empty

commands = [
    "echo 'Hello, worlds!'",
    "rm -rf app/output/*",
    "python3 main/update_or_insert_paths.py",
    "python3 main/prepare_unsearched_paths_json.py golem-cluster.yaml --batch-size 50",
    # "unbuffer ray up golem-cluster.yaml --yes --redirect-command-output --use-normal-shells",
    # "ray up golem-cluster.yaml --yes > >(cat)",
    "ray up golem-cluster.yaml --yes",
    # "stdbuf -oL -eL ray up golem-cluster.yaml --yes --redirect-command-output --use-normal-shells",
    # "./run_ray_up.sh golem-cluster.yaml --yes --redirect-command-output --use-normal-shells 2>&1",
    # "./run_ray_up.sh golem-cluster.yaml --yes",
    "ray rsync-up golem-cluster.yaml ./app/input/ /root/app/input/",
    "ray submit golem-cluster.yaml ./rayword.py --enable-console-logging",
    "ray rsync-down golem-cluster.yaml /root/app/output/ ./app/output",
    "python main/import_ray_results.py",
    "ray down golem-cluster.yaml --yes",
]


# Constants
CMD_WINDOW_HEIGHT = 2


# Set up logging
logging.basicConfig(
    filename="debug.log",
    filemode="w",
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s:%(levelname)s - %(message)s",
)


# Create a separate logger for specific log messages
temp_logger = logging.getLogger("temp_logger")
temp_logger.setLevel(logging.DEBUG)  # Set the desired logging level
file_handler = logging.FileHandler(
    "temp.log", mode="w"
)  # Set the file to write specific logs
file_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
)
temp_logger.addHandler(file_handler)
temp_logger.propagate = False


cmd_output_logger = logging.getLogger("cmdout_logger")
cmd_output_logger.setLevel(logging.DEBUG)  # Set the desired logging level
file_handler = logging.FileHandler(
    "cmdout.log", mode="w"
)  # Set the file to write specific logs
file_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
)
cmd_output_logger.addHandler(file_handler)
cmd_output_logger.propagate = False


update_event = asyncio.Event()


def is_process_sleeping(pid):
    """Check if a process with the given PID is in a 'sleeping' state."""
    try:
        # Read the process status from /proc/PID/status
        with open(f"/proc/{pid}/status", "r") as status_file:
            status_lines = status_file.readlines()

        # Search for the line containing the process state
        for line in status_lines:
            if line.startswith("State:"):
                # Extract the process state from the line
                state = line.split()[1]
                # Check if the process state indicates it is sleeping
                return state == "S"
    except FileNotFoundError:
        # Process with the given PID doesn't exist
        return False
    except Exception as e:
        # Handle other exceptions
        print(f"Error checking process state: {e}")
        return False


async def run_command(command, pad):
    # Start the subprocess
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Read stdout and stderr concurrently
    await asyncio.gather(
        read_lines_from_stream(proc.stdout, pad, proc),
        read_lines_from_stream(proc.stderr, pad, proc),
    )

    # Wait for the process to finish
    return await proc.wait()


async def read_lines_from_stream(stream, pad, proc):
    """read and process each line from the given stream"""
    while True:
        line = ""
        try:
            line = await asyncio.wait_for(stream.readline(), timeout=1.0)
        except asyncio.TimeoutError:
            continue
        if len(line) > 0:
            line = line.decode("utf-8")
            cmd_output_logger.debug(line)
            await print_line_to_ncurses_window(line, pad)
        else:
            break  # Exit the loop when no more data is available


async def print_line_to_ncurses_window(line: str, pad):
    pad.add_line(line)


async def handle_user_input_and_auto_scroll(
    stdscr, pad, windows_to_refresh, exit_event
):
    current_line_offset = 0
    auto_scroll_active = (
        True  # This flag is used to determine if the pad should auto-scroll
    )
    stdscr.nodelay(True)  # Non-blocking input
    last_timestamp = time.time()
    resizing_timer = False
    try:
        while not exit_event.is_set():
            ch = stdscr.getch()
            if ch == curses.KEY_DOWN:
                if current_line_offset > 0:
                    current_line_offset -= 1
                    if current_line_offset == 0:
                        auto_scroll_active = True
                    else:
                        update_event.set()
            elif ch == curses.KEY_UP:
                logging.debug(f"KEY_UP: current line offset is {current_line_offset}")
                if pad._pminrow - current_line_offset >= 0:
                    current_line_offset += 1
                    auto_scroll_active = False
                    update_event.set()
            elif ch == ord("q"):
                exit_event.set()
            elif ch == curses.KEY_RESIZE:
                if not resizing_timer:
                    last_timestamp = time.time()
                    resizing_timer = True

                curses.update_lines_cols()
                # check if enough time has passed
            elif ch == -1 and auto_scroll_active:  # No input and autoscroll is active
                # Auto-scroll to the most recent line that fits on screen

                if current_line_offset == 0:
                    # current_line = max(
                    #     0, pad._padline - (curses.LINES - CMD_WINDOW_HEIGHT - 1)
                    # )
                    update_event.set()

            if resizing_timer and time.time() - last_timestamp > 0.1:
                resizing_timer = False
                for window in windows_to_refresh:
                    window.resize()

            # Refresh logic: only refresh if the update event is set or autoscrolling is active
            if update_event.is_set():
                if not auto_scroll_active:
                    pad.refresh(pad._pminrow - current_line_offset)
                else:
                    pad.refresh()
                update_event.clear()
            await asyncio.sleep(0.1)
    finally:
        stdscr.nodelay(False)


async def main_loop(stdscr, commands):
    # cmd_window = WrappedWindow(CMD_WINDOW_HEIGHT, curses.COLS, 0, 0)
    curses.curs_set(0)
    cmd_window = CmdWindow(stdscr, 0, 0)
    screen_height, screen_width = stdscr.getmaxyx()
    pad = LogWindow(
        stdscr, CMD_WINDOW_HEIGHT, 0, screen_height - CMD_WINDOW_HEIGHT, screen_width
    )
    exit_event = asyncio.Event()

    # Start user input handling task
    user_input_task = asyncio.create_task(
        handle_user_input_and_auto_scroll(stdscr, pad, [cmd_window], exit_event)
    )

    # Execute commands
    for command in commands:
        cmd_window.update_command(command)
        progress_task = asyncio.create_task(cmd_window.update_progress_meter())

        # render_command_header(cmd_window, command)
        return_code = await run_command(
            command, pad
        )  # This function now returns the return code
        progress_task.cancel()
        temp_logger.debug(f"return code: {return_code} from cmd {command}")
        cmd_window.refresh()
        if return_code != 0:  # Check if the return code is not zero
            logging.error(
                f"Command '{command}' failed with return code {return_code}. Stopping execution of further commands."
            )
            cmd_window.update_command(command, failed=True)
            # render_command_header(cmd_window, command, failed=True)
            update_event.set()
            break  # Stop executing further commands

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
