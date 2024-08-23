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
        
        for qkey, qitem in test.items():
            if qkey not in data:
                log.error(f'{qkey} missing');
                continue

            if 'abstracts' not in data[qkey]:
                log.error(f'Field "abstracts" missing from {qkey}');
                continue

            for akey, aitem in qitem['abstracts'].items():
                if akey not in data[qkey]['abstracts']:
                    log.error(f'{akey} not in {qkey}');
                    continue
                
                if 'sentences' not in data[qkey]['abstracts'][akey]:
                    log.error(f'Field "sentences" missing from {qkey} {akey}');
                    continue

                l1 = len(aitem['sentences'])
                l2 = len(data[qkey]['abstracts'][akey]['sentences'])
                if l1 != l2:
                    log.error(f'{qkey} {akey} should have {l1} sentences but has {l2}')



if __name__ == '__main__':
    import argparse

    ap = argparse.ArgumentParser(
        description='Checker for PLABA Task 2 runs',
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
