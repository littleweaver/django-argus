from django.conf.urls import patterns, url
from django.views.generic import TemplateView

from argus.models import Member, Recipient, Category, Group
from argus.views import (MemberDetailView, GroupListView, GroupDetailView,
                         GroupCreateView, GroupUpdateView, GroupLoginView,
                         GroupChangePasswordView, GroupPasswordResetTokenView,
                         GroupPasswordResetConfirmView, GroupEmailConfirmView,
                         GroupLogoutView, GroupRelatedCreateView,
                         RecipientDetailView, ExpenseCreateView,
                         CategoryDetailView, GroupRelatedUpdateView)


urlpatterns = patterns('',
    url(r'^$',
        GroupListView.as_view(),
        name='argus_group_list'),
    url(r'^create/',
        GroupCreateView.as_view(),
        name='argus_group_create'),
    url(r'^logout/$',
        GroupLogoutView.as_view(),
        name='argus_group_logout'),

    url(r'^(?P<slug>{})/$'.format(Group.SLUG_REGEX),
        GroupDetailView.as_view(),
        name='argus_group_detail'),
    url(r'^(?P<slug>{})/edit/$'.format(Group.SLUG_REGEX),
        GroupUpdateView.as_view(),
        name='argus_group_update'),
    url(r'^(?P<slug>{})/edit/change_password/$'.format(Group.SLUG_REGEX),
        GroupChangePasswordView.as_view(),
        name='argus_group_change_password'),
    url(r'^(?P<slug>{})/login/$'.format(Group.SLUG_REGEX),
        GroupLoginView.as_view(),
        name='argus_group_login'),

    url(r'^(?P<slug>{})/password_reset/$'.format(Group.SLUG_REGEX),
        GroupPasswordResetTokenView.as_view(),
        name="argus_group_password_reset"),
    url(r'^(?P<slug>{})/password_reset/(?P<token>[0-9A-Za-z]{{1,13}}-[0-9A-Za-z]{{1,20}})$'.format(Group.SLUG_REGEX),
        GroupPasswordResetConfirmView.as_view(),
        name="argus_group_password_reset_confirm"),
    url(r'^(?P<slug>{})/password_reset/done/$'.format(Group.SLUG_REGEX),
        TemplateView.as_view(template_name="argus/group_password_reset_done.html"),
        name="argus_group_password_reset_done"),

    url(r'^(?P<slug>{})/confirm_email/(?P<token>[0-9A-Za-z]{{1,13}}-[0-9A-Za-z]{{1,20}})$'.format(Group.SLUG_REGEX),
        GroupEmailConfirmView.as_view(),
        name="argus_group_email_confirm"),

    url(r'^(?P<group_slug>{})/m/add/$'.format(Group.SLUG_REGEX),
        GroupRelatedCreateView.as_view(template_name="argus/member_form.html",
                                       context_object_name="member",
                                       model=Member),
        name='argus_member_create'),
    url(r'^(?P<group_slug>{})/m/(?P<pk>\d+)/$'.format(Group.SLUG_REGEX),
        MemberDetailView.as_view(),
        name='argus_member_detail'),
    url(r'^(?P<group_slug>{})/m/(?P<pk>\d+)/edit/$'.format(Group.SLUG_REGEX),
        GroupRelatedUpdateView.as_view(template_name="argus/member_form.html",
                                       context_object_name="member",
                                       model=Member),
        name='argus_member_update'),

    url(r'^(?P<group_slug>{})/r/add/$'.format(Group.SLUG_REGEX),
        GroupRelatedCreateView.as_view(template_name="argus/recipient_form.html",
                                       context_object_name="recipient",
                                       model=Recipient),
        name='argus_recipient_create'),
    url(r'^(?P<group_slug>{})/r/(?P<pk>\d+)/$'.format(Group.SLUG_REGEX),
        RecipientDetailView.as_view(),
        name='argus_recipient_detail'),
    url(r'^(?P<group_slug>{})/r/(?P<pk>\d+)/edit/$'.format(Group.SLUG_REGEX),
        GroupRelatedUpdateView.as_view(template_name="argus/recipient_form.html",
                                       context_object_name="recipient",
                                       model=Recipient),
        name='argus_recipient_update'),

    url(r'^(?P<group_slug>{})/c/add/$'.format(Group.SLUG_REGEX),
        GroupRelatedCreateView.as_view(template_name="argus/category_form.html",
                                       context_object_name="category",
                                       model=Category),
        name='argus_category_create'),
    url(r'^(?P<group_slug>{})/c/(?P<pk>\d+)/$'.format(Group.SLUG_REGEX),
        CategoryDetailView.as_view(),
        name='argus_category_detail'),
    url(r'^(?P<group_slug>{})/c/(?P<pk>\d+)/edit/$'.format(Group.SLUG_REGEX),
        GroupRelatedUpdateView.as_view(template_name="argus/category_form.html",
                                       context_object_name="category",
                                       model=Category),
        name='argus_category_update'),

    url(r'^(?P<group_slug>{})/expense/$'.format(Group.SLUG_REGEX),
        ExpenseCreateView.as_view(),
        name='argus_expense_create'),
)
