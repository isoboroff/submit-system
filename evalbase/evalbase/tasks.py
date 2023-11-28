import subprocess
from pathlib import Path

from huey import crontab
from huey.contrib.djhuey import task, db_task, on_commit_task

from .models import *
from django.conf import settings

SUBM_ROOT = Path(settings.MEDIA_ROOT)

@task()
def run_check_script(submission, script, *args):
    script_path = Path(settings.CHECK_SCRIPT_PATH) / script
    if not script_path.exists():
        raise FileNotFoundError(script_path)

    subm_dir = SUBM_ROOT / Path(submission.file.name).parent
    if not subm_dir.exists():
        raise FileNotFoundError(subm_dir)

    subm_path = SUBM_ROOT / submission.file.name
    if not subm_path.exists():
        raise FileNotFoundError(subm_path)

    proc = subprocess.run([script_path, *args, submission.file.name],
                          cwd=subm_dir,
                          capture_output=True,
                          text=True)

    submission.check_output = proc.stdout + '\n' + proc.stderr
    submission.is_validated = (proc.returncode == 0)
    submission.save()
