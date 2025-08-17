import re
import shutil
from pathlib import Path

from django.db import models
from django.conf import settings
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.urls import reverse, reverse_lazy
from django.db.models.functions import Lower
from django.core.validators import MinValueValidator, MaxValueValidator

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='userprofile',
    )
    street_address = models.CharField(
        max_length=150)
    city_state = models.CharField(
        max_length=150)
    postal_code = models.CharField(
        max_length=10)
    country = models.CharField(
        max_length=50)
    unique_id = models.CharField(
        # This ID comes from login.gov
        # If it's blank we record the one that comes with the login
        # otherwise we check that it matches
        blank=True
    )
    created_at = models.DateField(
        auto_now_add=True)

    added_to_slack = models.BooleanField(
        default=False)

    def __str__(self):
        return self.user.username

    def get_absolute_url(self):
        return reverse('profile')

class Conference(models.Model):
    """A Conference is an evaluation conference instance like TREC 2020."""
    shortname = models.CharField(
        max_length=15)
    longname = models.CharField(
        max_length=150)
    year = models.IntegerField(validators=[
        MinValueValidator(2024),
        MaxValueValidator(2032)
    ])
    open_signup = models.BooleanField()
    tech_contact = models.EmailField()
    admin_contact = models.EmailField()
    complete = models.BooleanField()
    agreements = models.ManyToManyField('Agreement', blank=True)
    results_root = models.CharField(
        max_length=15,
        default='{0}/{1}'.format(shortname, 'runs'))
    event_phase = models.BooleanField()

    def __str__(self):
        return self.shortname

class Organization(models.Model):
    """An Organization is a group that has registered to participate in a Conference."""

    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='org_owner_of')
    shortname = models.CharField(
        max_length=15,
        verbose_name='Short name',
        help_text='A short (max 15 chars) acronym or abbreviation.')
    longname = models.CharField(
        max_length=50,
        verbose_name='Long name',
        help_text='The full name of your organization.')
    contact_person = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='org_contact_for')
    passphrase = models.CharField(
        max_length=36,
        editable=False)
    members = models.ManyToManyField(
        User,
        related_name='member_of')
    conference = models.ManyToManyField(
        to='Conference',
        related_name='participants')
    track_interest = models.ManyToManyField(
        to='Track',
        #limit_choices_to=Q(conference=conference)
    )

    def __str__(self):
        return self.shortname

class Agreement(models.Model):
    """An Agreement is something somebody has to sign.  Usually for Conferences."""
    name = models.CharField(max_length=25)
    longname = models.CharField(max_length=150)
    template = models.CharField(max_length=30)

    def __str__(self):
        return self.name

