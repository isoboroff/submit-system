from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from evalbase.models import UserProfile
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Note that the users in the given file have been added to Slack'

    def add_arguments(self, parser):
        parser.add_argument('emails', type=Path)

    def handle(self, *args, **options):
        with open(options['emails'], 'r') as emails_file:
            for line in emails_file:
                email = line.strip()

                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    print(f'No such user {email}, skipping')
                    continue

                try:
                    profile = UserProfile.objects.get(user=user)
                except UserProfile.DoesNotExist:
                    profile = UserProfile(user=user)

                print(f'Marking {user.username} ({email}) as added to slack')
                profile.added_to_slack = True
                profile.save()
