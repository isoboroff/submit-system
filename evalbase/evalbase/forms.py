from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import password_validation
from .models import *


class SignupForm(UserCreationForm):
    # Stop these fields from including autocomplete attributes.
    # NIST web scanner says no-no.
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput(),
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name',
                  'email',
                  'password1', 'password2')


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

        task_choices = [(task.shortname, task.longname)
                        for task in context['all_tasks']]
        fields["task_interest"] = forms.MultipleChoiceField(
            label="Select tasks",
            choices=task_choices,
            widget=forms.CheckboxSelectMultiple,
            required=False,
            initial=context['tasks'])

        return type('MembersEditForm', (forms.Form,), fields)


class AgreementForm(forms.Form):
    sigtext = forms.CharField(label='Signature',
                              help_text='Please type your full name',
                              max_length=50)


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
            fields['runtag'] = forms.CharField(
                label='Runtag: a short identifier for the run',
                validators=[SubmitFormForm.make_runtag_checker(context)])
        else:
            fields['runtag'] = forms.CharField(label='runtag')

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
                choices = list(map(lambda x: (x,x), field.choices.split(',')))
                fields[field.meta_key] = forms.MultipleChoiceField(
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

        return type('SubmitFormForm', (forms.Form,), fields)


    def make_runtag_checker(context):
        def thunk(value):
            if runtag == 'submit' or runtag == 'list':
                raise ValidationError(
                    _('Submissions may not be named "submit" or "list"'))

            tags = (Submission.objects
                    .filter(task__conference=context['conf'])
                    .filter(runtag=value))
            if tags:
                raise ValidationError(
                    _('A submission with runtag %(runtag) has already been submitted.'),
                    params={'runtag': value})
        return thunk
