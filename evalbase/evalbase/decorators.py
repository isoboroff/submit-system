import functools
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import *

def evalbase_login_required(view_func):
    '''A convenience wrapper around the Django login_required
    decorator, that specifies the arguments we use in EvalBase.
    '''
    return login_required(view_func,
                          redirect_field_name='next',
                          login_url=reverse_lazy('login'))


def user_is_member_of_org(view_func):
    '''Confirm that the request.user is a member of the org named
    by the kwarg 'org'.
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'org' not in kwargs:
            raise Http404
        org = get_object_or_404(Organization, shortname=kwargs['org'])
        if (org.owner == request.user or
            org.members.filter(pk=request.user.pk).exists()):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return wrapped_view


def user_owns_org(view_func):
    '''Confirm that the request.user is the owner of the org
    named by the kwarg 'org'.
    '''
    @functools.wraps
    def wrapped_view(request, *args, **kwargs):
        if 'org' not in kwargs:
            raise Http404
        org = get_object_or_404(Organization, shortname=kwargs['org'])
        if (org.owner == request.user):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return wrapped_view


def user_is_active_participant(view_func):
    '''Confirm that the request.user is a member of an org in the conf
    named by kwarg['conf'], and that the org has submitted at least one
    submission.
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'conf' not in kwargs:
            raise Http404
        valid_orgs = (Organization.objects
                      .filter(conference__shortname=kwargs['conf'])
                      .filter(members__pk=request.user.pk))
        subs = (Submission.objects
                .filter(task__conference__shortname=kwargs['conf'])
                .filter(submitted_by_in=valid_orgs))
        if subs:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return wrapped_view


def user_may_edit_submission(view_func):
    '''Confirm that the request.user is either the submittor
    of the kwarg 'runtag' submitted to kwarg 'conf', or that
    the request.user is the owner of the group that submitted it.
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'conf' not in kwargs or 'runtag' not in kwargs:
            raise Http404
        sub = get_object_or_404(Submission,
                                Q(task__conference__shortname=kwargs['conf']) &
                                Q(runtag=kwargs['runtag']))
        if (sub.submitted_by == request.user or
            request.user == sub.org.owner):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return wrapped_view
