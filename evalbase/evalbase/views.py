import json
import time
import uuid
import logging
import collections
import zipfile
import tempfile
from django.conf import settings
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.urls import reverse_lazy
from django.utils.datastructures import MultiValueDictKeyError
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import PermissionDenied
from django.views.decorators.cache import never_cache
from django.db.models.query import QuerySet
from django.contrib import messages
import secrets
import jwt

import requests
import urllib

from .models import *
from .forms import *
from .decorators import *
from .tasks import run_check_script
from .utils import infinite_defaultdict

def site_is_down(request):
    return render(request, 'evalbase/site-down.html')

@require_http_methods(['GET', 'POST'])
def login_view(request):
    if settings.DEBUG and request.get_host() == '127.0.0.1:8000':
        if request.method == 'GET':
            form = DebuggingLoginForm()
            context = { 'form': form }
            return render(request, 'evalbase/simple_login.html', context)
    
        elif request.method == 'POST':
            form_data = DebuggingLoginForm(request.POST)
            if form_data.is_valid():
                try:
                    user = User.objects.get(username=form_data.cleaned_data['login_as'])
                except:
                    return Http404
                login(request, user)
                return HttpResponseRedirect(reverse_lazy('home'))
    else:
        return render(request, 'registration/login.html')

@require_http_methods(['GET'])
def login_gov_initiate(request):
    request.session['app_state'] = secrets.token_urlsafe(64)
    request.session['nonce'] = secrets.token_urlsafe(64)
    request.session.modified = True

    query_params = {
        'acr_values': 'urn:acr.login.gov:auth-only',
        'client_id': settings.LOGIN_GOV['client_id'],
        'redirect_uri': settings.LOGIN_GOV['redirect_uri'],
        'scope': 'openid email profile:name',
        'state': request.session['app_state'],
        'nonce': request.session['nonce'],
        'response_type': 'code',
        'prompt': 'select_account',
    }
    # build request_uri
    request_uri = '{base_url}?{query_params}'.format(
        base_url=settings.OPENID['authorization_endpoint'],
        query_params=requests.compat.urlencode(query_params)
    )

    return redirect(request_uri)

@require_http_methods(['GET'])
def login_gov_complete(request):
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    try:
        code = request.GET['code']
        app_state = request.GET['state']
    except MultiValueDictKeyError:
        return HttpResponse('Forbidden', status=403, reason='Missing query parameters')

    if app_state != request.session['app_state']:
        return HttpResponse('Forbidden', status=403, reason='App state mismatch')
    if not code:
        return HttpResponse('Forbidden', status=403, reason='Code missing')
    
    private_key = open('ssl/private.pem', 'r').read()
    jwt_encoded = jwt.encode({'iss': settings.LOGIN_GOV['client_id'],
                              'sub': settings.LOGIN_GOV['client_id'],
                              'aud': settings.OPENID['token_endpoint'],
                              'jti': secrets.token_urlsafe(16),
                              'exp': int(time.time()) + 300},
                              private_key, algorithm="RS256")

    query_params = {'grant_type': 'authorization_code',
                    'code': code,
                    'client_assertion': jwt_encoded,
                    'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
                    }
    query_params = requests.compat.urlencode(query_params)
    exchange = requests.post(
        settings.OPENID["token_endpoint"],
        headers=headers,
        data=query_params,
    ).json()

    # Get tokens and validate
    if not exchange.get("token_type") == 'Bearer':
        return HttpResponse("Forbidden", status=403, reason="Unsupported token type. Should be 'Bearer'.")
    access_token = exchange["access_token"]
    id_token = exchange["id_token"]

    # token is encrypted using a JWKS key
    jwks = requests.get(settings.OPENID['jwks_uri']).json()
    public_keys = {}
    for jwk in jwks['keys']:
        kid = jwk['kid']
        public_keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
    kid = jwt.get_unverified_header(id_token)['kid']
    key = public_keys[kid]
    try:
        id_token = jwt.decode(id_token, key, audience=settings.LOGIN_GOV['client_id'], algorithms=["RS256"])
    except jwt.ImmatureSignatureError:
        time.sleep(3)
        id_token = jwt.decode(id_token, key, audience=settings.LOGIN_GOV['client_id'], algorithms=["RS256"])

    # Authorization flow successful, get userinfo and sign in user
    userinfo_response = requests.get(settings.OPENID['userinfo_endpoint'],
        headers={'Authorization': f'Bearer {access_token}'}).json()
    unique_id = userinfo_response['sub']
    user_email = userinfo_response['email']
    verified = userinfo_response['email_verified']

    # need an authentication backend for getting the user by email address
    user = authenticate(email=user_email, verified=verified, unique_id=unique_id)
    if user is None:
        # Why are we None?
        # maybe email is not verified
        if not verified:
            # include a msg please
            messages.error(request, 'Your email is not validated on Login.gov', extra_tags='bg-danger-subtle text-emphasis')
            return render(request, 'registration/login.html')
        # Maybe this is a new user?
        elif not get_user_model().objects.filter(email=user_email).exists():
            request.session['email'] = user_email
            request.session['unique_id'] = unique_id
            return redirect('signup')
        else:
            # kick them back to the login screen
            messages.error(request, 'User not recognized', extra_tags='bg-danger-subtle text-emphasis')
            return render(request, 'registration/login.html')

    else:
        login(request, user)
        if not UserProfile.objects.filter(user=user).exists():
            profile = UserProfile(user=user, unique_id=unique_id)
            profile.save()
            return redirect('profile-create-edit')

    return redirect('home')


