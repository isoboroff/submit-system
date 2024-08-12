from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django import forms
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
    list_filter = ['user__member_of__conference__shortname', 'added_to_slack']
    ordering = ['-created_at', 'user__username']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
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


class SubmitFormFieldInline(admin.TabularInline):
    model = SubmitFormField
    extra = 3
    list_display = ('sequence', 'question', 'meta_key')

@admin.register(SubmitForm)
class SubmitFormAdmin(admin.ModelAdmin):
    inlines = [ SubmitFormFieldInline ]
    actions = ["replicate_form"]
    save_as = True
    view_on_site = True

    class TaskChoiceField(forms.ModelChoiceField):
        def label_from_instance(self, obj):
            return f'{obj.track.shortname}: {obj.longname}'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'task':
            return SubmitFormAdmin.TaskChoiceField(queryset=Task.objects.all())
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['shortname', 'longname', 'track_short', 'required', 'task_open', 'deadline', 'checker_file']

    @admin.display(ordering=Lower('shortname'))
    def track_short(self, obj):
        return obj.track.shortname

    @admin.display
    def submit_form(self, obj):
        return obj.submit_form

@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ['shortname', 'conference']
    list_filter = ['conference']
    filter_horizontal = ['coordinators']

class TrackInline(admin.TabularInline):
    model = Track
    list_display = ('shortname', 'longname', 'required', 'has_file', 'open')
    show_change_link = True

@admin.register(Conference)
class ConferenceAdmin(admin.ModelAdmin):
    inlines = [TrackInline]
    actions = [csvexport]


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['ci_shortname', 'owner_name', 'conference']
    list_filter = ['conference']
    readonly_fields = [ 'passphrase' ]
    filter_horizontal = [ 'members' ]
    search_fields = ['shortname', 'owner__first_name', 'owner__last_name', 'owner__email']
    actions = [csvexport]

    @admin.display(ordering=Lower('shortname'))
    def ci_shortname(self, obj):
        return obj.shortname

    @admin.display(ordering='owner__last_name')
    def owner_name(self, obj):
        return f'{obj.owner.first_name} {obj.owner.last_name} ({obj.owner.email})'

class SignatureInline(admin.TabularInline):
    model = Signature

class AgreementAdmin(admin.ModelAdmin):
    inlines = [SignatureInline]
    search_fields = ['signature__user']

admin.site.register(Agreement, AgreementAdmin)


class SubmitMetaInline(admin.TabularInline):
    model = SubmitMeta


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    inlines = [SubmitMetaInline]
    list_display = ['runtag', 'task', 'org', 'date', 'is_validated']
    readonly_fields = ['date']
    list_filter = ['task']
    search_fields = ['runtag']

    def delete_queryset(self, request, queryset):
        for submission in queryset:
            submission.delete()
