import json
from django.core.management.base import BaseCommand, CommandError
from evalbase.models import Task, Submission, SubmitMeta

valid_gloss = { 'W': 'waiting',
                'F': 'fail',
                'S': 'success'}

class Command(BaseCommand):
    help = 'Dump a report of submissions and their metadata for a task.'

    def add_arguments(self, parser):
        parser.add_argument('task')

    def handle(self, *args, **options):
        task = Task.objects.get(shortname=options['task'])
        if not task:
            raise CommandError(f'Task {options["task"]} not found.')

        fields = ['runtag', 'org', 'email', 'date', 'validated']

        with open(f'{task.shortname}.jl', 'w') as jsonfile:
            for run in task.submission_set.all():

                runrow = {'runtag': run.runtag,
                          'org': run.org.shortname,
                          'email': run.submitted_by.email,
                          'date': run.date.isoformat(),
                          'validated': valid_gloss[run.is_validated]
                          }
                for meta in run.submitmeta_set.all():
                    runrow[meta.key] = meta.value

                print(json.dumps(runrow), file=jsonfile)
