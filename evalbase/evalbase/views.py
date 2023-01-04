import uuid
import logging
from datetime import datetime
from django import utils
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views import generic
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseRedirect, Http404, FileResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import PermissionDenied
from .models import *
from .forms import *
from .decorators import *

@require_http_methods(['GET', 'POST'])
def signup_view(request):
    if request.method == 'GET':
        context = {'form': SignupForm()}
        return render(request, 'evalbase/signup.html', context)

    elif request.method == 'POST':
        form_data = SignupForm(request.POST)
        if form_data.is_valid():
            form_data.save()
        return HttpResponseRedirect(reverse_lazy('profile-create-edit'))


class EvalBaseLoginReqdMixin(LoginRequiredMixin):
    '''This subclasses the LoginRequiredMixin to point to our login view.'''

    login_url = reverse_lazy('login')


# User profiles are the model that holds information about users.  The
# User model itself comes from Django's auth library.  To add stuff like
# contact info or whatever, we use a UserProfile model.


@evalbase_login_required
@require_http_methods(['GET'])
def profile_view(request):
    profile = UserProfile.objects.filter(user=request.user).first()
    if not profile:
        return HttpResponseRedirect(reverse_lazy('profile-create-edit'))
    context = {'userprofile': profile,
               'orgs': (Organization.objects
                        .filter(Q(members=request.user)|Q(owner=request.user))
                        .filter(conference__complete=False)),
               'signatures': Signature.objects.filter(user=request.user)}
    return render(request, 'evalbase/profile_view.html', context)


@evalbase_login_required
@require_http_methods(['GET', 'POST'])
def profile_create_edit(request):
    if request.method == 'GET':
        cur_profile = UserProfile.objects.filter(user=request.user).first()
        if cur_profile:
            form = ProfileForm(instance=cur_profile,
                               initial={'user': request.user})
        else:
            form = ProfileForm()
        return render(request, 'evalbase/profile_form.html',
                      {'form': form})

    elif request.method == 'POST':
        cur_profile = UserProfile.objects.filter(user=request.user).first()
        if cur_profile:
            form_data = ProfileForm(request.POST, instance=cur_profile)
        else:
            form_data = ProfileForm(request.POST)

        if form_data.is_valid:
            if not cur_profile:
                instance = form_data.save(commit=False)
                instance.user = request.user
                instance.save()
            else:
                form_data.save()

        return HttpResponseRedirect(reverse_lazy('profile'))


# Organizations register to participate in Conferences.  Other kinds of
# evaluation activities might call them "teams" or "performers", but
# TREC isn't about winning or performing, it's about sciencing.

# One user registers an organization.  In order to join an organization,
# there is a special sign-up token URL that you share with members of your
# organization.


@evalbase_login_required
@user_is_member_of_org
@require_http_methods(['GET'])
def org_view(request, *args, **kwargs):
    return render(request, 'evalbase/org-detail.html', {'object': kwargs['_org']})


