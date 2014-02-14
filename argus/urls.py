from django.conf.urls import patterns, url

from argus.views import (MemberDetailView, GroupListView, GroupDetailView,
						 GroupCreateView)


urlpatterns = patterns('',
	url(r'^$',
		GroupListView.as_view(),
		name='argus_group_list'),
	url(r'^create/',
		GroupCreateView.as_view(),
		name='argus_group_create'),
	url(r'^(?P<group_slug>[\w-]+)/$',
		GroupDetailView.as_view(),
		name='argus_group_detail'),
	url(r'^(?P<group_slug>[\w-]+)/m/(?P<pk>\d+)/$',
		MemberDetailView.as_view(),
		name='argus_member_detail'),
)
