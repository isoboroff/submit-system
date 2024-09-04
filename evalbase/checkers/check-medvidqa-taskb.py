#!/usr/bin/env python3

import json
import sys
import os
import traceback
from pathlib import Path

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
        print(f'ERROR  {msg}', file=self.fp)
        self.error_count += 1
        assert self.error_count <= self.max_errors, 'Too many errors'

    def warn(self, msg):
        print(f'WARNING  {msg}', file=self.fp)

    def info(self, msg):
        print(f'INFO {msg}', file=self.fp)


def read_json(data_path):
    #### reading the json file
    with open(data_path, "r") as rfile:
        data_items = json.load(rfile)
    return data_items


def check_fields(data_path, log, sample_size=90):
    #### check the json file contains the required fields
    data_items = read_json(data_path)
    if len(data_items) != sample_size:
        log.error(
            f"submitted prediction json file doesn't have predictions for all {sample_size} segments!"
        )

    for data_item in data_items:
        if "sample_id" not in data_item:
            log.error(
                f"submitted prediction json file doesn't have required 'sample_id' field for {data_item}!"
            )

        if data_item["sample_id"] == "" or data_item["sample_id"] == None:
            log.error(
                f"submitted prediction json file have empty 'sample_id' field for {data_item}"
            )

        if "steps_list" not in data_item:
            log.error(
                f"submitted prediction json file doesn't have required 'steps_list' field for {data_item}!"
            )

        if "steps_list" in data_item and type(data_item["steps_list"]) is not list:
            log.error(
                f"submitted prediction json file doesn't have 'steps_list' list for {data_item}!"
            )

        if len(data_item["steps_list"]) == 0:
            log.error(
                f"submitted prediction json file have zero 'steps_list' for sample id {data_item['sample_id']}!"
            )

        for step_item in data_item["steps_list"]:
            if type(step_item) is not dict:
                log.error(
                    f"submitted prediction json file have following issue: the data type is not dictionary for one of the 'steps_list' related to sample id {data_item['sample_id']}!"
                )

            if "step_caption" not in step_item:
                log.error(
                    f"submitted prediction json file doesn't have required 'step_caption' field for sample id {data_item['sample_id']}!"
                )

            if step_item["step_caption"] == "" or step_item["step_caption"] == None:
                log.error("'step_caption' field can not be empty")

            if "step_caption_start" not in step_item:
                log.error(
                    f"submitted prediction json file doesn't have required 'step_caption_start' field for sample id {data_item['sample_id']}!"
                )

            if (
                step_item["step_caption_start"] == ""
                or step_item["step_caption_start"] == None
            ):
                log.error(
                    f"'step_caption_start' field can not be empty for for sample id {data_item['sample_id']}!"
                )

            if "step_caption_end" not in step_item:
                log.error(
                    f"submitted prediction json file doesn't have required 'step_caption_end' field for sample id {data_item['sample_id']}!"
                )

            if (
                step_item["step_caption_end"] == ""
                or step_item["step_caption_end"] == None
            ):
                log.error(
                    f"'step_caption_end' field can not be empty for for sample id {data_item['sample_id']}!"
                )


def check_non_ascii_characters(submission_file_path, log):
    ### check for non_asciii characters
    data_item_list = read_json(submission_file_path)
    for data_item in data_item_list:
        for key, value in data_item.items():
            if not str(value).isascii():
                log.error(f"Non-ascii characters in the file: {value}")
    return True


def read_and_validate_json(submission_file_path, log):
    ##### to check the validatity of the submission file

    check_fields(submission_file_path, log)
    check_non_ascii_characters(submission_file_path, log)

    log.info("Submission file validated successfully!!")


def main():
    with Errlog(sys.argv[1]) as log:
        try:
            prediction_file = sys.argv[1]
            read_and_validate_json(prediction_file, log)
        except Exception as e:
            log.error(e)
            traceback.print_exc()
            sys.exit(255)

        if log.error_count > 0:
            sys.exit(255)
        else:
            sys.exit(0)


if __name__ == "__main__":
    main()
