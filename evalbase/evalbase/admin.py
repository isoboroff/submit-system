from django.contrib import admin
from .models import *

admin.site.register(UserProfile)

class TaskInline(admin.TabularInline):
    model = Task
    list_display = ('shortname', 'longname', 'required', 'has_file', 'open')
    show_change_link = True

@admin.register(Conference)
class ConferenxeAdmin(admin.ModelAdmin):
    inlines = [TaskInline]


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    readonly_fields = [ 'passphrase' ]


admin.site.register(Agreement)    


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


