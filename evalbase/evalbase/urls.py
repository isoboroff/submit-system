"""evalbase URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import TemplateView
from django.contrib.auth import views as auth_views
from evalbase import views
from evalbase import settings

urlpatterns = ([
    path('admin/', admin.site.urls),
    # path('accounts/', include('django.contrib.auth.urls')),

    path(r"announcements/", include("pinax.announcements.urls", namespace="pinax_announcements")),

    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),

    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('signup/', views.signup_view, name='signup'),

    path('profile/', views.profile_view, name='profile'),
    path('profile/edit', views.profile_create_edit, name='profile-create-edit'),

    path('org/<str:conf>/<str:org>/edit', views.org_edit, name='org-edit'),
    path('org/join/<str:key>', views.org_join, name='org-join'),
    path('org/<str:conf>/create', views.org_create, name='org-create'),
    path('org/<str:conf>/<str:org>', views.org_view, name='org-detail'),

    path('conf/<str:conf>', views.conf_tracks, name='tracks'),
    path('agreements/<str:conf>/<str:agreement>/sign',
         views.sign_agreement, name='sign-agreement'),
    path('agreements/<str:agreement>',
         views.view_signature, name='sign-detail'),

    path('conf/<str:conf>/<str:task>/submit', views.submit_run,
         name='submit'),
    path('conf/<str:conf>/<str:task>/list', views.list_submissions,
         name='task_submissions'),
    path('conf/<str:conf>/<str:task>/evals', views.download_all_my_evals, name='evals-zip'),
    path('conf/<str:conf>/<str:task>/appendix', views.show_appendix, name='appendix'),
    path('conf/<str:conf>/<str:task>/appendix/<str:name>', views.show_appendix, name='appendix'),    
    path('run/<str:conf>/<str:task>/<str:runtag>', views.view_submission, name='run'),
    path('run/<str:conf>/<str:task>/<str:runtag>/run', views.download_submission_file, name='runfile'),
    path('run/<str:conf>/<str:task>/<str:runtag>/delete', views.delete_submission, name='run-delete'),
    path('conf/<str:conf>/<str:task>/<str:runtag>/edit', views.edit_submission, name='edit-task'),
    path('run/<str:conf>/<str:task>/<str:runtag>/<str:eval>', views.view_eval, name='eval'),
    path('howto/', views.howto_view, name="howto"),
    path('', views.home_view, name='home'),

    path('conf/<str:conf>/signups_per_track', views.org_signups_per_track,
         name='signups_per_track'),
    path('conf/<str:conf>/<str:track>/signups', views.org_signups_per_track,
         name='track_signups')
]
# + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
#+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
)

if settings.DEBUG:
     urlpatterns += staticfiles_urlpatterns()
