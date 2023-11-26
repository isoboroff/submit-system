from django.db import models
from django.conf import settings
from django.db.models import Q
from django.contrib.auth.models import User
from django.urls import reverse, reverse_lazy

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
    created_at = models.DateField(
        auto_now_add=True)

    def __str__(self):
        return self.user.username

    def get_absolute_url(self):
        return reverse('profile')

class Conference(models.Model):
    """A Conference is an evaluation conference instance like TREC 2020."""
    shortname = models.CharField(
        max_length=15)
    longname = models.CharField(
        max_length=50)
    open_signup = models.BooleanField()
    tech_contact = models.EmailField()
    admin_contact = models.EmailField()
    complete = models.BooleanField()
    agreements = models.ManyToManyField('Agreement', blank=True)
    results_root = models.CharField(
        max_length=15,
        default='{0}/{1}'.format(shortname, 'runs'))

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
        max_length=20,
        editable=False)
    members = models.ManyToManyField(
        User,
        related_name='member_of')
    conference = models.ForeignKey(
        Conference,
        on_delete=models.PROTECT,
        related_name='participants')
    task_interest = models.ManyToManyField(
        to='Task',
        #limit_choices_to=Q(conference=conference)
    )

    def __str__(self):
        return self.shortname

    def get_absolute_url(self):
        return reverse('org-detail', args=[str(self.shortname)])

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


class Task(models.Model):
    """A Task is like a TREC track, a thing in a Conference that people submit things to."""
    shortname = models.CharField(
        max_length=15)
    longname = models.CharField(
        max_length=50)
    conference = models.ForeignKey(
        Conference,
        on_delete=models.CASCADE)
    required = models.BooleanField()
    task_open = models.BooleanField()
    checker_file = models.CharField(max_length=30, default="NONE")

    def __str__(self):
        # return "/".join([self.conference.shortname, self.shortname])
        return self.longname

class SubmitForm(models.Model):
    """A SubmitForm is a form for submitting something to a Task."""
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE)
    header_template = models.CharField(
        max_length=30,
        blank=True)

    def __str__(self):
        return "/".join([self.task.conference.shortname, self.task.shortname])

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
        max_length=100)
    choices = models.CharField(
        max_length=100,
        blank=True)
    meta_key = models.CharField(
        max_length=15)
    sequence = models.IntegerField()
    question_type = models.IntegerField(
        choices=QuestionType.choices,
        default=QuestionType.TEXT)
    def __str__(self):
        return self.meta_key

    class Meta:
        ordering = ['sequence']

def get_submission_path(submission, filename):
    return 'submissions/{0}/{1}/results/{2}/{3}'.format(submission.task.conference.results_root,
                                                        submission.task.shortname,
                                                        submission.runtag,
                                                        submission.file.name)
class Submission(models.Model):
    """A Submission is something that got submitted to a Task via a SubmitForm."""
    runtag = models.CharField(max_length=15)
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
        upload_to=get_submission_path)
    is_validated = models.BooleanField()
    has_evaluation = models.BooleanField()

    def __str__(self):
        return f'{self.task.conference.shortname}/{self.runtag}'


class SubmitMeta(models.Model):
    """SubmitMetas are values for SubmitFormFields aside from task, org, submitter, file and date."""
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE)
    form_field = models.ForeignKey(
        SubmitFormField,
        on_delete=models.PROTECT)
    key = models.CharField(max_length=15)
    value = models.CharField(max_length=250)

    def __str__(self):
        return f'{self.submission.runtag} {self.key}:{self.value}'
