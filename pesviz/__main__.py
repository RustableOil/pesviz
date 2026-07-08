"""CLI entry point: parse arguments and hand off to pesviz.main.main."""

import argparse
from pesviz.main import main

def parse_args():
    """Parse the -fp/--filepath command-line argument."""
    parser = argparse.ArgumentParser()
    parser.add_argument( "-fp", "--filepath", type=str, required=True, help="File path to compressed search data file")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args)
