#!/usr/bin/env python3

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
        if line == -1:
            print(f'ERROR: {msg}', file=self.fp)
        else:
            print(f'ERROR Line {line}: {msg}', file=self.fp)
        self.error_count += 1
        assert self.error_count <= self.max_errors, 'Too many errors'

    def warn(self, line, msg):
        if line == -1:
            print(f'WARNING: {msg}')
        else:
            print(f'WARNING Line {line}: {msg}', file=self.fp)

if __name__ == '__main__':
    import argparse
    import re
    import subprocess
    import sys
    import traceback
    from pathlib import Path

    ap = argparse.ArgumentParser(
        description='Checker for RAGTIME generation runs',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    ap.add_argument('runfile')
    args = ap.parse_args()

    home = Path(sys.path[0])

    with Errlog(args.runfile) as log:
        try:
            result = subprocess.run([
                'rag_run_validator',
                '--topics', home / "aux/ragtime25_main_all.jsonl",
                '--strict_on_length',
                args.runfile],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            for line in result.stdout.splitlines():
                if re.search(r'\[Error:(\d+)\]', line):
                    log.error(-1, line)
                else:
                    log.warn(-1, line)
            if result.returncode != 0:
                sys.exit(255)
            else:
                sys.exit(0)
                
        except Exception as e:
            log.error(-1, e)
            traceback.print_exc()
            sys.exit(255)

        if log.error_count > 0:
            sys.exit(255)
        else:
            sys.exit(0)
