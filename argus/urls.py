from django.conf.urls import patterns, url
from django.views.generic import TemplateView

from argus.views import (MemberDetailView, GroupListView, GroupDetailView,
						 GroupCreateView, GroupUpdateView, GroupLoginView,
						 GroupChangePasswordView, GroupPasswordResetTokenView,
						 GroupPasswordResetConfirmView, GroupEmailConfirmView,
						 GroupLogoutView)


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

	url(r'^(?P<slug>[\w-]+)/$',
		GroupDetailView.as_view(),
		name='argus_group_detail'),
	url(r'^(?P<slug>[\w-]+)/edit/$',
		GroupUpdateView.as_view(),
		name='argus_group_update'),
	url(r'^(?P<slug>[\w-]+)/edit/change_password/$',
		GroupChangePasswordView.as_view(),
		name='argus_group_change_password'),
	url(r'^(?P<slug>[\w-]+)/login/$',
		GroupLoginView.as_view(),
		name='argus_group_login'),

	url(r'^(?P<slug>[\w-]+)/password_reset/$',
		GroupPasswordResetTokenView.as_view(),
		name="argus_group_password_reset"),
	url(r'^(?P<slug>[\w-]+)/password_reset/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})$',
		GroupPasswordResetConfirmView.as_view(),
		name="argus_group_password_reset_confirm"),
	url(r'^(?P<slug>[\w-]+)/password_reset/done/$',
		TemplateView.as_view(template_name="argus/group_password_reset_done.html"),
		name="argus_group_password_reset_done"),

	url(r'^(?P<slug>[\w-]+)/confirm_email/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})$',
		GroupEmailConfirmView.as_view(),
		name="argus_group_email_confirm"),

	url(r'^(?P<group_slug>[\w-]+)/m/(?P<pk>\d+)/$',
		MemberDetailView.as_view(),
		name='argus_member_detail'),
)
