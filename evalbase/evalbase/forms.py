import operator
import re

from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MaxLengthValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from .models import *

class DebuggingLoginForm(forms.Form):
    login_as = forms.CharField(max_length=20)

class SignupForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name']

    def clean(self):
        self.cleaned_data['password1'] = 'not-a-very-good-password'
        self.cleaned_data['password2'] = 'not-a-very-good-password'
        pass

    def _post_clean(self):
        pass

    def clean_email(self):
        data = self.cleaned_data['email']
        print(f'clean_email data is {data}')
        if User.objects.filter(email=data).exists():
            raise ValidationError('An account with this email address already exists.')
        return data

    def clean_username(self):
        data = self.cleaned_data['username']
        if User.objects.filter(username=data).exists():
            raise ValidationError('An account with this username already exists.')
        return data


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['street_address', 'city_state', 'country', 'postal_code']


class MembersEditForm(forms.Form):
    # Returning the form class in this somewhat clever way lets me set
    # the choices to the current members of the organization.
    def get_form_class(context):
        fields = {}
        member_choices = [(m.id, f'{m.first_name} {m.last_name} ({m.email})')
                          for m in context['members']]
        fields["users"] = forms.MultipleChoiceField(
            label="Select user(s) to remove",
            choices=member_choices,
            required=False,
            widget=forms.CheckboxSelectMultiple
        )

        track_choices = [(track.shortname, track.longname)
                        for track in context['all_tracks']]
        track_choices = sorted(track_choices, key=operator.itemgetter(1))
        fields["track_interest"] = forms.MultipleChoiceField(
            label="Select tracks",
            choices=track_choices,
            widget=forms.CheckboxSelectMultiple,
            required=False,
            initial=context['tracks'])

        return type('MembersEditForm', (forms.Form,), fields)


class AgreementForm(forms.Form):
    sigtext = forms.CharField(label='Signature',
                              help_text='Please type your full name',
                              max_length=50)
    
class RuntagField(forms.Field):
    default_validators = [
        RegexValidator(regex=r'[^\w\d_\.-]',
                       inverse_match=True,
                       message='Runtags may only contain letters, numbers, underscores, periods, and hyphens'),
        RegexValidator(regex=r'^\.',
                       inverse_match=True,
                       message='Runtags may not have a period as the first character'),
        MaxLengthValidator(20,
                           message='Runtags can be at most 20 characters long'),
    ]

    def __init__(self, existing_runtags, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.existing_runtags = existing_runtags

    def to_python(self, value):
        return super().to_python(value)
    
    def validate(self, value):
        super().validate(value)
        if value in self.existing_runtags:
            raise ValidationError(
                _('Another submission with the runtag %(runtag)s has already been submitted'),
                params={'runtag': value}
            )
        if value == 'submit' or value == 'list':
            raise ValidationError(
                _('Submissions may not be named "submit" or "list"'))

class SubmitFormForm(forms.Form):
    def get_form_class(context):
        fields = {}
        # Set up standard fields
        fields['conf'] = forms.CharField(
            widget=forms.HiddenInput(),
            initial=context['conf'].shortname)
        fields['task'] = forms.CharField(
            widget=forms.HiddenInput(),
            initial=context['task'].shortname)
        fields['user'] = forms.CharField(
            label='User name',
            widget=forms.TextInput(
                attrs={'value': context['user'].username,
                       'readonly': 'readonly',
                       'class': 'form-control-plaintext'}))
        fields['email'] = forms.EmailField(
            label='Email',
            widget=forms.EmailInput(
                attrs={'value': context['user'].email,
                       'readonly': 'readonly',
                       'class': 'form-control-plaintext'}))
        org_choices = list(map(lambda x: (x.shortname, x.longname), context['orgs']))
        fields['org'] = forms.ChoiceField(label='Organization', choices=org_choices)

        if context['mode'] == 'submit':
            fields['runfile'] = forms.FileField(label='Submission file')
            if context['track'].shortname != 'papers':
                existing_runtags = set(Submission.objects
                                    .filter(task__track__conference=context['conf'])
                                    .values_list('runtag', flat=True))
                fields['runtag'] = RuntagField(
                    label='Runtag: a short identifier for the run (letters, numbers, underscores, periods (not first character) or hyphens only, 20 characters or less)',
                    existing_runtags=existing_runtags)

        # Set up custom fields
        other_fields = (SubmitFormField.objects
                        .filter(submit_form=context['form'])
                        .order_by('sequence'))
        for field in other_fields:
            if field.question_type == SubmitFormField.QuestionType.TEXT:
                fields[field.meta_key] = forms.CharField(label=field.question)

            elif field.question_type == SubmitFormField.QuestionType.NUMBER:
                fields[field.meta_key] = forms.IntegerField(label=field.question)

            elif field.question_type == SubmitFormField.QuestionType.RADIO:
                choices = list(map(lambda x: (x,x), field.choices.split(',')))
                fields[field.meta_key] = forms.ChoiceField(
                    label=field.question,
                    choices=choices)

            elif field.question_type == SubmitFormField.QuestionType.CHECKBOX:
                if field.choices.startswith('TRACKS'):
                    fields[field. meta_key] = forms.ModelMultipleChoiceField(
                        label=field.question,
                        widget=forms.CheckboxSelectMultiple,
                        queryset=(Track.objects
                                  .filter(conference=context['conf'])
                                  .exclude(shortname='papers')))
                else:
                    choices = list(map(lambda x: (x,x), field.choices.split(',')))
                    fields[field.meta_key] = forms.MultipleChoiceField(
                        label=field.question,
                        widget=forms.CheckboxSelectMultiple,
                        choices=choices)

            elif field.question_type == SubmitFormField.QuestionType.EMAIL:
                fields[field.meta_key] = forms.EmailField(label=field.question)

            elif field.question_type == SubmitFormField.QuestionType.COMMENT:
                fields[field.meta_key] = forms.CharField(label=field.question,
                                                         widget=forms.Textarea)

            elif field.question_type == SubmitFormField.QuestionType.YESNO:
                fields[field.meta_key] = forms.ChoiceField(
                    label=field.question,
                    choices=[('yes', 'Yes'), ('no', 'No')])

            fields[field.meta_key].required = field.required
            fields[field.meta_key].blank = not field.required
            fields[field.meta_key].help_text = field.help_text

        return type('SubmitFormForm', (forms.Form,), fields)
