import csv
import datetime
import logging
from pathlib import Path
from types import SimpleNamespace
import argparse


from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.core.files import File
from evalbase.models import Organization, Submission, SubmitFormField, SubmitMeta, Task, SubmitForm

class Command(BaseCommand):
    help = 'Import RAGTIME dry run runs, which came in through a Google form'

    def add_arguments(self, parser):
        parser.formatter_class = argparse.ArgumentDefaultsHelpFormatter
        parser.add_argument('-r', '--runfile-dir',
                            help='Location of run files, should contain "retrieval" and "generation" directories',
                            type=Path,
                            default='/retrieval/evaluations/trec/trec34/ragtime/results/dry-run')
        parser.add_argument('spreadsheet',
                            help='Google spreadsheet for submissions')
        parser.add_argument('mapping',
                            help='CSV file mapping run names to filenames')


    def create_run(self, options, info_dict, filename):
        dryrun_task = Task.objects.get(shortname='trec2025-ragtime-dryrun')
        submission_form = SubmitForm.objects.get(task=dryrun_task)

        task_runs_location = {
            'Retrieval only': options.runfile_dir / 'retrieval',
            'English retrieval and generation': options.runfile_dir / 'generation',
            'Multilingual retrieval and generation': options.runfile_dir / 'generation',    
        }

        meta_fields = {
            'Task': 'ragtime-task',
            'Document Collection': 'ragtime-docs',
            'Machine Translation of Documents': 'ragtime-mt',
            'Write a short description of your retrieval process': 'std-description',
            'Write a short description of your generation process': 'ragtime-gen-desc',
            'Which LLM(s) where used by your system?': 'ragtime-llm',
            'Assessing priority': 'std-priority',
            'Open repository link': 'std-repo'
        }

        try:
            org = Organization.objects.get(shortname=info_dict['Group'])
        except ObjectDoesNotExist:
            self.log.warning(f'Org {info_dict["Group"]} does not exist')
            return None
        except MultipleObjectsReturned:
            orgs = Organization.objects.filter(shortname=info_dict['Group'])
            self.log.warning(f'Multiple orgs called {info_dict["Group"]} exist: {orgs}')
            return None

        try:
            user = User.objects.get(email=info_dict['Email Address'])
        except ObjectDoesNotExist:
            self.log.warning(f'User {info_dict["Email Address"]} does not exist')
            return None
        except MultipleObjectsReturned:
            users = User.objects.filter(shortname=info_dict['Email Address'])
            self.log.warning(f'Multiple users with email {info_dict["Email Address"]} exist: {users}')
            return None

        submit_date, _ = info_dict['Timestamp'].split()
        month, day, year = [int(foo) for foo in submit_date.split('/')]
        submit_stamp = datetime.date(year, month, day)

        runtype = task_runs_location[info_dict['Task']]
        if runtype.name == 'retrieval':
            filename = f'{filename}/{filename}'
        with open(task_runs_location[info_dict['Task']] / filename, 'rb') as fp:
            runfile = fp.read()

        run = Submission(
            runtag=info_dict['Run Name'],
            task=dryrun_task,
            org=org,
            submitted_by=user,
            date=submit_stamp,
            file=ContentFile(runfile, name=info_dict['Run Name']),
            is_validated=Submission.ValidationState.SUCCESS,
            has_evaluation=False,
            check_output=''
        )
        run.save()
        self.stdout.write(f'Created run {run.runtag}')

        for field, key in meta_fields.items():
            meta_field = SubmitFormField.objects.get(submit_form=submission_form, meta_key=key)
            sm = SubmitMeta(
                submission=run,
                form_field=meta_field,
                key=key,
                value=info_dict[field]
            )
            sm.save()
            self.stdout.write(f'    {key}: {info_dict[field]}')
    

    def handle(self, *args, **options):
        options = SimpleNamespace(**options)

        logging.basicConfig(level=logging.WARNING, 
                            format='%(levelname)s: %(message)s',
                            stream=self.stderr)
        self.log = logging.getLogger(__name__)

        if not options.runfile_dir.exists():
            raise CommandError(f'Runfile path {options.runfile_dir} does not exist')

        filenames = {}
        with open(options.mapping, 'r') as mapping_fp:
            reader = csv.DictReader(mapping_fp)
            for row in reader:
                if row['file'] == 'DROP':
                    continue
                filenames[row['Run Name']] = row['file']

        # There can be duplicate entries in the spreadsheet.  Take only the latest entry for a given run name
        runrows = {}

        with open(options.spreadsheet, 'r') as spreadsheet_fp:
            reader = csv.DictReader(spreadsheet_fp)
            for row in reader:
                if row['Run Name'] not in filenames:
                    continue
                runrows[row['Run Name']] = row

        for row in runrows.values():
            self.create_run(options, row, filenames[row['Run Name']])