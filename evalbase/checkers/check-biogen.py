#!/usr/bin/env python3

import collections
import json
import re
import sys
import traceback
import unicodedata
from pathlib import Path

import spacy
nlp = spacy.load('en_core_web_sm')


# Check a BioGen track generation output for
# - missing or non-matching run_id
# - incorrect or missing topics
# - malformed references
# - no sentences
# - generation length > 400


class Errlog:
    """This is meant to be used in a context manager, for example
    with Errlog(foo) as log:
        ...
    If not, be sure to call .close() when done.
    """

    def __init__(self, runfile, max_errors=930):
        self.filename = runfile + ".errlog"
        print(f"Writing errors to {self.filename}")
        self.fp = open(self.filename, "w")
        self.error_count = 0
        self.max_errors = max_errors

    def __enter__(self):
        return self

    def close(self):
        if self.error_count == 0:
            print("No errors", file=self.fp)
        self.fp.close()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def error(self, line, msg):
        print(f"ERROR Line {line}: {msg}", file=self.fp)
        self.error_count += 1
        if self.error_count > self.max_errors:
            raise Exception(f"{line} Stopping, too many errors")

    def warn(self, line, msg):
        print(f"WARNING Line {line}: {msg}", file=self.fp)


def check_biogen_run(args, log):
    DOCNO = re.compile(r'^\d+$')
    CITE = re.compile(r'\[(\d+?)\]')

    def fix_rag_answer(obj, current_length, count):
        log.warn(count, f"Attempting to fix RAG answer of length {current_length}")
        while current_length > 400 and obj["answer"]:
            last_sentence = obj["answer"].pop()
            text = last_sentence["text"].strip()
            tokenized = unicodedata.normalize("NFKC", text)
            tokens = tokenized.split()
            current_length -= len(tokens)
            log.warn(count, f"Removing a sentence from the end: {text}")
            log.warn(count, f"Updated length: {current_length}")

        obj["response_length"] = current_length
        return obj, current_length

    topics = collections.Counter()
    for t in range(116, 181):
        topics[t] = 0

    queries = {}

    run = open(args.runfile, "r")
    count = 0
    # Check JSON parse
    try:
        obj = json.load(run)
    except json.JSONDecodeError as j:
        log.error(count, f"Error parsing JSON line at {j.colno}")
        sys.exit(255)

    count = 1

    # Check that all root fields are present
    if not "team_id" in obj:
        log.error(count, 'Entry is missing "team_id" field.')

    # Check runtag
    if not "run_name" in obj:
        log.error(count, 'Entry is missing "run_name" field.')

    # Check email
    if not "contact_email" in obj:
        log.error(count, 'Entry is missing "contact_email" field.')

    # Check results
    if not "results" in obj:
        log.error(count, 'Entry is missing "results" field.')

    for output in obj['results']:
        if not "topic_id" in output:
            log.error(count, 'Results entry is missing "topic_id" field.')

        if int(output['topic_id']) not in topics:
            log.error(count, f'Invalid topic ID {output["topic_id"]}')

        if not "references" in output:
            log.error(count, 'Results entry is missing "references" field.')
            continue

        # Check references
        refs = set()
        for ref in output["references"]:
            if not DOCNO.match(ref):
                log.error(count, f'Invalid reference docno {ref} for topic {object["topic_id"]}')
            elif ref in refs:
                log.error(count, f'Duplicate document {ref} in references for topic {object["topic_id"]}')
            elif len(refs) > 3:
                log.warn(count, f'Too many references (max 3), extras ignored for topic {object["topic_id"]}')
            else:
                refs.add(ref)

        if not "answer" in output:
            log.error(count, 'Results entry is missing "answer" field.')
            continue

        tokd = nlp(output['answer'])
        if len(doc) > 500:
            log.error(count, f'Answer is too long for topic {object["topic_id"]}')

        # Check citations
        for cite in CITE.finditer(output['answer']):
            if cite.group(0) not in refs:
                log.error(count, f'Answer for topic {output["topic_id"]} has a citation that is not in the references list.')
            if not DOCNO.fullmatch(cite.group(1)):
                log.error(count, f'Answer for topic {output["topic_id"]} has a bogus docno as a citation .')


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Checker for TREC BioGen runs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    ap.add_argument("runfile")

    args = ap.parse_args()

    with Errlog(args.runfile) as log:
        try:
            result = check_biogen_run(args, log)
        except Exception as e:
            log.error(-1, e)
            traceback.print_exc()
            sys.exit(255)

        if log.error_count > 0:
            sys.exit(255)
        else:
            sys.exit(0)
