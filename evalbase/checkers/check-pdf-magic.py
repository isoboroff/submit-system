#!/usr/bin/env python3

import filetype
import argparse
import sys
import re
import sys
import traceback
import collections
from pathlib import Path

# Check a paper submission for errors:
# - must be PDF

class Errlog():
    '''This is meant to be used in a context manager, for example
    with Errlog(foo) as log:
        ...
    If not, be sure to call .close() when done.
    '''
    def __init__(self, runfile, max_errors=25):
        self.filename = runfile + '.errlog'
        self.fp = open(self.filename, 'w')
        self.error_count = 0
        self.max_errors = max_errors

    def __enter__(self):
        return self

    def close(self):
        if self.error_count == 0:
            print('No errors', file=self.fp)
        self.fp.close()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def error(self, line, msg):
        print(f'ERROR Line {line}: {msg}', file=self.fp)
        self.error_count += 1
        assert self.error_count <= self.max_errors, 'Too many errors'

    def warn(self, line, msg):
        print(f'WARNING Line {line}: {msg}', file=self.fp)


def check_paper(args, log):
    kind = filetype.guess(args.runfile)
    if kind is None:
        log.error(-1, 'File type cannot be checked, contact admin.')
        return
    if kind.mime != 'application/pdf':
        log.error(-1, 'Paper file type must be PDF.')
        return

if __name__ == '__main__':
    import argparse

    ap = argparse.ArgumentParser(
        description='Checker for normal TREC runs',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    ap.add_argument('runfile')

    args = ap.parse_args()
    with Errlog(args.runfile) as log:
        try:
            result = check_paper(args, log)
        except Exception as e:
            log.error(-1, e)
            traceback.print_exc()
            sys.exit(255)

        if log.error_count > 0:
            sys.exit(255)
        else:
            sys.exit(0)

