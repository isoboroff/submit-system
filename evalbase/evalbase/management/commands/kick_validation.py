from django.core.management.base import BaseCommand, CommandError
from evalbase.models import Submission, Task
from evalbase.views import run_check_script

class Command(BaseCommand):
    help = 'Kick validation for any submissions waiting for validation in the specified task'

    def add_arguments(self, parser):
        parser.add_argument('-f', '--force',
                            action='store_true',
                            help='Force validation to run on all submissions')
        parser.add_argument('-r', '--run',
                            help='Run validation for a specific run (default is all runs)',
                            default=None)
        parser.add_argument('task',
                            help='Run validation over all runs in a task')

    def handle(self, *args, **options):
        task = Task.objects.get(shortname=options['task'])
        if not task:
            raise CommandError(f'Task {options["task"]} not found.')

        run_one = False
        if task.checker_file and task.checker_file != 'NONE':
            for sub in Submission.objects.filter(task=task):
                if (options['force'] or
                    sub.is_validated == Submission.ValidationState.WAITING or
                    (options['run'] and sub.runtag == options['run'])):
                    checktask = run_check_script(sub, task.checker_file)
                    print('Running', task.checker_file, 'for submission',
                            sub, '(', checktask, ')')
                    run_one = True
                elif not options['run'] or options['force']:
                    print(f'Skipping {sub}, {sub.is_validated}')
        else:
            print('Task has no checker to run')

        if not run_one:
            print('No submissions to check')
