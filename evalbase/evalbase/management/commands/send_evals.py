from email.message import EmailMessage
import json
import os
from pathlib import Path
import smtplib
import sys
import textwrap
import magic
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from evalbase.models import Organization, Task, Submission, Evaluation

class Command(BaseCommand):
    help = 'Send evaluation results for a task to teams.'
    
    def add_arguments(self, parser):
        parser.add_argument('task',
                            help='Task to send evals for (\'list\' to list them)')  
        
        parser.add_argument('-c', '--conf',
                            help='Conference shortname',
                            default='trec-2024')
        
        parser.add_argument('--comments', 
                            help='Comments to add to the text part of the email',
                            default=None)
        
        parser.add_argument('--attach',
                            help='Attach an extra file to the email',
                            action='append')
        
        parser.add_argument('--send',
                            help='Actually send the emails instead of saving them to files',
                            action='store_true')       
    
    def handle(self, *args, **options):
        email_template = textwrap.dedent("""
        Subject: Evaluation Results for {track} {task}
    
        Hi {team_name},
    
        Please find attached the evaluation results for your submissions to the {track} {task}.
        """)

        if options['task'] == 'list':
            tasks = (Task.objects
                     .filter(track__conference__shortname=options['conf']))
            for t in tasks:
                print(t.shortname, t.longname)
                
        else:
            task = Task.objects.get(shortname=options['task'])
            if not task:
                raise CommandError(f'Task {options["task"]} not found')
            
            if options['comments']:
                comment_content = open(options['comments']).read()
                comment_content = textwrap.dedent(comment_content)
                email_template += f"\n\n{comment_content}"
            
            for org_id in Submission.objects.filter(task=task).values_list('org', flat=True).distinct():
                org = Organization.objects.get(id=org_id)
                msg = EmailMessage()
                to_list = set()
                msg['Subject'] = f"Evaluation Results for {task.longname}"
                msg['From'] = task.track.conference.tech_contact
                to_list.add(org.owner.email)
                to_list.add(org.contact_person.email)
                msg.set_content(email_template.format(task=task.longname, track=task.track.longname, team_name=org.longname))
                
                for run in Submission.objects.filter(task=task, org=org):  
                    to_list.add(run.submitted_by.email)
                    evals = Evaluation.objects.filter(submission=run)
                    for eval in evals:
                        eval_name = Path(eval.filename.name).name
                        with eval.filename.open('rb') as f:
                            msg.add_attachment(f.read(), maintype='application', subtype='octet-stream', filename=eval_name)
                                
                msg['To'] = ', '.join(to_list)

                if options['attach']:
                    for attachment in options['attach']:
                        (mime_main, mime_subtype) = magic.from_file(attachment, mime=True).split('/')
                        with open(attachment, 'rb') as f:
                            content = f.read()
                            msg.add_attachment(content, maintype=mime_main, subtype=mime_subtype, filename=os.path.basename(attachment))
                            
                if options['send']:
                    # Send the email
                    with smtplib.SMTP('localhost') as s:
                        s.send_message(msg)
                else:
                    # Save the email to a file
                    filename = f"{org.shortname}_{task.shortname}_evals.eml"
                    with open(filename, 'wb') as f:
                        f.write(msg.as_bytes())
