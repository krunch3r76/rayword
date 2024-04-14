#!/usr/bin/env python3
# start_indexing_color.py
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


async def run_command(command, stdscr, pad, pad_line):
    """Run a single command asynchronously, updating the curses pad with output."""
    proc = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        # Assuming stdscr and pad are passed correctly and used within curses wrapper
        pad.addstr(pad_line[0], 0, line.decode())
        pad_line[0] += 1
        pad.refresh(0, 0, 0, 0, curses.LINES - 1, curses.COLS - 1)

    await proc.wait()


async def main_loop(stdscr, commands):
    curses.curs_set(0)
    pad = curses.newpad(1000, curses.COLS)
    pad_line = [0]

    for command in commands:
        await run_command(command, stdscr, pad, pad_line)
        # Optionally wait for user input here before continuing to the next command
        # stdscr.addstr(
        #     curses.LINES - 1, 0, "Press any key to continue to the next command..."
        # )
        # stdscr.refresh()
        # stdscr.getch()


def main():
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    try:
        asyncio.run(main_loop(stdscr, commands))
    finally:
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()


if __name__ == "__main__":
    main()
