#!/usr/bin/env python3

import re
import sys
import traceback
import collections
from pathlib import Path

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

    def error(self, line, msg):
        print(f'ERROR Line {line}: {msg}', file=self.fp)
        self.error_count += 1
        assert self.error_count <= self.max_errors, 'Too many errors'

    def warn(self, line, msg):
        print(f'WARNING Line {line}: {msg}', file=self.fp)


def check_retrieval_run(args, log):
    the_runtag = None
    warned_about_q0 = False

    topics = collections.Counter()
    topics_docs = {}

    if args.topicfile:
        topicfile = Path(args.topicfile)
        if not topicfile.exists():
            topicfile = Path(sys.path[0]) / args.topicfile
            if not topicfile.exists():
                raise FileNotFoundError(f'{args.topicfile} not found')

        with open(topicfile, 'r') as fp:
            for line in fp:
                t = line.strip()
                topics[t] = 0
                topics_docs[t] = dict()

    with open(args.runfile, 'r') as run:
        count = 0
        for line in run:
            fields = line.strip().split()
            count += 1

            if len(fields) == 6:
                topic, q0, docno, rank, sim, runtag = fields
            else:
                log.error(count, 'Wrong number of fields (expecting 6)');
                # critical failure, stop checking
                return

            if the_runtag is None:
                the_runtag = runtag
            elif the_runtag != runtag:
                log.error(count, f'Run tag inconsistent ("{runtag}" instead of "{the_runtag}")')
            elif runtag != args.runfile:
                log.error(count, f'Runtag does not match file')
                # catastophic fail, stop checking
                return

            if topic not in topics:
                if args.topicfile:
                    log.error(count, f'Unknown test topic ({topic})')
                    # end checks for this line
                    continue
                elif args.topics.match(topic):
                    topics_docs[topic] = {}
                else:
                    log.error(count, f'Unknown tests topic ({topic})')

            if q0 != 'Q0' and not warned_about_q0:
                log.error(count, f'Field 2 is "{q0}" and not Q0')
                # If they got it wrong on one line, it's probably on all the lines
                warned_about_q0 = True

            # Check that rank is a positive integer
            testrank = int(rank)
            if testrank < 0 or str(testrank) != rank:
                log.error(count, f'Column 4 (rank) {rank} must be a positive integer')

            if args.docnos.fullmatch(docno):
                if docno in topics_docs[topic]:
                    log.error(count, f'{docno} retrieved more than once for topic {topic}')
                    continue
                else:
                    topics_docs[topic][docno] = sim
            else:
                log.error(count, f'Unrecognized docno {docno}')
                continue
            topics[topic] += 1

    for topic in topics:
        if topics[topic] == 0:
            log.error(count, f'No documents retrieved for topic {topic}')
        elif topics[topic] > args.maxret:
            log.error(count, f'Too many documents ({topics[topic]}) retrieved for topic {topic}')



if __name__ == '__main__':
    import argparse

    ap = argparse.ArgumentParser(
        description='Checker for normal TREC runs',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    def make_re(s):
        return re.compile(s, re.IGNORECASE)

    ap.add_argument('-t', '--topics',
                    type=make_re,
                    default=re.compile(r'\d+'),
                    help='Regular expression for topics')
    ap.add_argument('-f', '--topicfile',
                    help='File containing topic IDs')
    ap.add_argument('-d', '--docnos',
                    type=make_re,
                    default=re.compile(r'\w+'),
                    help='Regular expression for docnos')
    ap.add_argument('-m', '--maxret',
                    type=int,
                    default=1000,
                    help='Maximum number of documents allowed for a topic')
    ap.add_argument('runfile')

    args = ap.parse_args()
    with Errlog(args.runfile) as log:
        try:
            result = check_retrieval_run(args, log)
        except Exception as e:
            log.error(-1, e)
            traceback.print_exc()
            sys.exit(255)

        if log.error_count > 0:
            sys.exit(255)
        else:
            sys.exit(0)
