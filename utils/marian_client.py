#!/usr/bin/env python3
"""
A client that connects to a Marian server and translates text interactively.
Run `python utils.marian_client.py` and type a text to translate in the terminal
Source: https://github.com/marian-nmt/marian-dev/blob/master/scripts/server/client_example.py
"""


from __future__ import division, print_function, unicode_literals

import argparse
import sys

from websocket import create_connection

if __name__ == "__main__":
    # handle command-line options
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,  # Preserves whitespace in the help text.
    )
    parser.add_argument("-b", "--batch-size", type=int, default=1)
    parser.add_argument("-p", "--port", type=int, default=8886)
    args = parser.parse_args()

    # open connection
    ws = create_connection(f"ws://localhost:{args.port}/translate")

    count = 0
    batch = ""
    for line in sys.stdin:
        count += 1
        batch += line.decode("utf-8") if sys.version_info < (3, 0) else line
        if count == args.batch_size:
            # translate the batch
            ws.send(batch)
            result = ws.recv()
            print(result.rstrip())

            count = 0
            batch = ""

    if count:
        # translate the remaining sentences
        ws.send(batch)
        result = ws.recv()
        print(result.rstrip())

    # close connection
    ws.close()
