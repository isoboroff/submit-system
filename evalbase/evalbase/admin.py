from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.db.models.functions import Lower
from csvexport.actions import csvexport
from .models import *

class CustomUserAdmin(UserAdmin):
    model = User
    actions = [csvexport]
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'added_to_slack', 'first_name', 'last_name', 'created_at']
    list_editable = ['added_to_slack']
    date_hierarchy = 'created_at'
    list_filter = ['user__member_of__conference__shortname']
    ordering = ['-created_at', 'user__username']
    actions = ['mark_slacked', 'clear_slacked', csvexport]

    @admin.display(description='username')
    def username(self, obj):
        return obj.user.username

    @admin.display(description='email')
    def email(self, obj):
        return obj.user.email

    @admin.display(description='first_name')
    def first_name(self, obj):
        return obj.user.first_name

    @admin.display(description='last_name')
    def last_name(self, obj):
        return obj.user.last_name

    @admin.display(description='created_at')
    def created_at(self, obj):
        return obj.user.created_at

    @admin.action(description='Mark as added to Slack')
    def mark_slacked(modeladmin, request, queryset):
        queryset.update(added_to_slack=True)

    @admin.action(description='Clear added to Slack')
    def clear_slacked(modeladmin, request, queryset):
        queryset.update(added_to_slack=False)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['shortname', 'conference']
    list_filter = ['conference']
    filter_horizontal = ['coordinators']

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
    list_display = ['ci_shortname', 'owner', 'conference']
    list_filter = ['conference']
    readonly_fields = [ 'passphrase' ]
    actions = [csvexport]

    @admin.display(ordering=Lower('shortname'))
    def ci_shortname(self, obj):
        return obj.shortname

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


