import functools
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseRedirect
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import *

# These permission decorators follow a general API pattern,
# where keywords in the URLconf that are retrieved from
# the database are returned as extra kwargs entries.

def evalbase_login_required(view_func):
    '''A convenience wrapper around the Django login_required
    decorator, that specifies the arguments we use in EvalBase.
    '''
    return login_required(view_func,
                          redirect_field_name='next',
                          login_url=reverse_lazy('login'))


def user_is_member_of_org(view_func):
    '''Confirm that the request.user is a member of the org named
    by the kwargs 'org' and 'conf'
    kwargs: org, conf
    returns: _org
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'org' not in kwargs or 'conf' not in kwargs:
            raise Http404('No such org or conf')
        org = get_object_or_404(Organization,
                                shortname=kwargs['org'],
                                conference__shortname=kwargs['conf'])
        if (org.owner == request.user or
            org.members.filter(pk=request.user.pk).exists()):
            kwargs['_org'] = org
            kwargs['_conf'] = get_object_or_404(Conference,
                                                shortname=kwargs['conf'])
            return view_func(request, *args, **kwargs)
        raise PermissionDenied('User is not member of org')
    return wrapped_view


def user_owns_org(view_func):
    '''Confirm that the request.user is the owner of the org
    named by the kwarg 'org'.
    kwargs: org
    returns: _org
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'org' not in kwargs or 'conf' not in kwargs:
            raise Http404('No such org or conf')
        org = get_object_or_404(Organization,
                                shortname=kwargs['org'],
                                conference__shortname=kwargs['conf'])
        if (org.owner == request.user):
            kwargs['_org'] = org
            kwargs['_conf'] = get_object_or_404(Conference,
                                                shortname=kwargs['conf'])
            return view_func(request, *args, **kwargs)
        raise PermissionDenied('User is not org owner')
    return wrapped_view


def user_is_active_participant(view_func):
    '''Confirm that the request.user is a member of an org in the conf
    named by kwarg['conf'], and that the org has submitted at least one
    submission.
    kwargs: conf
    returns: _valid_orgs, _subs
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'conf' not in kwargs:
            raise Http404('No such conf')
        valid_orgs = (Organization.objects
                      .filter(conference__shortname=kwargs['conf'])
                      .filter(members__pk=request.user.pk))
        subs = (Submission.objects
                .filter(task__conference__shortname=kwargs['conf'])
                .filter(submitted_by_in=valid_orgs))
        if subs:
            kwargs['_valid_orgs'] = valid_orgs
            kwargs['_subs'] = subs
            return view_func(request, *args, **kwargs)
        raise PermissionDenied('User is not active participant')
    return wrapped_view


def user_is_participant(view_func):
    '''Confirm that the user is a member of an org registered to
    participate in the conf named by kwargs['conf'].  This is essentially
    the same permission as user_is_member_of_org, except there's
    no org in kwargs.
    kwargs: conf
    returns: _valid_orgs
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'conf' not in kwargs:
            raise Http404('No such conf')
        valid_orgs = (Organization.objects
                      .filter(conference__shortname=kwargs['conf'])
                      .filter(members__pk=request.user.pk))
        if valid_orgs:
            kwargs['_valid_orgs'] = valid_orgs
            return view_func(request, *args, **kwargs)
        raise PermissionDenied('User is not a member of a participating group')
    return wrapped_view

def user_is_track_coordinator(view_func):
    '''Confirm that the user is a coordinator for this task.
    Staff are coordinators for all tasks.
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_staff:
            if 'conf' not in kwargs:
                raise Http404('No such conf')
            is_coord = (Track.objects.
                        filter(conference__shortname=kwargs['conf']))
        else:
            if 'conf' not in kwargs or 'task' not in kwargs:
                raise Http404('No such conf or track')
            task = get_object_or_404(Task, shortname=kwargs['task'])
            track = task.track
            is_coord = track.coordinators.filter(pk=request.user.pk)

        if is_coord:
            kwargs['_is_coord'] = is_coord
            return view_func(request, *args, **kwargs)
        raise PermissionDenied('User is not a coordinator of this track')
    return wrapped_view

def user_is_staff(view_func):
    '''Confirm that the request.user is_staff.
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_staff:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied('User is not staff')
    return wrapped_view

def user_may_edit_submission(view_func):
    '''Confirm that the request.user is either the submittor
    of the kwarg 'runtag' submitted to kwarg 'conf', or that
    the request.user is the owner of the group that submitted it.
    kwargs: conf, runtag
    returns: _sub
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'conf' not in kwargs or 'runtag' not in kwargs:
            raise Http404('No such conf or runtag')
        sub = get_object_or_404(Submission,
                                Q(task__track__conference__shortname=kwargs['conf']) &
                                Q(runtag=kwargs['runtag']))
        if (sub.submitted_by == request.user or
            request.user == sub.org.owner):
            kwargs['_sub'] = sub
            return view_func(request, *args, **kwargs)
        raise PermissionDenied('User may not edit submission')
    return wrapped_view


def conference_is_open(view_func):
    '''Confirm that the conference named in the kwarg 'conf' is not complete.
    kwargs: conf
    returns: _conf
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'conf' not in kwargs:
            raise Http404('No such conf')
        conf = get_object_or_404(Conference, shortname=kwargs['conf'])
        if not conf.complete:
            kwargs['_conf'] = conf
            return view_func(request, *args, **kwargs)
        raise PermissionDenied('Conference is not open')
    return wrapped_view


def task_is_open(view_func):
    '''Confirm that the task is still open for submissions.
    kwargs: conf, task
    returns: _conf, _task
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'conf' not in kwargs or 'task' not in kwargs:
            raise Http404('No such conf or task')
        conf = get_object_or_404(Conference, shortname=kwargs['conf'])
        task = get_object_or_404(Task, shortname=kwargs['task'], track__conference=conf)
        if task.task_open:
            kwargs['_conf'] = conf
            kwargs['_task'] = task
            return view_func(request, *args, **kwargs)
        raise PermissionDenied('Task is not open')
    return wrapped_view

def agreements_signed(view_func):
    '''Confirm that the user has signed all agreements required by the conf.
    kwargs: conf
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'conf' not in kwargs:
            raise Http404('No such conf')
        conf = get_object_or_404(Conference, shortname=kwargs['conf'])
        signed = True
        for ag in conf.agreements.all():
            signed = False
            to_sign = ag
            for sig in ag.signature_set.all():
                if sig.user == request.user:
                    signed = True
        if not signed:
            # raise PermissionDenied('You haven\'t signed the necessary agreements')
            return HttpResponseRedirect(
                reverse('sign-agreement',
                        kwargs={'conf': conf,
                                'agreement': to_sign}))

        return view_func(request, *args, **kwargs)
    return wrapped_view


def check_conf_and_task(view_func):
    '''Check conf and task fields of URL and if they're ok, return
    the objects in the kwargs.
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'conf' not in kwargs or 'task' not in kwargs:
            raise Http404('No such conf')
        conf = get_object_or_404(Conference, shortname=kwargs['conf'])
        task = get_object_or_404(Task, shortname=kwargs['task'],
                                 track__conference=conf)

        kwargs['_conf'] = conf
        kwargs['_task'] = task
        return view_func(request, *args, **kwargs)
    return wrapped_view
