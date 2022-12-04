from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import UserCreationForm
from .models import *


class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name',
                  'email',
                  'password1', 'password2')

class MembersEditForm(forms.Form):
    def get_form_class(context):
        fields = {}
        # member_choices = list(map(lambda x: (x.email), context['members']))[0]
        member_choices = []
        for member in context['members']:
            member_choices.append((member.id,f'{member.first_name} {member.last_name} ({member.email})'))
        fields["users"] = forms.ChoiceField(label="Select a user to remove: ", choices=member_choices)
        return type('MembersEditForm', (forms.Form,), fields)



class SubmitFormForm(forms.Form):
    def get_form_class(context):
        fields = {}
        # Set up standard fields
        fields['conf'] = forms.CharField(widget=forms.HiddenInput(), initial=context['conf'].shortname)
        fields['task'] = forms.CharField(widget=forms.HiddenInput(), initial=context['task'].shortname)

        fields['user'] = forms.CharField(label='User name',
                                         widget=forms.TextInput(attrs={'value': context['user'].username,
                                                                       'readonly': 'readonly',
                                                                       'class': 'form-control-plaintext'}))
        fields['email'] = forms.EmailField(label='Email',
                                           widget=forms.EmailInput(attrs={'value': context['user'].email,
                                                                          'readonly': 'readonly',
                                                                          'class': 'form-control-plaintext'}))
        org_choices = list(map(lambda x: (x.shortname, x.longname), context['orgs']))
        fields['org'] = forms.ChoiceField(label='Organization', choices=org_choices)

        fields['runtag'] = forms.CharField(label='runtag',
                                           validators=[SubmitFormForm.make_runtag_checker(context)])
        
        fields['runfile'] = forms.FileField(label='Submission file')
        
        # Set up custom fields
        other_fields = SubmitFormField.objects.filter(submit_form=context['form']).order_by('sequence')
        for field in other_fields:
            if field.question_type == SubmitFormField.QuestionType.TEXT:
                fields[field.meta_key] = forms.CharField(label=field.question)

            elif field.question_type == SubmitFormField.QuestionType.NUMBER:
                fields[field.meta_key] = forms.IntegerField(label=field.question)

            elif field.question_type == SubmitFormField.QuestionType.RADIO:
                choices = list(map(lambda x: (x,x), field.choices.split(',')))
                fields[field.meta_key] = forms.ChoiceField(label=field.question, choices=choices)

            elif field.question_type == SubmitFormField.QuestionType.CHECKBOX:
                choices = list(map(lambda x: (x,x), field.choices.split(',')))
                fields[field.meta_key] = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple,
                                                                   choices=choices)

            elif field.question_type == SubmitFormField.QuestionType.EMAIL:
                fields[field.meta_key] = forms.EmailField(label=field.question)

            elif field.question_type == SubmitFormField.QuestionType.COMMENT:
                fields[field.meta_key] = forms.CharField(label=field.question,
                                                         widget=forms.Textarea)

            elif field.question_type == SubmitFormField.QuestionType.YESNO:
                fields[field.meta_key] = forms.ChoiceField(label=field.question,
                                                           choices=[('yes', 'Yes'), ('no', 'No')])
        return type('SubmitFormForm', (forms.Form,), fields)

    def edit_form_class(context):
        fields = {}
        # Set up standard fields
        fields['conf'] = forms.CharField(widget=forms.HiddenInput(), initial=context['conf'].shortname)
        fields['task'] = forms.CharField(widget=forms.HiddenInput(), initial=context['task'].shortname)

        fields['user'] = forms.CharField(label='User name',
                                         widget=forms.TextInput(attrs={'value': context['user'].username,
                                                                       'readonly': 'readonly',
                                                                       'class': 'form-control-plaintext'}))
        fields['email'] = forms.EmailField(label='Email',
                                           widget=forms.EmailInput(attrs={'value': context['user'].email,
                                                                          'readonly': 'readonly',
                                                                          'class': 'form-control-plaintext'}))
        org_choices = list(map(lambda x: (x.shortname, x.longname), context['orgs']))
        fields['org'] = forms.ChoiceField(label='Organization', choices=org_choices, initial=context['org'])

        fields['runtag'] = forms.CharField(label='runtag',
                                           validators=[SubmitFormForm.make_runtag_checker(context)], initial=context['runtag'])

        fields['runfile'] = forms.FileField(label='Submission file', initial=context["file"]) #FIXME

        # Set up custom fields
        other_fields = SubmitFormField.objects.filter(submit_form=context['form']).order_by('sequence')
        for field in other_fields:
            if field.question_type == SubmitFormField.QuestionType.TEXT:
                print("OG:")
                print(original)
                original = SubmitMeta.objects.filter(key=field.meta_key).filter(submission_id=context["id"])[0]
                fields[field.meta_key] = forms.CharField(label=field.question, initial=original.value)

            elif field.question_type == SubmitFormField.QuestionType.NUMBER:
                original = SubmitMeta.objects.filter(key=field.meta_key).filter(submission_id=context["id"])[0]
                fields[field.meta_key] = forms.IntegerField(label=field.question, initial=original.value)

            elif field.question_type == SubmitFormField.QuestionType.RADIO:
                original = SubmitMeta.objects.filter(key=field.meta_key).filter(submission_id=context["id"])[0]
                choices = list(map(lambda x: (x, x), field.choices.split(',')))
                fields[field.meta_key] = forms.ChoiceField(label=field.question, choices=choices, initial=original.value)

            elif field.question_type == SubmitFormField.QuestionType.CHECKBOX:
                original = SubmitMeta.objects.filter(key=field.meta_key).filter(submission_id=context["id"])[0]
                choices = list(map(lambda x: (x, x), field.choices.split(',')))
                fields[field.meta_key] = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple,
                                                                   choices=choices, initial=original.value)

            elif field.question_type == SubmitFormField.QuestionType.EMAIL:
                original = SubmitMeta.objects.filter(key=field.meta_key).filter(submission_id=context["id"])[0]
                fields[field.meta_key] = forms.EmailField(label=field.question, initial=original.value)

            elif field.question_type == SubmitFormField.QuestionType.COMMENT:
                original = SubmitMeta.objects.filter(key=field.meta_key).filter(submission_id=context["id"])[0]
                fields[field.meta_key] = forms.CharField(label=field.question,
                                                         widget=forms.Textarea, initial=original.value)

            elif field.question_type == SubmitFormField.QuestionType.YESNO:
                original = SubmitMeta.objects.filter(key=field.meta_key).filter(submission_id=context["id"])[0]
                fields[field.meta_key] = forms.ChoiceField(label=field.question,
                                                           choices=[('yes', 'Yes'), ('no', 'No')],initial=original.value)


        return type('SubmitFormForm', (forms.Form,), fields)


    def make_runtag_checker(context):
        def thunk(value):
            tags = SubmitMeta.objects.filter(submission__task=context['task']).filter(key='runtag').filter(value=value)
            if tags:
                raise ValidationError(
                    _('A submission with runtag %(runtag) has already been submitted.'),
                    params={'runtag': value})
        return thunk
