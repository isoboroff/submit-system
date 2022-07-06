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

class SignUp(generic.edit.CreateView):
    form_class = SignupForm
    success_url = reverse_lazy('profile-create')
    template_name = 'evalbase/signup.html'

class EvalBaseLoginReqdMixin(LoginRequiredMixin):
    login_url = reverse_lazy('login')

class ProfileDetail(EvalBaseLoginReqdMixin, generic.detail.DetailView):
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
    model = UserProfile
    fields = ['street_address', 'city_state', 'country', 'postal_code']
    template_name = 'evalbase/profile_form.html'

    # The profile is always for the current user.
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class ProfileEdit(EvalBaseLoginReqdMixin, generic.edit.UpdateView):
    model = UserProfile
    fields = ['street_address', 'city_state', 'country', 'postal_code']
    template_name = 'evalbase/profile_form.html'

    # You can only see your own profile.
    def get_object(self):
        try:
            return UserProfile.objects.get(user=self.request.user)
        except:
            return None

class OrganizationList(EvalBaseLoginReqdMixin, generic.ListView):
    model = Organization
    template_name = 'evalbase/my-orgs.html'

    def get_queryset(self):
        # return orgs I own or I am a member of.
        rs = Organization.objects.filter(members__pk=self.request.user.pk)
        rs = rs.union(Organization.objects.filter(owner=self.request.user))
        return rs

class OrganizationDetail(EvalBaseLoginReqdMixin, generic.DetailView):
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
    model = Organization
    template_name = 'evalbase/org-create.html'
    fields = ['shortname', 'longname', 'task_interest']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.conf = Conference.objects.get(shortname=self.kwargs['conf'])
        context['conf'] = self.conf
        return context

    def form_valid(self, form):
        form.instance.contact_person = self.request.user
        form.instance.owner = self.request.user
        confname = self.kwargs['conf']
        form.instance.conference = Conference.objects.get(shortname=confname)
        form.instance.passphrase = uuid.uuid4()
        form.instance.save()
        form.instance.members.add(self.request.user)
        return super().form_valid(form)


class OrganizationJoin(EvalBaseLoginReqdMixin, generic.TemplateView):
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







class ListAgreements(EvalBaseLoginReqdMixin, generic.ListView):
    model = Agreement
    template_name ='evalbase/agreements.html'

    def get_queryset(self):
        conf = Conference.objects.get(shortname=self.kwargs['conf'])
        return conf.agreements.all()

class HomeView(LoginRequiredMixin, generic.base.TemplateView):
    template_name = 'evalbase/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['open_evals'] = Conference.objects.filter(open_signup=True)
        context['my_orgs'] = Organization.objects.filter(members__pk=self.request.user.pk).filter(conference__complete=False)
        context['submissions'] = Submission.objects.filter(submitted_by_id=self.request.user.id)
        return context

class ConferenceTasks(EvalBaseLoginReqdMixin, generic.ListView):
    model = Task
    template_name = 'evalbase/tasks.html'

    def get_queryset(self):
        return Task.objects.filter(conference__shortname=self.kwargs['conf']).filter(task_open=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conf = Conference.objects.get(shortname=self.kwargs['conf'])
        orgs = Organization.objects.filter(members__pk=self.request.user.pk).filter(conference=conf)
        myruns = Submission.objects.filter(task__conference=conf).filter(org__in=orgs).order_by('task')
        context['conf'] = conf
        context['myruns'] = myruns
        return context

class SubmitTask(EvalBaseLoginReqdMixin, generic.TemplateView):
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
        # Adding groups to conferences is broken right now, so I'm choosing any temporarily.
        # This will need to get changed. TODO
        # context['orgs'] = Organization.objects.filter(members=self.request.user).filter(conference=conf)
        context['orgs'] = Organization.objects.all()

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
            sub = Submission(task=context['task'],
                             org=Organization.objects.filter(conference=context['conf']).filter(shortname=stuff['org'])[0],
                             submitted_by=request.user,
                             runtag=stuff['runtag'],
                             file=stuff['runfile'],
                             is_validated=False,
                             has_evaluation=False
                             )
            sub.save()

            custom_fields = SubmitFormField.objects.filter(submit_form=context['form'])
            for field in custom_fields:
                smeta = SubmitMeta(submission=sub, form_field=field, key=field.meta_key, value=stuff[field.meta_key])
                smeta.save()
            return render(request, 'evalbase/home.html', context={'form': stuff})
            ## FIXME - Not the correct forwarding after
        else:
            context['gen_form'] = form
            return render(request, 'evalbase/submit.html', context=context)

class EditTask(EvalBaseLoginReqdMixin, generic.TemplateView):
    template_name = 'evalbase/edit.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conf = Conference.objects.get(shortname=kwargs['conf'])
        task = Task.objects.get(shortname=kwargs['task'], conference=conf)
        submitform = SubmitForm.objects.get(task=task)
        run = Submission.objects.filter(submitted_by_id=self.request.user.id).filter(task__conference__shortname=self.kwargs['conf']).filter(id = context['id'])[0]
        context['conf'] = conf
        context['task'] = task
        context['form'] = submitform
        context['user'] = self.request.user
        context['org'] = run.org
        context['runtag'] = run.runtag
        context['file'] = run.file
        context['id'] = run.id
        # Adding groups to conferences is broken right now, so I'm choosing any temporarily.
        # This will need to get changed. TODO
        # context['orgs'] = Organization.objects.filter(members=self.request.user).filter(conference=conf)
        context['orgs'] = Organization.objects.all()
        form_class = SubmitFormForm.edit_form_class(context)
        sff = form_class()
        context['gen_form'] = sff
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form_class = SubmitFormForm.get_form_class(context)
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            run = Submission.objects.filter(submitted_by_id=self.request.user.id).filter(
                task__conference__shortname=self.kwargs['conf']).filter(id=context['id'])[0]
            stuff = form.cleaned_data
            print("FILE IS")
            print(stuff['runfile'])
            run.file = stuff['runfile']
            run.org = Organization.objects.filter(conference=context['conf']).filter(shortname=stuff['org'])[0]
            run.runtag = stuff['runtag']
            run.save()

            custom_fields = SubmitFormField.objects.filter(submit_form=context['form'])
            for field in custom_fields:
                original = SubmitMeta.objects.filter(key=field.meta_key).filter(submission_id=run.id)[0]
                original.value = stuff[field.meta_key]
                original.save()


            return render(request, 'evalbase/home.html', context={'form': stuff})
            ## FIXME
        else:
            context['gen_form'] = form
            return render(request, 'evalbase/submit.html', context=context)



class Submissions(EvalBaseLoginReqdMixin, generic.TemplateView):
    template_name = 'evalbase/run.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # run = Submission.objects.filter(runtag=self.kwargs['runtag']).filter(task__shortname=self.kwargs['task']).filter(task__conference__shortname=self.kwargs['conf'])
        run = Submission.objects.filter(runtag=self.kwargs['runtag']).filter(task__conference__shortname=self.kwargs['conf'])
        if run[0].submitted_by != self.request.user:
            raise PermissionDenied()
        context['submission'] = run[0]
        context['metas'] = SubmitMeta.objects.filter(submission_id=context['submission'].id)
        field_descs = {}
        for meta in context['metas']:
            field_descs[meta.key] = meta.form_field.question
        context['fields'] = field_descs
        context["file"] = context['submission'].file
        return context


@login_required
def download(request, conf, task, runtag):
    print(request,conf,task, runtag)
    run = Submission.objects.filter(runtag=runtag).filter(task__conference__shortname=conf)
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