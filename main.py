"""Entry point: launch CLI when arguments are provided, GUI otherwise.

Usage
-----
GUI mode (no arguments):
    python main.py

CLI mode:
    python main.py <input_dir> [options]
    python main.py --help

Force CLI without launching GUI:
    python main.py --no-gui <input_dir> [options]
"""

import sys


def main():
    args = sys.argv[1:]

    # Strip --no-gui sentinel if present.
    force_cli = "--no-gui" in args
    if force_cli:
        args = [a for a in args if a != "--no-gui"]
        sys.argv = [sys.argv[0]] + args

    # If there are remaining positional-looking arguments treat as CLI.
    has_positional = any(not a.startswith("-") for a in args)

    if force_cli or has_positional:
        from video_resizer.cli import main as cli_main
        sys.exit(cli_main())
    else:
        from video_resizer.gui import run_gui
        run_gui()


if __name__ == "__main__":
    main()
