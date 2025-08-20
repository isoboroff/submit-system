#!/usr/bin/env python
import csv


def validate_csv_run_file(file_path):
    errors = []
    # Dictionary to track seen ranks for each query_ID
    query_ranks = {}

    # Read the file and store IDs in a set (faster lookup than list)
    with open("2025.testing.ids.txt", "r", encoding="utf-8-sig") as f:
        ids_in_file = {line.strip() for line in f}
       # print(ids_in_file)

    with open(file_path, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        row_number = 1
        for row in reader:
            # Check that there are exactly 4 fields
            if len(row) != 4:
                errors.append(f"Row {row_number}: Expected 4 fields, got {len(row)}")
                row_number += 1
                continue

            query_id_str, dummy, rank_str, answer = row

            # Check if my_id exists in the file
            if dummy.strip() not in ids_in_file:
                errors.append(f"{dummy} NOT found in testing video Ids.")

            # Validate query_ID: should be an integer >= 1
            try:
                query_id = int(query_id_str)
                if query_id < 1:
                    errors.append(f"Row {row_number}: query_ID must be >= 1, got {query_id_str}")
            except ValueError:
                errors.append(f"Row {row_number}: query_ID is not a valid integer: {query_id_str}")
                row_number += 1
                continue  # Skip further checks if query_ID is invalid

            # Validate rank: should be an integer between 1 and 10
            try:
                rank = int(rank_str)
                if rank < 1 or rank > 10:
                    errors.append(f"Row {row_number}: rank must be between 1 and 10, got {rank_str}")
            except ValueError:
                errors.append(f"Row {row_number}: rank is not a valid integer: {rank_str}")
                row_number += 1
                continue  # Skip duplicate check if rank is invalid

            # Validate answer: must be non-empty
            if not answer.strip():
                errors.append(f"Row {row_number}: answer field is empty")

            # Check for unique ranks per query_ID
            if query_id not in query_ranks:
                query_ranks[query_id] = set()
            if rank in query_ranks[query_id]:
                errors.append(f"Row {row_number}: Duplicate rank {rank} for query_ID {query_id}")
            else:
                query_ranks[query_id].add(rank)

            row_number += 1

    return errors

# Example usage:
if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python validator.py <csv_file_path>")
        sys.exit(1)

    

    file_path = sys.argv[1]
    validation_errors = validate_csv_run_file(file_path)

    if validation_errors:
        print("Validation errors found:")
        with open(file_path+'.errlog', 'w') as errFile:
            print('\n'.join(validation_errors),file=errFile)
        for error in validation_errors:
            print(" -", error)
        sys.exit(1)
    else:
        print("CSV run file is valid.")
        with open(file_path+'.errlog', 'w') as errFile:
            print('No error found\n',file=errFile)
        sys.exit(0)
