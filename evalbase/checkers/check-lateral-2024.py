#!/usr/bin/env python3

import re
import sys
import traceback
from pathlib import Path

# Check a Lateral Reading 2024 run for errors:
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


def check_clueweb_id(docid):
    return re.match(r'clueweb22-en\d{4}-\d{2}-\d{5}', docid)

def check_questions_run(runfile, log):
    the_runtag = None
    topics_file = Path(__file__).parent / 'trec-2024-lateral-reading-task1-articles.txt'
    topic_counts = {}

    with open(topics_file, 'r') as topics_fp:
        for line in topics_fp:
            topic_counts[line.strip()] = 0

    with open(runfile, 'r') as run:
        count = 0
        for line in run:
            fields = line.strip().split('\t', maxsplit=3)
            count += 1

            if len(fields) != 4:
                log.error(count, 'Line is missing a field')
                continue

            topic, runtag, qnum, question = fields

            if topic not in topic_counts:
                log.error(count, f'{topic} is not a valid document ID')
                continue

            if the_runtag == None:
                the_runtag = runtag
            else:
                if runtag != the_runtag:
                    log.error(count, f'{runtag} does not match runtag {the_runtag}')
                    continue

            qnum = int(qnum)
            if qnum < 1 or qnum > 10:
                log.error(count, f'{qnum} must be a number from 1 to 10')

            if topic_counts[topic] >= 10:
                log.error(count, f'Too many questions for document {topic}')

            topic_counts[topic] += 1

    for topic, nret in topic_counts.items():
        if nret == 0:
            log.error(count, f'Missing questions for document {topic}')
        elif nret < 10:
            log.warn(count, f'Document {topic} has only {nret} questions')



if __name__ == '__main__':
    import argparse

    ap = argparse.ArgumentParser(
        description='Checker for Lateral Reading runs')

    ap.add_argument('task', choices=['questions', 'documents'])
    ap.add_argument('runfile')

    args = ap.parse_args()

    with Errlog(args.runfile) as log:
        try:
            if args.task == 'questions':
                result = check_questions_run(args.runfile, log)
            elif args.task == 'documents':
                pass
        except Exception as e:
            log.error(-1, e)
            traceback.print_exc()
            sys.exit(255)

        if log.error_count > 0:
            sys.exit(255)
        else:
            sys.exit(0)
