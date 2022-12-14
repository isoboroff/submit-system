import uuid
from datetime import datetime
from django import utils
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views import generic
from django.http import HttpResponseRedirect, Http404, FileResponse
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import PermissionDenied
from .models import *
from .forms import *

# When possible, I try to use generic views.  However, sometimes that makes
# simple things difficult, in which case we have to dive to a lower level.
# It's tricky to decide when you have to dive, but a good rule of thumb is
# when you can't figure out how to do something, you find a solution on
# StackOverflow, and it's very non-ovious or hidden in the Django documentation.

class SignUp(generic.edit.CreateView):
    '''Registering a new user.'''

    form_class = SignupForm
    success_url = reverse_lazy('profile-create')
    template_name = 'evalbase/signup.html'


class EvalBaseLoginReqdMixin(LoginRequiredMixin):
    '''This subclasses the LoginRequiredMixin to point to our login view.'''

    login_url = reverse_lazy('login')


# User profiles are the model that holds information about users.  The
# User model itself comes from Django's auth library.  To add stuff like
# contact info or whatever, we use a UserProfile model.

class ProfileDetail(EvalBaseLoginReqdMixin, generic.detail.DetailView):
    '''User profile detail view.'''

    model = UserProfile
    template_name = 'evalbase/profile_view.html'

    # You can only see your own profile.
    def get_object(self):
        try:
            return UserProfile.objects.get(user=self.request.user)
        except:
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = User.objects.get(pk=self.request.user.id)
        return context


class ProfileCreate(EvalBaseLoginReqdMixin, generic.edit.CreateView):
    '''User profile creation view.'''

    model = UserProfile
    fields = ['street_address', 'city_state', 'country', 'postal_code']
    template_name = 'evalbase/profile_form.html'

    # The profile is always for the current user.
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class ProfileEdit(EvalBaseLoginReqdMixin, generic.edit.UpdateView):
    '''Editing the user profile.'''

    model = UserProfile
    fields = ['street_address', 'city_state', 'country', 'postal_code']
    template_name = 'evalbase/profile_form.html'

    # You can only see your own profile.
    def get_object(self):
        try:
            return UserProfile.objects.get(user=self.request.user)
        except:
            return None


# Organizations register to participate in Conferences.  Other kinds of
# evaluation activities might call them "teams" or "performers", but
# TREC isn't about winning or performing, it's about sciencing.

# One user registers an organization.  In order to join an organization,
# there is a special sign-up token URL that you share with members of your
# organization.


class OrganizationList(EvalBaseLoginReqdMixin, generic.ListView):
    '''List the organizations I'm a member of.'''

    model = Organization
    template_name = 'evalbase/my-orgs.html'

    def get_queryset(self):
        # return orgs I own or I am a member of.
        rs = Organization.objects.filter(members__pk=self.request.user.pk)
        rs = rs.union(Organization.objects.filter(owner=self.request.user))
        return rs


class OrganizationDetail(EvalBaseLoginReqdMixin, generic.DetailView):
    '''Organization detail view.

    The really useful thing here is the signup URL, which must be shared
    with people who want to be part of this organization.
    '''

    model = Organization
    template_name = 'evalbase/org-detail.html'
    slug_field = 'shortname'
    slub_url_kwarg = 'shortname'
    def get_object(self):
        try:
            org = Organization.objects.get(shortname=self.kwargs['shortname'])
            if org.owner == self.request.user or org.members.filter(pk=self.request.user.pk).exists():
                return org
            else:
                raise PermissionDenied()
        except:
            raise PermissionDenied()


class OrganizationEdit(EvalBaseLoginReqdMixin, generic.TemplateView):
    '''The organization edit view is for removing people from the org.'''

    template_name = "evalbase/org-edit.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = Organization.objects.get(shortname=self.kwargs['name'])
        if org.owner == self.request.user or org.members.filter(pk=self.request.user.pk).exists():
            context['org'] = org
            # Get members of the org, but not yourself
            context['members'] = org.members.all().exclude(id = self.request.user.id)
            print("Members:")
            print(context['members'])
            form_class = MembersEditForm.get_form_class(context)
            mef = form_class()
            context['gen_form'] = mef
        else:
            raise PermissionDenied()
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form_class = MembersEditForm.get_form_class(context)
        form = form_class(request.POST)
        # TODO add a confirmation screen of some sort?
        if form.is_valid():
            stuff = form.cleaned_data
            org = context['org']
            user = User.objects.filter(id=stuff['users'])[0]
            org.members.remove(user)
            return HttpResponseRedirect(reverse_lazy('home'))
        else:
            return render(request, 'evalbase/org-edit.html', context=context)


