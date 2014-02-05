from django.conf.urls import patterns, url

from argus.views import MemberView


urlpatterns = patterns('',
	url(r'^(?P<group_slug>[\w-]+)/m/(?P<pk>\d+)',
		MemberView.as_view(),
		name='argus_member_detail'),
)