@evalbase_login_required
@user_is_member_of_org
@conference_is_open
@require_http_methods(['GET', 'POST'])
def org_edit(request, *args, **kwargs):

    org = kwargs['_org']
    members = org.members.all().exclude(id=request.user.id)
    context = {'org': org, 'members': members}

    if request.method == 'GET':
        form_class = MembersEditForm.get_form_class(context)
        form = form_class()
        context['gen_form'] = form
        return render(request, 'evalbase/org-edit.html', context)

    elif request.method == 'POST':
        form_class = MembersEditForm.get_form_class(context)
        form = form_class(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            org.members.remove(*cleaned['users'])
        return HttpResponseRedirect(reverse_lazy('org-detail',
                                                 kwargs={'conf': kwargs['conf'],
                                                         'org': kwargs['org']}))


@evalbase_login_required
@conference_is_open
@require_http_methods(['GET', 'POST'])
def org_create(request, *args, **kwargs):
    '''Create an organization.  This is signing up to participate in
    an evaluation.

    The complex thing about this form is that we ask registrants to indicate
    which tracks they would like to participate in.  So we need to get the
    list of tracks for this conference.

    In form validation, we create the random signup key URL.
    '''

    class _Form(forms.Form):
        shortname = forms.CharField(max_length=15)
        longname = forms.CharField(max_length=50)
        task_interest = forms.ModelMultipleChoiceField(
            widget=forms.CheckboxSelectMultiple,
            queryset=(Task
                      .objects
                      .filter(conference=kwargs['_conf'])
                      .order_by('longname')))

    if request.method == 'GET':
        form = _Form()
        return render(request, 'evalbase/org-create.html',
                      { 'conf': kwargs['_conf'],
                        'form': form })

    elif request.method == 'POST':
        form = _Form(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            org = Organization(
                shortname=cleaned['shortname'],
                longname=cleaned['longname'],
                contact_person=request.user,
                owner=request.user,
                conference=kwargs['_conf'],
                passphrase=uuid.uuid4())
            org.save()
            org.task_interest.set(cleaned['task_interest'])
            org.members.add(request.user)
            org.save()
            return HttpResponseRedirect(reverse_lazy('home'))
        else:
            return render(request, 'evalbase/org-create.html',
                          { 'conf': kwargs['_conf'],
                            'form': form })


@evalbase_login_required
@require_http_methods(['GET', 'POST'])
def org_join(request, *args, **kwargs):
    '''Join an organization.  This view is triggered by someone
    using the special 'join-org' key for an organization.
    The conference has to be open, but since the URL doesn't have
    the conference specified, we can't use the conference_is_open
    decorator.
    '''

    org = Organization.objects.filter(passphrase=kwargs['key'])
    if not org:
        raise Http404('org not found, wtf')
    org = org[0]
    if not org.conference.open_signup:
        raise PermissionDenied

    if request.method == 'GET':
        return render(request, 'evalbase/join.html',
                      { 'org': org,
                        'key': kwargs['key'] })

    elif request.method == 'POST':
        user = request.user
        org.members.add(user)
        return HttpResponseRedirect(reverse_lazy('home'))


@evalbase_login_required
def home_view(request, *args, **kwargs):
    '''The main page.  You can see what conferences you are participating
    in and which ones you can sign up to participate in.
    '''
    open_evals = Conference.objects.filter(open_signup=True)
    my_orgs = (Organization.objects
               .filter(members__pk=request.user.pk)
               .filter(conference__complete=False))
    complete = (Conference.objects
                .filter(complete=True)
                .filter(participants__members__pk=request.user.pk))

    return render(request, 'evalbase/home.html',
                  { 'open_evals': open_evals,
                    'my_orgs': my_orgs,
                    'complete': complete })


class ConferenceTasks(EvalBaseLoginReqdMixin, generic.ListView):
    '''List the tracks in a conference.'''

    model = Task
    template_name = 'evalbase/tasks.html'

    def get_queryset(self):
        return (Task.objects
                .filter(conference__shortname=self.kwargs['conf'])
                .filter(task_open=True))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conf = Conference.objects.get(shortname=self.kwargs['conf'])
        orgs = (Organization.objects
                .filter(members__pk=self.request.user.pk)
                .filter(conference=conf))
        myruns = (Submission.objects
                  .filter(task__conference=conf)
                  .filter(org__in=orgs)
                  .order_by('task'))
        agreements = conf.agreements.exclude(signature__user=self.request.user.pk)
        context['conf'] = conf
        context['myruns'] = myruns
        context['agreements'] = agreements
        return context


@login_required(login_url=reverse_lazy('login'))
def sign_agreement(request, conf, agreement):
    agrobj = get_object_or_404(Agreement, name=agreement)
    template = 'evalbase/' + agrobj.template

    # Check if the form was already signed
    existing = Signature.objects.filter(user=request.user,
                                        agreement=agrobj)
    if existing:
        return HttpResponseRedirect(reverse('tasks', kwargs={'conf': conf}))

    if request.method == 'POST':
        form = AgreementForm(request.POST)
        if form.is_valid():
            sig = Signature(user=request.user,
                            agreement=agrobj,
                            sigtext=form.cleaned_data['sigtext'])
            sig.save()
            return HttpResponseRedirect(reverse('tasks', kwargs={'conf': conf}))
    else:
        form = AgreementForm()

    return render(request, template, { 'form': form })


class SubmitRun(EvalBaseLoginReqdMixin, generic.TemplateView):
    '''This is the view for submitting a run to a task.  Each task has
    a custom set of metadata fields for the submission form, and those
    are described in the SubmitMetas class.  This form is what creates
    Submissions.
    '''

    template_name = 'evalbase/submit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conf = Conference.objects.get(shortname=kwargs['conf'])
        task = Task.objects.get(shortname=kwargs['task'], conference=conf)
        submitform = SubmitForm.objects.get(task=task)

        context['conf'] = conf
        context['task'] = task
        context['form'] = submitform
        context['user'] = self.request.user
        context['orgs'] = (Organization.objects
                           .filter(members__pk=self.request.user.pk)
                           .filter(conference=conf))
        context['mode'] = 'submit'

        form_class = SubmitFormForm.get_form_class(context)
        sff = form_class()
        context['gen_form'] = sff
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form_class = SubmitFormForm.get_form_class(context)
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            stuff = form.cleaned_data
            org = (Organization.objects
                   .filter(shortname=stuff['org'])
                   .filter(members__pk=self.request.user.pk)
                   .filter(conference=context['conf']))[0]

            sub = Submission(task=context['task'],
                             org = org,
                             submitted_by=request.user,
                             runtag=stuff['runtag'],
                             is_validated=False,
                             has_evaluation=False
                             )
            sub.save()

            custom_fields = SubmitFormField.objects.filter(submit_form=context['form'])
            for field in custom_fields:
                smeta = SubmitMeta(submission=sub,
                                   form_field=field,
                                   key=field.meta_key,
                                   value=stuff[field.meta_key])
                smeta.save()
            return HttpResponseRedirect(reverse('tasks',
                                                kwargs={'conf': self.kwargs['conf']}))
        else:
            context['gen_form'] = form
            return render(request, 'evalbase/submit.html', context=context)


class EditSubmission(EvalBaseLoginReqdMixin, generic.TemplateView):
    '''A form for editing the metadata for a submission.'''

    template_name = 'evalbase/edit.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conf = Conference.objects.get(shortname=kwargs['conf'])
        task = Task.objects.get(shortname=kwargs['task'], conference=conf)
        submitform = SubmitForm.objects.get(task=task)

        if not task.task_open:
            raise PermissionDenied('Task is closed')

        context['conf'] = conf
        context['task'] = task
        context['form'] = submitform
        context['user'] = self.request.user
        context['orgs'] = (Organization.objects
                           .filter(members__pk=self.request.user.pk)
                           .filter(conference=conf))
        context['mode'] = 'edit'
        form_class = SubmitFormForm.get_form_class(context)

        run = (Submission.objects
               .filter(submitted_by_id=self.request.user.id)
               .filter(task__conference__shortname=self.kwargs['conf'])
               .filter(id=kwargs['id'])[0])

        form_info = {'conf': conf,
                     'task': run.task,
                     'org': run.org,
                     'user': run.submitted_by,
                     'email': run.submitted_by.email,
                     'runtag': run.runtag,
                     'runfile': run.file}
        other_infos = SubmitMeta.objects.filter(submission=run)
        for run_meta in other_infos:
            form_info[run_meta.key] = run_meta.value

        sff = form_class(form_info)
        context['gen_form'] = sff
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if not context['task'].task_open:
            raise Http404('Task closed')

        form_class = SubmitFormForm.get_form_class(context)
        form = form_class(request.POST)
        if form.is_valid():
            stuff = form.cleaned_data
            run = (Submission.objects
                   .filter(submitted_by_id=self.request.user.id)
                   .filter(task__conference__shortname=self.kwargs['conf'])
                   .filter(runtag=stuff['runtag'])[0])
            stuff = form.cleaned_data
            org = (Organization.objects
                   .filter(members__pk=self.request.user.pk)
                   .filter(shortname=stuff['org'])
                   .filter(conference__shortname=self.kwargs['conf']))
            if not org:
                raise Http404()

            run.org = org[0]
            run.runtag = stuff['runtag']
            run.save()

            custom_fields = SubmitFormField.objects.filter(submit_form=context['form'])
            for field in custom_fields:
                original = (SubmitMeta.objects
                            .filter(key=field.meta_key)
                            .filter(submission_id=run.id)[0])
                original.value = stuff[field.meta_key]
                original.save()


            return HttpResponseRedirect(reverse_lazy('home'))
        else:
            context['gen_form'] = form
            return render(request, 'evalbase/submit.html', context=context)


class DeleteSubmission(EvalBaseLoginReqdMixin, generic.DeleteView):
    model = Submission
    # success_url = reverse_lazy('tasks', kwargs['conf'])
    slug_url_kwarg = 'runtag'
    slug_field = 'runtag'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = super().get_object()

        if self.request.user != obj.submitted_by or self.request.user != obj.org.owner:
            raise Http404

        context['object'] = obj
        return context

    def get_success_url(self):
        return reverse_lazy('tasks', kwargs={'conf': self.kwargs['conf']})


class Submissions(EvalBaseLoginReqdMixin, generic.TemplateView):
    '''View a submission.'''
    template_name = 'evalbase/run.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        run = (Submission.objects
               .filter(runtag=self.kwargs['runtag'])
               .filter(task__conference__shortname=self.kwargs['conf']))[0]
        if run.submitted_by != self.request.user and run.org.org_owner_of != self.request.user:
            raise PermissionDenied()
        context['submission'] = run
        context['metas'] = (SubmitMeta.objects
                            .filter(submission_id=context['submission'].id))
        field_descs = {}
        for meta in context['metas']:
            field_descs[meta.key] = meta.form_field.question
        context['fields'] = field_descs
        context["file"] = context['submission'].file
        return context


@login_required
def download(request, conf, task, runtag):
    print(request,conf,task, runtag)
    run = (Submission.objects
           .filter(runtag=runtag)
           .filter(task__conference__shortname=conf))
    if run[0].submitted_by != request.user:
        raise PermissionDenied()
    sub = run[0]
    file = sub.file
    try:
        filepath = settings.DOWNLOAD_DATA + "/" +  file.url

        return FileResponse(open(filepath, 'rb'),
            as_attachment=True)
    except FileNotFoundError:
        raise Http404(f'file-not-found, {filepath}')
