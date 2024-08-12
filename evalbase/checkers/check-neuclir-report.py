#!/usr/bin/env python3

import re
import sys
import traceback
import json
import unicodedata
import collections
from pathlib import Path

# Check a NeuCLIR report generation run for the following:
# - missing or non-matching run_id
# - incorrect or missing requests (documents)
# - no sentences
# - report length

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
        if (self.error_count > self.max_errors):
            raise Exception(f'{line} Stopping, too many errors')

    def warn(self, line, msg):
        print(f'WARNING Line {line}: {msg}', file=self.fp)

UUID = re.compile(r'^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}\Z', re.I)

def check_neuclir_report_run(args, log):
    the_runtag = None

    topics = collections.Counter()

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

    with open(args.runfile, 'r') as run:
        count = 0
        for line in run:
            count += 1
            length = 0

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as j:
                log.error(count, f'Error parsing JSON line at {j.colno}')
                continue

            if not ('request_id' in obj and
                    'run_id' in obj and
                    'collection_ids' in obj and
                    'sentences' in obj):
                log.error(count, 'Entry is missing a required field.')
                continue

            request_id = obj['request_id']
            run_id = obj['run_id']

            if the_runtag is None:
                the_runtag = run_id
            elif the_runtag != obj['run_id']:
                log.error(count, f'Run tag inconsistent ("{obj["run_id"]}" instead of "{the_runtag}")')

            if request_id not in topics:
                if args.topicfile:
                    log.error(count, f'Unknown request ({request_id})')
                    # end checks for this line
                    continue
                else:
                    log.error(count, f'Unknown request ({request_id})')


            for coll in obj['collection_ids']:
                if coll not in ['neuclir/1/zho','neuclir/1/rus','neuclir/1/fas']:
                    error(count, f'Bogus collection id {coll}')

            if not obj['sentences']:
                log.error(count, f'No report sentences for request {request_id}')
                # skip sentence checks
                continue

            for s in obj['sentences']:
                if not ('text' in s and
                        'citations' in s):
                    log.error(count, 'Entry sentence is missing a field')
                    continue

                length += len(unicodedata.normalize('NFKC', s['text']))

                if len(s['citations']) > 2:
                    log.error(count, 'Too many citations (max 2 per sentence)')

                these_sites = set()
                for cite in s['citations']:
                    if not UUID.match(cite):
                        log.error(count, 'Bogus docid in citation')
                    if cite in these_sites:
                        log.error(count, 'Repeated citation')

                    these_sites.add(cite)

            if length > 2000:
                log.error(count, f'Report is too long ({length} chars)')

            topics[request_id] += 1

    for topic in topics:
        if topics[topic] == 0:
            log.error(count, f'No reports returned for request {topic}')
        elif topics[topic] > 1:
            log.error(count, f'Too many reports ({topics[topic]}) generated for reuqest {topic}')



if __name__ == '__main__':
    import argparse

    ap = argparse.ArgumentParser(
        description='Checker for normal TREC runs',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    ap.add_argument('-f', '--topicfile',
                    required=True,
                    help='File containing topic IDs')
    ap.add_argument('runfile')

    args = ap.parse_args()

    with Errlog(args.runfile) as log:
        try:
            result = check_neuclir_report_run(args, log)
        except Exception as e:
            log.error(-1, e)
            traceback.print_exc()
            sys.exit(255)

        if log.error_count > 0:
            sys.exit(255)
        else:
            sys.exit(0)
