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
from django.views.generic.base import TemplateView
from django.contrib.auth import views as auth_views
from evalbase import views

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),

    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('signup/', views.SignUp.as_view(template_name='evalbase/signup.html'), name='signup'),

    path('profile/', views.ProfileDetail.as_view(), name='profile'),
    path('profile/create', views.ProfileCreate.as_view(), name='profile-create'),
    path('profile/edit', views.ProfileEdit.as_view(), name='profile-edit'),

    path('org/list', views.OrganizationList.as_view(), name='my-orgs'),
    path('org/edit/<name>', views.OrganizationEdit.as_view(), name='org-edit'),
    path('org/join/<key>', views.OrganizationJoin.as_view(), name='org-join'),
    path('org/create/<str:conf>', views.OrganizationCreate.as_view(), name='org-create'),
    path('org/<str:shortname>', views.OrganizationDetail.as_view(), name='org-detail'),

    path('conf/<str:conf>', views.ConferenceTasks.as_view(), name='tasks'),
    path('conf/agreements/<str:conf>', views.ListAgreements.as_view(), name='agree'),
    path('conf/<str:conf>/<str:task>/submit', views.SubmitRun.as_view(), name='submit'),
    path('conf/<str:conf>/<str:task>/<int:id>/edit', views.EditSubmission.as_view(), name='edit-task'),

    path('run/<str:conf>/<str:task>/<str:runtag>', views.Submissions.as_view(), name='run'),
    path('run/<str:conf>/<str:task>/<str:runtag>/download', views.download, name='run-download'),
    
    path('', views.HomeView.as_view(template_name='evalbase/home.html'), name='home'),
]