class Signature(models.Model):
    """Signature is a signature on an agreement."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    sigtext = models.CharField(max_length=50)
    agreement = models.ForeignKey(Agreement, on_delete=models.CASCADE)

class Track(models.Model):
    '''A track is one or more tasks on a specific problem.'''
    shortname = models.CharField(
        max_length=15)
    longname = models.CharField(
        max_length=50)
    conference = models.ForeignKey(
        Conference,
        on_delete=models.CASCADE)
    coordinators = models.ManyToManyField(User, blank=True)
    url = models.URLField(blank=True)

    def __str__(self):
        return self.longname

class Task(models.Model):
    """A Task is like a TREC track, a thing in a Conference that people submit things to."""
    shortname = models.CharField(
        max_length=25)
    longname = models.CharField(
        max_length=50)
    track = models.ForeignKey(Track, on_delete=models.CASCADE, null=True)
    required = models.BooleanField()
    task_open = models.BooleanField()
    deadline = models.DateField(null=True, blank=True)
    checker_file = models.CharField(max_length=500, default="NONE")

    def __str__(self):
        # return "/".join([self.conference.shortname, self.shortname])
        return f'{self.track.conference.shortname}/{self.track.shortname}/{self.shortname}: {self.longname}'

class SubmitForm(models.Model):
    """A SubmitForm is a form for submitting something to a Task."""
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='submit_form'
    )
    header_template = models.CharField(
        max_length=30,
        blank=True)
    testing = models.BooleanField(default=False)

    def __str__(self):
        return "/".join([self.task.track.conference.shortname, self.task.track.shortname, self.task.shortname])
    
    def copy(self):
        '''Copy a form and its fields.  The new fields are saved to the database.
        Don't forget to save the new model instance.'''
        new_form = SubmitForm(task=self.task, header_template=self.header_template, testing=self.testing)
        new_form.save()
        for field in self.submitformfield_set.all():
            new_field = field.copy()
            new_field.submit_form = new_form
            new_field.save()
        return new_form

class SubmitFormField(models.Model):
    """A SubmitFormField is a field in a SubmitForm.
    These forms are table-driven to make it easy to write submission forms."""
    class QuestionType(models.IntegerChoices):
        TEXT = 1
        NUMBER = 2
        RADIO = 3
        CHECKBOX = 4
        EMAIL = 5
        COMMENT = 6
        RUNTAG = 7
        YESNO = 8

    submit_form = models.ForeignKey(
        SubmitForm,
        on_delete=models.CASCADE)
    question = models.CharField(
        max_length=1000)
    choices = models.CharField(
        max_length=1000,
        blank=True)
    meta_key = models.CharField(
        max_length=25)
    sequence = models.IntegerField()
    question_type = models.IntegerField(
        choices=QuestionType.choices,
        default=QuestionType.TEXT)
    required = models.BooleanField(
        default=True)
    help_text = models.CharField(
        max_length=1000,
        blank=True,
        default='')

    def __str__(self):
        return self.meta_key
    
    def copy(self):
        '''Copy a field.  Don't forget to save() it.'''
        new_sff = SubmitFormField(question=self.question,
                                  choices=self.choices,
                                  meta_key=self.meta_key,
                                  sequence=self.sequence,
                                  question_type=self.question_type,
                                  required=self.required,
                                  help_text=self.help_text)
        return new_sff

    class Meta:
        ordering = ['sequence']

def get_submission_path(submission, filename):
    return '{0}/{1}/results/{2}/{3}'.format(
        submission.task.track.conference.results_root,
        submission.task.shortname,
        submission.runtag,
        submission.runtag)

class Submission(models.Model):
    """A Submission is something that got submitted to a Task via a SubmitForm."""

    class ValidationState(models.TextChoices):
        WAITING = 'W', 'waiting for validation'
        FAIL = 'F', 'validation failed'
        SUCCESS = 'S', 'validation succeeded'

    runtag = models.CharField(max_length=150)
    task = models.ForeignKey(
        Task,
        on_delete=models.PROTECT)
    org = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT)
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT)
    date = models.DateField(
        auto_now_add=True)
    file = models.FileField(
        upload_to=get_submission_path,
        max_length=500)
    is_validated = models.CharField(
        max_length=1,
        choices=ValidationState.choices,
        default=ValidationState.WAITING)
    has_evaluation = models.BooleanField()
    check_output = models.TextField(blank=True)

    def save(self, **kwargs):
        if self._state.adding:
            if re.search(r'[^\d\w_\.-]', self.runtag):
                raise ValidationError(_('Runtags may only have letters, numbers, hyphens, periods (not first), or underscores'))
            
            if self.runtag.startswith('.'):
                raise ValidationError(_('Runtags may not start with a period'))
            
            if len(self.runtag) > 20:
                raise ValidationError(_('Runtags cannot be more than 20 characters long'))
            
            if Submission.objects.filter(task__track__conference=self.task.track.conference, runtag=self.runtag).exists():
                raise ValidationError(_('Runtags must be unique, an another submission to %(conf)s already has runtag %(runtag)s',
                                        params={'conf': self.task.track.conference.longname,
                                                'runtag': self.runtag}))
        super().save(**kwargs)

    def delete(self, *args, **kwargs):
        run_dir =  (Path(settings.MEDIA_ROOT) / self.file.name).parent
        shutil.rmtree(run_dir, ignore_errors=True)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f'{self.task.track.conference.shortname}/{self.runtag}'


class SubmitMeta(models.Model):
    """SubmitMetas are values for SubmitFormFields aside from task, org, submitter, file and date."""
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE)
    form_field = models.ForeignKey(
        SubmitFormField,
        on_delete=models.PROTECT)
    key = models.CharField(max_length=25)
    value = models.CharField(max_length=2500)

    def __str__(self):
        return f'{self.submission.runtag} {self.key}:{self.value}'


def get_eval_path(evaluation, filename):
    run_path = get_submission_path(evaluation.submission, 'foo')
    eval_path = Path(run_path).with_name(f'{evaluation.submission.runtag}.{evaluation.name}')
    return eval_path

def get_stats_path(statsfile, filename):
    return '{0}/{1}/tables/{2}'.format(
        statsfile.task.track.conference.results_root,
        statsfile.task.shortname,
        statsfile.name
    )

class Evaluation(models.Model):
    """Evaluations are output files from scoring programs like trec_eval.  These are how results are delivered to participants.  They are kept in the run results directory so you can use get_submission_path() to know where they go."""
    submission = models.ForeignKey(
        Submission,
        on_delete=models.PROTECT)
    name = models.CharField(max_length=20)
    filename = models.FileField(
        upload_to=get_eval_path,
        max_length=250)
    date = models.DateField(auto_now=True)

    def __str__(self):
        return f'{self.submission.runtag}:{self.name}'


class StatsFile(models.Model):
    '''StatsFiles are statistics, like min/med/max tables, that go with a particular task evaluation.'''
    name = models.CharField(max_length=40)
    task = models.ForeignKey(
        Task,
        on_delete=models.PROTECT)
    filename = models.FileField(
        upload_to=get_stats_path,
        max_length=250)
    date = models.DateField(auto_now=True)

    def __str__(self):
        return f'{self.task.shortname}:{self.name}'


class Appendix(models.Model):
    '''Information for displaying an appendix page'''
    task = models.ForeignKey(
        Task,
        on_delete=models.PROTECT)
    name = models.CharField(max_length=40)
    # Fields in the evaluation file (assumed to be tidy and columnar)
    measure_name_field = models.IntegerField()
    topic_field = models.IntegerField()
    score_field = models.IntegerField()
    # Measures to display, or "all"
    measures = models.JSONField(max_length=1024)
    # topic number that represents the average over topics ("all")
    average_topic = models.CharField(max_length=20, blank=True, null=True)
    sort_column = models.CharField(max_length=20, blank=True, null=True)
    # These allow subsetting the list of eval outputs to use
    queryset_field = models.CharField(max_length=25, blank=True, null=True)
    queryset_qtype = models.CharField(max_length=25, blank=True, null=True)
    queryset_target = models.CharField(max_length=25, blank=True, null=True)