@require_http_methods(['GET'])
def howto_view(request):
    return render(request, 'evalbase/howto.html')

@require_http_methods(['GET', 'POST'])
def signup_view(request):
    if request.method == 'GET':
        form = SignupForm(initial={'email': request.session['email']})
        context = {'form': form}
        return render(request, 'evalbase/signup.html', context)

    elif request.method == 'POST':
        form_data = SignupForm(request.POST)
        if form_data.is_valid():
            user = User.objects.create_user(form_data.cleaned_data['username'],
                                     password='not-a-good-password',
                                     email=request.session['email'],
                                     first_name=form_data.cleaned_data['first_name'],
                                     last_name=form_data.cleaned_data['last_name'])
            login(request, user)
            return HttpResponseRedirect(reverse_lazy('profile-create-edit'))
        else:
            context = {'form': form_data}
            return render(request, 'evalbase/signup.html', context)


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
                        .filter(
                            Q(members=request.user)|Q(owner=request.user))
                        .filter(conference__complete=False)
                        .distinct()),
               'signatures': Signature.objects.filter(user=request.user)}
    return render(request, 'evalbase/profile_view.html', context)


@evalbase_login_required
@require_http_methods(['GET', 'POST'])
@never_cache
def profile_create_edit(request):
    if request.method == 'GET':
        cur_profile = UserProfile.objects.filter(user=request.user).first()
        if cur_profile:
            form = ProfileForm(instance=cur_profile,
                               initial={'user': request.user})
        else:
            form = ProfileForm(initial={'unique_id': request.session.pop('unique_id', None)})
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
        else:
            return render(request, 'evalbase/profile_form.html',
                          {'form': form})

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
    return render(request, 'evalbase/org-detail.html',
                  { 'object': kwargs['_org'],
                    'conf': kwargs['_conf'] })


@evalbase_login_required
@user_owns_org
@conference_is_open
@require_http_methods(['GET', 'POST'])
def org_edit(request, *args, **kwargs):

    org = kwargs['_org']
    members = org.members.all().exclude(id=request.user.id)
    all_tracks = org.conference.track_set.all()
    tracks = list(org.track_interest.all().values_list('shortname', flat=True))
    context = {'org': org,
               'members': members,
               'all_tracks': all_tracks,
               'tracks': tracks,
               }

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
            org.track_interest.clear()
            tracks = map(
                lambda tname: (Track.objects
                               .filter(conference=kwargs['_conf'])
                               .get(shortname=tname)),
                cleaned['track_interest'])
            org.track_interest.set(tracks)
        else:
            logging.error(form.errors)

        return HttpResponseRedirect(
            reverse_lazy('org-detail',
                         kwargs={'conf': kwargs['conf'],
                                 'org': kwargs['org']}))


