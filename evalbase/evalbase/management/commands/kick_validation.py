from django.core.management.base import BaseCommand, CommandError
from evalbase.models import Submission, Task
from evalbase.views import run_check_script

class Command(BaseCommand):
    help = 'Kick validation for any submissions waiting for validation in the specified task'

    def add_arguments(self, parser):
        parser.add_argument('task')

    def handle(self, *args, **options):
        task = Task.objects.get(shortname=options['task'])
        if not task:
            raise CommandError(f'Task {options["task"]} not found.')

        run_one = False
        if task.checker_file and task.checker_file != 'NONE':
            for sub in Submission.objects.filter(task=task):
                if sub.is_validated == Submission.ValidationState.WAITING:
                    checktask = run_check_script(sub, task.checker_file)
                    print('Running', task.checker_file, 'for submission',
                          sub, '(', checktask, ')')
                    run_one = True
        if not run_one:
            print('No submissions to check')
