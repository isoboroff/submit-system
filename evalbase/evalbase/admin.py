from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from csvexport.actions import csvexport
from .models import *

class CustomUserAdmin(UserAdmin):
    model = User
    actions = [csvexport]
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

admin.site.register(UserProfile)

class TaskInline(admin.TabularInline):
    model = Task
    list_display = ('shortname', 'longname', 'required', 'has_file', 'open')
    show_change_link = True

@admin.register(Conference)
class ConferenceAdmin(admin.ModelAdmin):
    inlines = [TaskInline]
    actions = [csvexport]


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    readonly_fields = [ 'passphrase' ]
    actions = [csvexport]

class SignatureInline(admin.TabularInline):
    model = Signature

class AgreementAdmin(admin.ModelAdmin):
    inlines = [SignatureInline]
        
admin.site.register(Agreement, AgreementAdmin)


class SubmitFormFieldInline(admin.TabularInline):
    model = SubmitFormField
    extra = 3
    list_display = ('sequence', 'question', 'meta_key')


@admin.register(SubmitForm)
class SubmitFormAdmin(admin.ModelAdmin):
    inlines = [SubmitFormFieldInline]
    list_filter = ('task__conference', 'task__shortname')


class SubmitMetaInline(admin.TabularInline):
    model = SubmitMeta


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    inlines = [SubmitMetaInline]


