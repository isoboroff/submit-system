from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from evalbase.models import SubmitMeta

class Command(BaseCommand):
    help = 'Print out all form meta-keys in the database.'

    def handle(self, *args, **options):
        fields = (SubmitMeta.objects
                  .values('key')
                  .annotate(c=Count('key'))
                  .order_by('-c'))
        for f in fields:
            print(f['key'])
