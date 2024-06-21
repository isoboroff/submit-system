import subprocess
from pathlib import Path

from huey import crontab
from huey.contrib.djhuey import task, db_task, on_commit_task

from .models import *
from django.conf import settings

SUBM_ROOT = Path(settings.MEDIA_ROOT)

@task()
def run_check_script(submission, script, *args):
    argsplit = script.split()
    script = argsplit[0]
    args = [*args, *argsplit[1:]]

    script_path = Path(settings.CHECK_SCRIPT_PATH) / script
    if not script_path.exists():
        raise FileNotFoundError(script_path)

    subm_file = SUBM_ROOT / submission.file.name

    subm_dir = SUBM_ROOT / subm_file.parent
    if not subm_dir.exists():
        raise FileNotFoundError(subm_dir)

    subm_path = SUBM_ROOT / submission.file.name
    if not subm_file.exists():
        raise FileNotFoundError(subm_file)

    proc = subprocess.run([script_path, *args, subm_file.name],
                          cwd=subm_dir,
                          capture_output=True,
                          text=True)

    errlog = 'no errlog'
    errlog_file = subm_dir / (subm_file.name + '.errlog')
    if errlog_file.exists():
        with open(errlog_file, 'r') as errlog_fp:
            errlog = errlog_fp.read()
    else:
        raise FileNotFoundError(errlog_file)

    submission.check_output = errlog + '\n'
    if proc.returncode == 0:
        submission.is_validated = Submission.ValidationState.SUCCESS
    else:
        submission.is_validated = Submission.ValidationState.FAIL
    submission.save()