class OrganizationCreate(EvalBaseLoginReqdMixin, generic.edit.CreateView):
    '''Create an organization.  This is signing up to participate in
    an evaluation.

    The complex thing about this form is that we ask registrants to indicate
    which tracks they would like to participate in.  So we need to get the
    list of tracks for this conference.

    In form validation, we create the random signup key URL.
    '''

    model = Organization
    template_name = 'evalbase/org-create.html'
    fields = ['shortname', 'longname', 'task_interest']

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        conf = self.kwargs.get('conf')
        conf = Conference.objects.get(shortname=conf)
        conftasks = Task.objects.filter(conference=conf)
        form.fields['task_interest'].queryset = conftasks
        form.fields['task_interest'].choices = [
            (t.id, t.longname) for t in conftasks]
        form.fields['task_interest'].widget.attrs={'size': str(conftasks.count())}
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.conf = Conference.objects.get(shortname=self.kwargs['conf'])
        context['conf'] = self.conf
        return context

    def form_valid(self, form):
        '''Aside from validating, set up the signup key.'''

        form.instance.contact_person = self.request.user
        form.instance.owner = self.request.user
        confname = self.kwargs['conf']
        form.instance.conference = Conference.objects.get(shortname=confname)
        form.instance.passphrase = uuid.uuid4()
        form.instance.save()
        form.instance.members.add(self.request.user)
        return super().form_valid(form)


class OrganizationJoin(EvalBaseLoginReqdMixin, generic.TemplateView):
    '''This is the view when someone goes to the special join-an-organization
    URL.
    '''

    template_name='evalbase/join.html'

    def get_context_data(self, **kwargs):
        org = Organization.objects.get(passphrase=self.kwargs['key'])
        context = super().get_context_data(**kwargs)
        context['org'] = org
        context['key'] = self.kwargs['key']
        return context

    def post(self, request, *args, **kwargs):
        user = self.request.user
        org = Organization.objects.get(passphrase=self.kwargs['key'])
        org.members.add(user)
        if org.conference.agreements.exists():
            return HttpResponseRedirect(reverse_lazy('agree'), kwargs={'org':org, 'conf': org.conference})
        else:
            return HttpResponseRedirect(reverse_lazy('home'))


# Trying to integrate agreements.  This class is homeless at the moment.

class ListAgreements(EvalBaseLoginReqdMixin, generic.ListView):
    model = Agreement
    template_name ='evalbase/agreements.html'

    def get_queryset(self):
        conf = Conference.objects.get(shortname=self.kwargs['conf'])
        return conf.agreements.all()


class HomeView(EvalBaseLoginReqdMixin, generic.base.TemplateView):
    '''The main page.  You can see what conferences you are participating
    in and which ones you can sign up to participate in.
    '''

    template_name = 'evalbase/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['open_evals'] = Conference.objects.filter(open_signup=True)
        context['my_orgs'] = (Organization.objects
                              .filter(members__pk=self.request.user.pk)
                              .filter(conference__complete=False))
        context['complete'] = (Conference.objects
                               .filter(complete=True)
                               .filter(participants__members__pk=self.request.user.pk))
        return context


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
        context['conf'] = conf
        context['myruns'] = myruns
        return context


class SubmitTask(EvalBaseLoginReqdMixin, generic.TemplateView):
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
            sub = Submission(task=stuff['task'],
                             org = stuff['org'],
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
            return render(request, 'evalbase/home.html')
        else:
            context['gen_form'] = form
            return render(request, 'evalbase/submit.html', context=context)


class EditTask(EvalBaseLoginReqdMixin, generic.TemplateView):
    '''A form for editing the metadata for a submission.'''

    template_name = 'evalbase/edit.html'
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
                return Http404

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


class Submissions(EvalBaseLoginReqdMixin, generic.TemplateView):
    '''View a submission.'''
    template_name = 'evalbase/run.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        run = (Submission.objects
               .filter(runtag=self.kwargs['runtag'])
               .filter(task__conference__shortname=self.kwargs['conf']))
        if run[0].submitted_by != self.request.user:
            raise PermissionDenied()
        context['submission'] = run[0]
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
