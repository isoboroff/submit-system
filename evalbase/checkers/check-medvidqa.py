#!/usr/bin/env python3

import json
import sys
import os

def read_json(data_path):
	#### reading the json file
	with open(data_path, 'r') as rfile:
		data_items = json.load(rfile)
	return data_items


def check_fields(data_path, question_size=52):
	#### check the json file contains the required fields
	data_items = read_json(data_path)
	if len(data_items)!=question_size:
		print(f"submitted prediction json file doesn't have predictions for all {question_size} questions!")
		sys.exit(0)

	for data_item in data_items:
		if 'question_id' not in data_item:
			print(f"submitted prediction json file doesn't have required 'question_id' field for {data_item}!")
			sys.exit(0)

		if data_item['question_id']=='' or data_item['question_id']==None:
			print(f"submitted prediction json file have empty 'question_id' field for {data_item}")
			sys.exit(0)

		if 'relevant_videos' not in data_item:
			print(f"submitted prediction json file doesn't have required 'relevant_videos' field for {data_item}!")
			sys.exit(0)

		if 'relevant_videos' in data_item and type(data_item['relevant_videos']) is not list:
			print(f"submitted prediction json file doesn't have 'relevant_videos' list for {data_item}!")
			sys.exit(0)

		if len(data_item['relevant_videos'])==0:
			print(f"submitted prediction json file have zero 'relevant_videos' for questiond id {data_item['question_id']}!")
			sys.exit(0)
		
		for rel_vid_item in data_item['relevant_videos']:
			if type(rel_vid_item) is not dict:
				print(f"submitted prediction json file have following issue: the data type is not dictionary for one of the 'relevant_videos' related to questiond id {data_item['question_id']}!")
				sys.exit(0)

			if 'video_id' not in rel_vid_item:
				print(f"submitted prediction json file doesn't have required 'video_id' field for questiond id {data_item['question_id']}!")
				sys.exit(0)
			
			if rel_vid_item['video_id']=='' or rel_vid_item['video_id']==None:
				print("'video_id' field can not be empty")
				sys.exit(0)


			if 'relevant_score' not in rel_vid_item:
				print(f"submitted prediction json file doesn't have required 'relevant_score' field for questiond id {data_item['question_id']}!")
				sys.exit(0)
			
			if rel_vid_item['relevant_score']=='' or rel_vid_item['relevant_score']==None:
				print(f"'relevant_score' field can not be empty for for questiond id {data_item['question_id']}!")

				sys.exit(0)

			if type(rel_vid_item['relevant_score']) not in [float, int] :
				print(f"'relevant_score' field must be int/float value for questiond id {data_item['question_id']}!")
				sys.exit(0)


			if 'answer_start_second' not in rel_vid_item:
				print(f"submitted prediction json file doesn't have required 'answer_start_second' field for questiond id {data_item['question_id']} and relevant_video {rel_vid_item['video_id']}!")
				sys.exit(0)

			if 'answer_end_second' not in rel_vid_item:
				print(f"submitted prediction json file doesn't have required 'answer_end_second' field for questiond id {data_item['question_id']} and relevant_video {rel_vid_item['video_id']}!")
				sys.exit(0)
		
		
			if rel_vid_item['answer_start_second']=='' or rel_vid_item['answer_start_second']==None:
				print("'answer_start_second' field can not be empty")
				sys.exit(0)

			if rel_vid_item['answer_end_second']=='' or rel_vid_item['answer_end_second']==None:
				print("'answer_start_second' field can not be empty")
				sys.exit(0)

			if type(rel_vid_item['answer_start_second']) not in [float, int] or type(rel_vid_item['answer_end_second']) not in [float, int]:
				print("'answer_start_second'/'answer_end_second' field must be int/float value!")
				sys.exit(0)




def check_file_name_and_type(submission_file):
	### check the file name
	if os.path.basename(submission_file)!="predictions.json":
		print("submission json file name is invalid!")
		sys.exit(0)

def check_non_ascii_characters(submission_file_path):
	### check for non_asciii characters
	data_item_list = read_json(submission_file_path)
	for data_item in data_item_list:
		for key, value in data_item.items():
			if not str(value).isascii():
				print(f"Non-ascii characters in the file: {value}")
				sys.exit(0)
	return True

def read_and_validate_json(submission_file_path):
	##### to check the validatity of the submission file


	# check_file_name_and_type(submission_file_path). #### relaxing the need of predictions.json submission file name
	check_fields(submission_file_path)
	check_non_ascii_characters(submission_file_path)
	
	print("Submission file validated successfully!!")



def main():
	prediction_file = sys.argv[1]
	read_and_validate_json(prediction_file)

if __name__ == '__main__':
	main()