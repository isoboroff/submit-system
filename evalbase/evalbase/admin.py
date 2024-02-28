from django.contrib import admin
from .models import *
from django.contrib.auth.models import User, Group
from pinax.announcements.models import Announcement, Dismissal

# These are required because we are using adminplus.  If we revert to
# stock admin, these will cause exceptions as they were all
# autodiscovered.
admin.site.register(User)
admin.site.register(Group)
admin.site.register(Announcement)
admin.site.register(Dismissal)

admin.site.register(UserProfile)

class TaskInline(admin.TabularInline):
    model = Task
    list_display = ('shortname', 'longname', 'required', 'has_file', 'open')
    show_change_link = True

class ConferenceAdmin(admin.ModelAdmin):
    inlines = [TaskInline]
admin.site.register(Conference)


class OrganizationAdmin(admin.ModelAdmin):
    readonly_fields = [ 'passphrase' ]
admin.site.register(Organization)

class SignatureInline(admin.TabularInline):
    model = Signature

class AgreementAdmin(admin.ModelAdmin):
    inlines = [SignatureInline]

admin.site.register(Agreement, AgreementAdmin)


class SubmitFormFieldInline(admin.TabularInline):
    model = SubmitFormField
    extra = 3
    list_display = ('sequence', 'question', 'meta_key')

class SubmitFormAdmin(admin.ModelAdmin):
    inlines = [SubmitFormFieldInline]
    list_filter = ('task__conference', 'task__shortname')
admin.site.register(SubmitForm)

class SubmitMetaInline(admin.TabularInline):
    model = SubmitMeta

class SubmissionAdmin(admin.ModelAdmin):
    inlines = [SubmitMetaInline]
admin.site.register(Submission)