@evalbase_login_required
@conference_is_open
@require_http_methods(['GET', 'POST'])
@never_cache
def org_create(request, *args, **kwargs):
    '''Create an organization.  This is signing up to participate in
    an evaluation.

    The complex thing about this form is that we ask registrants to indicate
    which tracks they would like to participate in.  So we need to get the
    list of tracks for this conference.

    In form validation, we create the random signup key URL.
    '''
    class _Form(forms.Form):
        existing_org = forms.ModelChoiceField(
            label='Existing organization',
            queryset=Organization.objects.filter(owner=request.user),
            required=False)
        shortname = forms.CharField(
            label='Organization ID - a short name for your organization (e.g. "nist")',
            max_length=15,
            required=False)
        longname = forms.CharField(
            label='Full name of your organization',
            max_length=50,
            required=False)
        track_interest = forms.ModelMultipleChoiceField(
            label='Which tracks are you interested in?',
            widget=forms.CheckboxSelectMultiple,
            queryset=(Track
                      .objects
                      .filter(conference=kwargs['_conf'])
                      .order_by('longname')))
        
        def clean(self):
            cleaned_data = super().clean()
            old_org = cleaned_data.get('existing_org')
            sname = cleaned_data.get('shortname')
            print(old_org, sname)
            if not old_org and not sname:
                raise ValidationError('You must either choose an existing organization or create a new one')
            if old_org and sname:
                raise ValidationError('You can either use an existing organization or create a new one')

            if (Organization.objects.filter(shortname=sname).exists()):
                raise ValidationError('Another organization is registered with this name.')

            return cleaned_data
        
    if request.method == 'GET':
        form = _Form()
        return render(request, 'evalbase/org-create.html',
                      { 'conf': kwargs['_conf'],
                        'have_orgs': Organization.objects.filter(owner=request.user).exists(),
                        'form': form })

    elif request.method == 'POST':
        form = _Form(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            if 'existing_org' in cleaned and cleaned['existing_org']:
                org = Organization.objects.get(shortname=cleaned['existing_org'])
            else:
                org = Organization(
                    shortname=cleaned['shortname'],
                    longname=cleaned['longname'],
                    contact_person=request.user,
                    owner=request.user,
                    passphrase=uuid.uuid4())
            org.save()
            org.conference.add(kwargs['_conf']),
            org.track_interest.set(cleaned['track_interest'])
            org.members.add(request.user)
            org.save()
            return HttpResponseRedirect(reverse_lazy('home'))
        else:
            return render(request, 'evalbase/org-create.html',
                          { 'conf': kwargs['_conf'],
                            'have_orgs': Organization.objects.filter(owner=request.user).exists(),
                            'form': form })


@evalbase_login_required
@require_http_methods(['GET', 'POST'])
def org_join(request, *args, **kwargs):
    '''Join an organization.  This view is triggered by someone
    using the special 'join-org' key for an organization.
    Orgs can be joined any time.
    '''

    org = Organization.objects.filter(passphrase=kwargs['key'])
    if not org:
        raise Http404('org not found, wtf')
    org = org[0]

    if request.method == 'GET':
        return render(request, 'evalbase/join.html',
                      { 'org': org,
                        'key': kwargs['key'] })

    elif request.method == 'POST':
        user = request.user
        org.members.add(user)
        send_mail(f'{org.shortname}: {user} joined',
                  f'This email is notifying you that user {user} ({user.first_name} {user.last_name} <{user.email}>) has joined the {org.shortname} ({org.longname}) team at Evalbase.',
                  'ian.soboroff@nist.gov',
                  [org.owner.email, org.contact_person.email],
                  fail_silently=False)
        return HttpResponseRedirect(reverse_lazy('home'))


# This is the main 'index.html' page view


@evalbase_login_required
@require_http_methods(['GET'])
def home_view(request, *args, **kwargs):
    '''The main page.  You can see what conferences you are participating
    in and which ones you can sign up to participate in.
    '''
    open_evals = (Conference.objects
                  .filter(open_signup=True)
                  .exclude(participants__members__pk = request.user.pk))
    my_orgs = (Organization.objects
               .filter(Q(members__pk=request.user.pk) | Q(owner__pk=request.user.pk), conference__complete=False)
               .distinct())
    complete = (Conference.objects
                .filter(complete=True)
                .filter(participants__members__pk=request.user.pk)
                .distinct())

    return render(request, 'evalbase/home.html',
                  { 'open_evals': open_evals,
                    'my_orgs': my_orgs,
                    'complete': complete })


# This view lists the tracks in a conference.  If the track is open
# for submissions, there is a link for submitting a run.  If the
# user has submitted runs, they are listed here.


@evalbase_login_required
@user_is_participant
@require_http_methods(['GET'])
def conf_tracks(request, *args, **kwargs):
    '''List the tracks in a conference.'''
    conf = Conference.objects.get(shortname=kwargs['conf'])
    agreements = conf.agreements.exclude(signature__user=request.user.pk)
    if agreements:
        return HttpResponseRedirect(reverse_lazy('sign-agreement',
                                     kwargs={'conf': conf,
                                             'agreement': agreements[0]}))
    tracks = (Track.objects
              .filter(conference=conf)
              .exclude(shortname='papers'))
    papers = (Track.objects
              .filter(conference=conf)
              .filter(shortname='papers')
              .first())
    tasks = (Task.objects
             .filter(track__conference=conf))
    orgs = (Organization.objects
            .filter(members__pk=request.user.pk)
            .filter(conference=conf))
    myruns = (Submission.objects
              .filter(task__track__conference=conf)
              .filter(org__in=orgs)
              .order_by('task', 'date'))
    appendices = None
    if conf.event_phase or conf.complete:
        appendices = (Appendix.objects
                      .filter(task__track__conference=conf)
                      .order_by('task__track__shortname', 'task__shortname'))
        appendices = { app.task.shortname: [ app ] for app in appendices }
 
    tracks_i_coordinate = set()
    for track in Track.objects.filter(coordinators__pk=request.user.pk):
        tracks_i_coordinate.add(track.shortname)

    task_dict = collections.defaultdict(list)
    for task in tasks:
        task_dict[task.track.shortname].append(task)

    return render(request, 'evalbase/tasks.html',
                  { 'tracks': tracks,
                    'papers': papers,
                    'tracks_i_coordinate': tracks_i_coordinate,
                    'tasks': task_dict,
                    'conf': conf,
                    'myruns': myruns,
                    'appendices': appendices,
                    'agreements': agreements })


# Users may not be able to submit runs before they have signed an
# agreement such as the TREC no-ads agreement.


@evalbase_login_required
@require_http_methods(['GET', 'POST'])
def sign_agreement(request, conf, agreement):
    agrobj = get_object_or_404(Agreement, name=agreement)
    template = 'evalbase/' + agrobj.template

    # Check if the form was already signed
    existing = Signature.objects.filter(user=request.user,
                                        agreement=agrobj)
    if existing:
        return HttpResponseRedirect(reverse('tracks', kwargs={'conf': conf}))

    if request.method == 'POST':
        form = AgreementForm(request.POST)
        if form.is_valid():
            sig = Signature(user=request.user,
                            agreement=agrobj,
                            sigtext=form.cleaned_data['sigtext'])
            sig.save()
            return HttpResponseRedirect(reverse('tracks', kwargs={'conf': conf}))
    else:
        form = AgreementForm()

    return render(request, template, { 'form': form })


@evalbase_login_required
@require_http_methods(['GET'])
def view_signature(request, agreement):
    sigs = Signature.objects.filter(user=request.user)
    agr = Agreement.objects.get(name=agreement)
    signature = get_object_or_404(sigs, agreement=agr)
    template = 'evalbase/' + signature.agreement.template

    return render(request, template, { 'sig': signature })


# Submitting, editing, and deleting runs.  This constructs a form based
# on the form fields defined for this track in the database, and handles
# its return.

@agreements_signed
@evalbase_login_required
@user_is_participant
@require_http_methods(['GET', 'POST'])
def submit_run(request, *args, **kwargs):
    '''This is the view for submitting a run to a task.  Each task has
    a custom set of metadata fields for the submission form, and those
    are described in the SubmitMetas class.  This form is what creates
    Submissions.
    '''
    template_name = 'evalbase/submit.html'

    conf = kwargs['conf']
    task = kwargs['task']
    try:
        conf = Conference.objects.get(shortname=conf)
        task = Task.objects.get(shortname=task, track__conference=conf)
        submitform = SubmitForm.objects.get(task=task)
    except Exception as e:
        raise Http404(e)

    is_coord = (Track.objects
                .filter(conference=conf)
                .filter(task=task)
                .filter(coordinators__pk=request.user.pk)
                .exists())

    if not (request.user.is_staff or is_coord or task.task_open):
        raise Http404('Task is not open')

    context = {}
    context['conf'] = conf
    context['task'] = task
    context['track'] = task.track
    context['form'] = submitform
    context['user'] = request.user
    context['orgs'] = (Organization.objects
                       .filter(members__pk=request.user.pk)
                       .filter(conference=conf))
    context['mode'] = 'submit'
    context['testing'] = submitform.testing
    context['open'] = task.task_open

    form_class = SubmitFormForm.get_form_class(context)

    if request.method == 'GET':
        sff = form_class()
        context['gen_form'] = sff
        return render(request, template_name, context=context)

    elif request.method == 'POST':
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            stuff = form.cleaned_data
            org = (Organization.objects
                   .filter(shortname=stuff['org'])
                   .filter(members__pk=request.user.pk)
                   .filter(conference=context['conf']))[0]
            
            if context['track'].shortname == 'papers':
                num_papers = (Submission.objects
                              .filter(task__track__conference=context['conf'])
                              .filter(task=context['task'])
                              .filter(org=org)
                              .count())
                runtag = f'{org.shortname}-{context["task"].shortname}-{num_papers + 1}'
            else:
                runtag = urllib.parse.quote(stuff['runtag'], safe='')

            sub = Submission(task=context['task'],
                             org = org,
                             submitted_by=request.user,
                             runtag=runtag,
                             file=request.FILES.get('runfile', None),
                             is_validated=Submission.ValidationState.WAITING,
                             has_evaluation=False
                             )

            sub.save()

            custom_fields = SubmitFormField.objects.filter(submit_form=context['form'])
            for field in custom_fields:
                if isinstance(stuff[field.meta_key], QuerySet):
                    for thing in stuff[field.meta_key]:
                        key = field.meta_key
                        value = thing.shortname
                        smeta = SubmitMeta(submission=sub,
                                           form_field=field,
                                           key=key,
                                           value=value)
                        smeta.save()
                else:
                    smeta = SubmitMeta(submission=sub, 
                                       form_field=field,
                                       key=field.meta_key,
                                       value=stuff[field.meta_key])
                    smeta.save()

            if task.checker_file and task.checker_file != 'NONE':
                run_check_script(sub, task.checker_file)

            return HttpResponseRedirect(reverse('tracks',
                                            kwargs={'conf': conf}))
        else:
            context['gen_form'] = form
            return render(request, 'evalbase/submit.html', context=context)


def safe_parse_list(s):
    '''Database entries for checkbox values are lists, in Python format.
    Turn them into real lists of values, without using eval or
    ast.literal_eval'''
    import ast
    tree = ast.parse(s, mode='eval')
    if isinstance(tree.body, ast.List):
        vals = []
        for elt in tree.body.elts:
            if isinstance(elt, ast.Constant):
                vals.append(elt.value)
            else:
                return None
        return vals
    else:
        return None


@evalbase_login_required
@task_is_open
@user_may_edit_submission
@require_http_methods(['GET', 'POST'])
def edit_submission(request, *args, **kwargs):
    '''A form for editing the metadata for a submission.'''

    template_name = 'evalbase/edit.html'

    context = {}
    conf = kwargs['_conf']
    task = kwargs['_task']
    submitform = SubmitForm.objects.get(task=task)

    context['conf'] = conf
    context['task'] = task
    context['track'] = task.track
    context['form'] = submitform
    context['user'] = request.user
    context['orgs'] = (Organization.objects
                       .filter(members__pk=request.user.pk)
                       .filter(conference=conf))
    context['mode'] = 'edit'
    form_class = SubmitFormForm.get_form_class(context)

    run_list = (Submission.objects
                .filter(submitted_by=request.user)
                .filter(task__track__conference__shortname=kwargs['conf'])
                .filter(runtag=kwargs['runtag']))
    if run_list:
        run = run_list[0]
    else:
        raise PermissionDenied("You don't have access to this run.")

    form_info = {'conf': conf,
                 'task': run.task,
                 'org': run.org,
                 'user': run.submitted_by,
                 'email': run.submitted_by.email,
                 'runtag': run.runtag,
                 'runfile': run.file}
    other_infos = SubmitMeta.objects.filter(submission=run)
    for run_meta in other_infos:
        info_field = SubmitFormField.objects.filter(meta_key=run_meta.key)[0]
        if info_field.question_type == SubmitFormField.QuestionType.CHECKBOX:
            form_info[run_meta.key] = safe_parse_list(run_meta.value)
        else:
            form_info[run_meta.key] = run_meta.value

    if request.method == 'GET':
        sff = form_class(form_info)
        context['gen_form'] = sff
        return render(request, template_name, context=context)

    elif request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            stuff = form.cleaned_data
            run = (Submission.objects
                   .filter(submitted_by_id=request.user.id)
                   .filter(task__track__conference__shortname=kwargs['conf'])
                   .filter(runtag=run.runtag)[0])
            org = (Organization.objects
                   .filter(members__pk=request.user.pk)
                   .filter(shortname=stuff['org'])
                   .filter(conference__shortname=kwargs['conf']))
            if not org:
                raise Http404()

            run.org = org[0]
            run.save()

            custom_fields = SubmitFormField.objects.filter(submit_form=context['form'])
            for field in custom_fields:
                original = (SubmitMeta.objects
                            .filter(key=field.meta_key)
                            .filter(submission_id=run.id)[0])
                original.value = stuff[field.meta_key]
                original.save()


            return HttpResponseRedirect(reverse_lazy('run',
                                                     kwargs={'conf': conf,
                                                             'task': task.shortname,
                                                             'runtag': run.runtag}))
        else:
            context['gen_form'] = form
            return render(request, template_name, context=context)


@evalbase_login_required
@user_may_edit_submission
@check_conf_and_task
@task_is_open
@require_http_methods(['GET', 'POST'])
def delete_submission(request, *args, **kwargs):
    template = 'evalbase/submission_confirm_delete.html'
    run = kwargs['_sub']

    if request.method == 'GET':
        return render(request, template, context={'object': run})

    elif request.method == 'POST':
        run.delete()
        # This should be handled by django_cleanup now.
        #run_dir =  (Path(settings.MEDIA_ROOT) / run.file.name).parent
        #shutil.rmtree(run_dir, ignore_errors=True)
        return HttpResponseRedirect(
            reverse_lazy('tracks', kwargs={'conf': kwargs['conf']}))


@evalbase_login_required
@check_conf_and_task
@require_http_methods(['GET'])
def view_submission(request, *args, **kwargs):
    '''View a submission.'''
    template_name = 'evalbase/run.html'

    context = {}
    conf = get_object_or_404(Conference, shortname=kwargs['conf'])
    run = Submission.objects.filter(runtag=kwargs['runtag']).filter(task__shortname=kwargs['task'])[0]

    is_coord =             run.task.track.coordinators.filter(pk=request.user.pk)
    if not (request.user.is_staff or
            request.user == run.submitted_by or
            request.user == run.org.owner or
            kwargs['_conf'].event_phase or
            is_coord):
        result = []
        if not request.user.is_staff:
            result.append('staff')
        if not request.user == run.submitted_by:
            result.append('submitter')
        if not request.user == run.org.owner:
            result.append('org lead')
        if not is_coord:
            result.append('track coordinator')
        raise PermissionDenied(f'User is not one of [{", ".join(result)}]')

    context['submission'] = run
    context['metas'] = (SubmitMeta.objects
                        .filter(submission_id=run.id))
    context['may_edit'] = (request.user == run.submitted_by or
                           request.user == run.org.owner)
    field_descs = {}
    for meta in context['metas']:
        field_descs[meta.key] = meta.form_field.question
    context['fields'] = field_descs
    context["file"] = run.file

    return render(request, template_name, context)


@evalbase_login_required
@check_conf_and_task
@require_http_methods(['GET'])
def view_eval(request, *args, **kwargs):
    '''View an evaluation score output.'''
    run = Submission.objects.filter(runtag=kwargs['runtag']).filter(task__shortname=kwargs['task'])[0]

    is_coord = run.task.track.coordinators.filter(pk=request.user.pk)
    if not (request.user.is_staff or
            request.user == run.submitted_by or
            request.user == run.org.owner or
            kwargs['_conf'].event_phase or
            is_coord):
        result = []
        if not request.user.is_staff:
            result.append('staff')
        if not request.user == run.submitted_by:
            result.append('submitter')
        if not request.user == run.org.owner:
            result.append('org lead')
        if not is_coord:
            result.append('track coordinator')
        raise PermissionDenied(f'User is not one of [{", ".join(result)}]')

    eval = run.evaluation_set.filter(name=kwargs['eval'])[0]
    with open(eval.filename.path, 'r') as eval_fp:
        eval_txt = eval_fp.read()
    return HttpResponse(eval_txt,
                        headers={'Content-Type': 'text/plain'})


@evalbase_login_required
@check_conf_and_task
@require_http_methods(['GET'])
def download_all_my_evals(request, *args, **kwargs):
    task = kwargs['_task']

    my_evals = (Evaluation.objects
                .filter(submission__task=task)
                .filter(submission__submitted_by=request.user))
    
    my_org_evals = (Evaluation.objects
                    .filter(submission__task=task)
                    .filter(submission__submitted_by__member_of__owner=request.user))
    
    evals = my_evals.union(my_org_evals)
    if not evals.exists():
        raise Http404

    with tempfile.SpooledTemporaryFile() as tmp:
        with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
            for e in evals:
                zipf.write(e.filename.path, 
                           arcname=f'{e.submission.runtag}.{e.name}')
            for s in StatsFile.objects.filter(task=task):
                zipf.write(s.filename.path, 
                           arcname=f'{s.task.shortname}.{s.name}')
            zipf.close()

        tmp.flush()
        tmp.seek(0)
        data = tmp.read()
        return HttpResponse(content=data,
                            headers={'Content-Type': 'application/zip',
                                     'Content-Disposition': 'attachment; filename=evals.zip'})

@evalbase_login_required
@check_conf_and_task
@conference_in_event_phase
@require_http_methods(['GET'])
def show_appendix(request, *args, **kwargs):
    template_name = 'evalbase/appendix.html'
    if 'name' in kwargs:
        appendix = get_object_or_404(Appendix, name=kwargs['name'], task=kwargs['_task'])
    else:
        appendix = Appendix.objects.filter(task=kwargs['_task'])[0]
        
    evals = Evaluation.objects.filter(submission__task=kwargs['_task'])
    if 'name' in kwargs:
        evals = evals.filter(name=kwargs['name'])
    if appendix.queryset_field and appendix.queryset_qtype and appendix.queryset_target:
        filter = appendix.queryset_field + '__' + appendix.queryset_qtype
        evals = evals.filter(**{filter: appendix.queryset_target})
    means = collections.defaultdict(dict)
    scores = infinite_defaultdict()
    runs = {}
    if appendix.measures == "all":
        measures = {}
    else:
        measures = { m: 0 for m in appendix.measures }
        
    for eval in evals:
        runs[eval.submission.runtag] = eval.submission.org
        with open(eval.filename.path, 'r') as eval_file:
            for line in eval_file:
                # assumes a trec_eval format file
                fields = line.strip().split()
                measure = fields[appendix.measure_name_field]
                topic = fields[appendix.topic_field]
                score = fields[appendix.score_field]
                if measure == 'runid':
                    continue
                if topic == appendix.average_topic:
                    if appendix.measures == 'all':
                        means[eval.submission.runtag][measure] = score
                        measures[measure] = 1
                    elif measure in measures:
                        means[eval.submission.runtag][measure] = score
                else:
                    if appendix.measures == 'all':
                        scores[eval.submission.runtag][measure][topic] = score
                        measures[measure] = 1
                    elif measure in measures:
                        scores[eval.submission.runtag][measure][topic] = score
            for measure in measures:
                if measure not in means[eval.submission.runtag]:
                    sum_score = sum([float(s) for s in scores[eval.submission.runtag][measure].values()])
                    avg = sum_score / len(scores[eval.submission.runtag][measure])
                    means[eval.submission.runtag][measure] = f'{avg:6.4f}'
    if appendix.sort_column and appendix.sort_column in measures:
        sorted_keys = sorted(means, 
                             key=lambda x: means[x][appendix.sort_column], 
                             reverse=True)
        tmp_dict = { runtag: means[runtag] for runtag in sorted_keys }
        means = tmp_dict
        
    context = {}
    context['scores'] = dict(means)
    context['runs'] = runs
    context['measures'] = measures.keys()
    context['task'] = kwargs['_task']
    context['conf'] = kwargs['_conf']
    context['name'] = appendix.name
    return render(request, template_name, context=context)
    

@evalbase_login_required
@check_conf_and_task
@require_http_methods(['GET'])
def download_submission_file(request, *args, **kwargs):
    '''Get the actual submitted run.'''
    run = Submission.objects.filter(runtag=kwargs['runtag']).filter(task__shortname=kwargs['task'])[0]

    is_coord = run.task.track.coordinators.filter(pk=request.user.pk)
    if not (request.user.is_staff or
            request.user == run.submitted_by or
            request.user == run.org.owner or
            is_coord):
        result = []
        if not request.user.is_staff:
            result.append('staff')
        if not request.user == run.submitted_by:
            result.append('submitter')
        if not request.user == run.org.owner:
            result.append('org lead')
        if not is_coord:
            result.append('track coordinator')
        raise PermissionDenied(f'User is not one of [{", ".join(result)}]')

    with open(run.file.path, 'rb') as run_fp:
        run_content = run_fp.read()
    return HttpResponse(run_content,
                        headers={'Content-Type': 'application/octet-stream',
                                 'Content-Disposition': f'inline; filename="{run.runtag}'})


@evalbase_login_required
@user_is_track_coordinator
@check_conf_and_task
@require_http_methods(['GET'])
def list_submissions(request, *args, **kwargs):
    '''List all submissions to a task.'''
    template_name = 'evalbase/all_runs.html'

    runs = (Submission.objects
        .filter(task=kwargs['_task'])
        .filter(task__track__conference=kwargs['_conf']))

    run_meta = collections.defaultdict(dict)
    metas = (SubmitMeta.objects
        .filter(submission__task__track__conference=kwargs['_conf'])
        .filter(submission__task=kwargs['_task']))
    for m in metas:
        run_meta[m.submission.runtag][m.key] = m.value

    return render(request, template_name, {
        'conf': kwargs['_conf'],
        'runs': runs,
        'metas': run_meta})

def _user_is_staff(user):
    return user.is_staff

@evalbase_login_required
@user_is_track_coordinator
@require_http_methods(['GET'])
def org_signups_per_track(request, *args, **kwargs):
    '''List, for all tracks in this conference, how many orgs indicated an interest.
    '''
    template_name = 'evalbase/org_signups_per_track.html'

    results = {}
    conf = get_object_or_404(Conference, shortname=kwargs['conf'])
    if 'track' in kwargs:
        tracks = Track.objects.filter(conference=conf, shortname=kwargs['track'])
    else:
        tracks = Track.objects.filter(conference=conf)
    for track in tracks:
        results[track.shortname] = []
        for org in track.organization_set.all():
            orgdict = { 'longname': org.longname,
                        'shortname': org.shortname,
                        'contact_person': f'{org.contact_person.first_name} {org.contact_person.last_name}',
                        'contact_email': org.contact_person.email,
            }
            results[track.shortname].append(orgdict)

    return render(request, template_name, {
        'conf': conf,
        'results': results,
        'results_json': results,
        'open': True if len(results) == 1 else False
    })
