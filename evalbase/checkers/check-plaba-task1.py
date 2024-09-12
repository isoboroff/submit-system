#!/usr/bin/env python3

import re
import sys
import traceback
import collections
from pathlib import Path
import json

# Check a standard trec_eval formatted run for errors:
# - missing or non-matching runtag
# - incorrect or missing topics (documents)
# - fewer or more than 10 questions per topic
# - question numbers are numbers between 1 and 10

labels = {'SUBSTITUTE', 'GENERALIZE', 'EXPLAIN', 'EXEMPLIFY', 'OMIT'}
task1Bset = False
task1Cset = False

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

    def error(self, msg):
        print(f'ERROR: {msg}', file=self.fp)
        self.error_count += 1
        assert self.error_count <= self.max_errors, 'Too many errors'

    def warn(self, msg):
        print(f'WARNING: {msg}', file=self.fp)


def check_retrieval_run(args, log):
    the_runtag = None
    warned_about_q0 = False

    topics = collections.Counter()
    topics_docs = {}

    if args.testfile:
        testfile = Path(args.testfile)
        if not testfile.exists():
            testfile = Path(sys.path[0]) / args.testfile
            if not testfile.exists():
                raise FileNotFoundError(f'{args.testfile} not found')

        with open(testfile, 'r') as fp:
            test = json.load(fp)
    else:
        log.error("Test file required.")
        return

    with open(args.runfile, 'r') as run:
        try:
            data = json.load(run)
        except Exception as e:
            log.error(f"Couldn't parse run file as JSON ({e})")
            return
        
        for akey in test.keys():
            if akey not in data.keys():
                log.error(f'{akey} missing');
                continue
            global task1Bset, task1Cset
            try:
                for term, repls in data[akey].items():
                    if not isinstance(repls, str):
                        if task1Bset:
                            if not task1B:
                                log.error(f'To participate in Task 1B, all terms must have labels; found labels for {term} in {akey} but not for first term')
                        else:
                            task1Bset = True
                            task1B = True
                        for repl in repls:
                            task1B = True
                            if len(repl) == 0:
                                log.error(f'Term "{term}" in {akey} has empty label array')
                                continue
                            if repl[0] not in labels:
                                log.error(f'Invalid label "{repl[0]}" for term "{term}" in {akey}; labels must be one of {{{",".join(labels)}}}')
                            if task1Cset and task1C:
                                if len(repl) < 2 and repl[0] != 'OMIT':
                                    log.error(f'To participate in Task 1C, all non-OMIT labels must be accompanied by text (no text for label {repl[0]} for term "{term}" in {akey})')
                            elif task1Cset and not task1C:
                                if len(repl) > 1:
                                    log.error(f'To participate in Task 1C, all non-OMIT labels must be accompanied by text (label {repl[0]} for term "{term}" in {akey} has text but first label did not)')
                            if not task1Cset:
                                if repl[0] != 'OMIT' and len(repl) > 1 and len(repl[1]):
                                    task1C = True
                                    task1Cset = True
                                elif repl[0] != 'OMIT':
                                    task1C = False
                                    task1Cset = True
                            if repl[0] == 'OMIT' and len(repl) > 1 and len(repl[1]):
                                log.warn(f'Ignoring text entry for OMIT label for term "{term}" in {akey}')
                        if len(repl) > 2:
                            log.error(f'Too many items after label {repl[0]} for term "{term}" in {akey}; must be at most one more item (the text for Task 1C)')
                    elif isinstance(repls, str):
                        log.error(f'Value associated with term "{term}" in {akey} is a string; must be array if any')
            except AttributeError:
                if task1Bset:
                    if task1B:
                        log.error(f'To participate in Task 1B, all terms must have labels; missing for {term} in {akey}')
                else:
                    task1Bset = True
                    task1B = False

if __name__ == '__main__':
    import argparse

    ap = argparse.ArgumentParser(
        description='Checker for PLABA Task 1 runs',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    ap.add_argument('-t', '--testfile',
                    type=str,
                    default="",
                    help='Test JSON file')
    ap.add_argument('runfile')

    args = ap.parse_args()
    with Errlog(args.runfile) as log:
        try:
            result = check_retrieval_run(args, log)
        except Exception as e:
            log.error(e)
            traceback.print_exc()
            sys.exit(255)

        if log.error_count > 0:
            sys.exit(255)
        else:
            sys.exit(0)
