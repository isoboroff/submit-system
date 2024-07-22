#!/usr/bin/env python3

import json
import sys
import os


def read_json(data_path):
    #### reading the json file
    with open(data_path, "r") as rfile:
        data_items = json.load(rfile)
    return data_items

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
        print(f'ERROR {msg}', file=self.fp)
        self.error_count += 1
        assert self.error_count <= self.max_errors, 'Too many errors'

    def warn(self, msg):
        print(f'WARNING {msg}', file=self.fp)

    def say(self, msg):
        print(f'{msg}', file=self.fp)


def check_fields(data_path, question_size=52):
    #### check the json file contains the required fields
    data_items = read_json(data_path)
    if len(data_items) != question_size:
        log.error(
            f"submitted prediction json file doesn't have predictions for all {question_size} questions!"
        )

    for data_item in data_items:
        if "question_id" not in data_item:
            log.error(
                f"submitted prediction json file doesn't have required 'question_id' field for {data_item}!"
            )

        if data_item["question_id"] == "" or data_item["question_id"] == None:
            log.error(
                f"submitted prediction json file have empty 'question_id' field for {data_item}"
            )

        if "relevant_videos" not in data_item:
            log.error(
                f"submitted prediction json file doesn't have required 'relevant_videos' field for {data_item}!"
            )

        if (
            "relevant_videos" in data_item
            and type(data_item["relevant_videos"]) is not list
        ):
            log.error(
                f"submitted prediction json file doesn't have 'relevant_videos' list for {data_item}!"
            )

        if len(data_item["relevant_videos"]) == 0:
            log.error(
                f"submitted prediction json file have zero 'relevant_videos' for questiond id {data_item['question_id']}!"
            )

        for rel_vid_item in data_item["relevant_videos"]:
            if type(rel_vid_item) is not dict:
                log.error(
                    f"submitted prediction json file have following issue: the data type is not dictionary for one of the 'relevant_videos' related to questiond id {data_item['question_id']}!"
                )

            if "video_id" not in rel_vid_item:
                log.error(
                    f"submitted prediction json file doesn't have required 'video_id' field for questiond id {data_item['question_id']}!"
                )

            if rel_vid_item["video_id"] == "" or rel_vid_item["video_id"] == None:
                log.error("'video_id' field can not be empty")

            if "relevant_score" not in rel_vid_item:
                log.error(
                    f"submitted prediction json file doesn't have required 'relevant_score' field for questiond id {data_item['question_id']}!"
                )

            if (
                rel_vid_item["relevant_score"] == ""
                or rel_vid_item["relevant_score"] == None
            ):
                log.error(
                    f"'relevant_score' field can not be empty for for questiond id {data_item['question_id']}!"
                )


            if type(rel_vid_item["relevant_score"]) not in [float, int]:
                log.error(
                    f"'relevant_score' field must be int/float value for questiond id {data_item['question_id']}!"
                )

            if "answer_start_second" not in rel_vid_item:
                log.error(
                    f"submitted prediction json file doesn't have required 'answer_start_second' field for questiond id {data_item['question_id']} and relevant_video {rel_vid_item['video_id']}!"
                )

            if "answer_end_second" not in rel_vid_item:
                log.error(
                    f"submitted prediction json file doesn't have required 'answer_end_second' field for questiond id {data_item['question_id']} and relevant_video {rel_vid_item['video_id']}!"
                )

            if (
                rel_vid_item["answer_start_second"] == ""
                or rel_vid_item["answer_start_second"] == None
            ):
                log.error("'answer_start_second' field can not be empty")

            if (
                rel_vid_item["answer_end_second"] == ""
                or rel_vid_item["answer_end_second"] == None
            ):
                log.error("'answer_start_second' field can not be empty")

            if type(rel_vid_item["answer_start_second"]) not in [float, int] or type(
                rel_vid_item["answer_end_second"]
            ) not in [float, int]:
                log.error(
                    "'answer_start_second'/'answer_end_second' field must be int/float value!"
                )


def check_file_name_and_type(submission_file):
    ### check the file name
    # if os.path.basename(submission_file) != "predictions.json":
    #    log.error("submission json file name is invalid!")
    try:
        with open(submission_file, 'r') as fp:
            testing = json.load(fp)
    except ValueError:
        log.error('File is not JSON')
    return False


def check_non_ascii_characters(submission_file_path):
    ### check for non_asciii characters
    data_item_list = read_json(submission_file_path)
    for data_item in data_item_list:
        for key, value in data_item.items():
            if not str(value).isascii():
                log.error(f"Non-ascii characters in the file: {value}")
    return True


def read_and_validate_json(submission_file_path):
    ##### to check the validatity of the submission file

    # check_file_name_and_type(submission_file_path). #### relaxing the need of predictions.json submission file name
    check_fields(submission_file_path)
    check_non_ascii_characters(submission_file_path)

    if log.error_count > 0:
        log.error("Submission file has errors, please fix and resubmit")
        sys.exit(255)
    else:
        log.say("Submission file validated successfully!!")
        sys.exit(0)


def main():
    prediction_file = sys.argv[1]
    read_and_validate_json(prediction_file)


if __name__ == "__main__":
    with Errlog(sys.argv[1]) as log:
        main()
