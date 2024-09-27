import json
from pathlib import Path
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from evalbase.models import Task, Submission, Evaluation

class Command(BaseCommand):
    help = 'Import evaluation outputs for a task.'

    def add_arguments(self, parser):
        parser.add_argument('task',
                            help='Evals are for this task (\'list\' to list them)')

        parser.add_argument('eval',
                            help='Evaluation name',
                            default='trec_eval')

        parser.add_argument('-c', '--conf',
                            help='Conference shortname',
                            default='trec-2024')

        parser.add_argument('-d', '--directory',
                            help='Directory containing eval files',
                            type=Path,
                            default=Path('.'))

        parser.add_argument('-f', '--force',
                            help='Overwrite existing evals',
                            action='store_true')

    def handle(self, *args, **options):
        if options['task'] == 'list':
            tasks = (Task.objects
                     .filter(track__conference=option['conf']))
            for t in tasks:
                print(t.shortname, t.longname)

        else:
            task = Task.objects.get(shortname=options['task'])
            if not task:
                raise CommandError(f'Task {options["task"]} not found')

            eval = options['eval']

            for run in Submission.objects.filter(task=task):
                evalpath = options['directory'] / f'{run.runtag}.{eval}'
                if not evalpath.exists():
                    evaldir = options['directory'] / run.runtag
                    if not (evaldir.exists() and evaldir.is_dir()):
                        raise CommandError(f'Can\'t find {eval} eval for run {run.runtag} here or in directory {evaldir}')
                    evalpath = evaldir / f'{run.runtag}.{eval}'
                    if not evalpath.exists():
                        raise CommandError(f'Can\'t find {eval} eval for run {run.runtag} in directory {evaldir}')

                try:
                    old_eval = Evaluation.objects.get(submission=run, name=eval)
                    if old_eval:
                        if options['force']:
                            old_eval.delete()
                        else:
                            raise CommandError(f'Found existing eval.  To overwrite, use -f')
                except Evaluation.DoesNotExist:
                    pass

                new_eval = Evaluation()
                new_eval.name = eval
                new_eval.submission = run
                with evalpath.open(mode='r') as fp:
                    new_eval.filename = File(fp, name=evalpath.name)
                    new_eval.save()

                print(f'Evaluation {eval} for {run.runtag} imported.')
