import datetime
import hashlib

from django.db import models
from django.db.models import Q
from django.http import Http404
from django.views.generic import DetailView, ListView, RedirectView

from argus.models import Member, Group, Share


class GroupCreateView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        created = False
        while True:
            slug = hashlib.sha1(datetime.datetime.now().isoformat()).hexdigest()[:6]
            q = (Q(auto_slug=slug) |
                 Q(custom_slug=slug))
            if not Group.objects.filter(q).exists():
                group = Group.objects.create(auto_slug=slug)
                break
        return group.get_absolute_url()


class GroupListView(ListView):
    model = Group
    template_name = 'argus/group_list.html'
    context_object_name = 'groups'


class GroupDetailView(DetailView):
    model = Group
    template_name = 'argus/group_detail.html'
    context_object_name = 'group'

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        queryset = queryset.filter(Q(auto_slug=self.kwargs['group_slug']) |
                                   Q(custom_slug=self.kwargs['group_slug']))
        try:
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404

        return obj

    def get_queryset(self):
        qs = super(GroupDetailView, self).get_queryset()
        return qs.prefetch_related('members', 'recipients', 'categories')


class MemberDetailView(DetailView):
    model = Member
    template_name = 'argus/member_detail.html'
    context_object_name = 'member'

    def get_queryset(self):
        qs = super(MemberDetailView, self).get_queryset()
        qs = qs.select_related('group')
        return qs.filter(Q(group__auto_slug=self.kwargs['group_slug']) |
                         Q(group__custom_slug=self.kwargs['group_slug']))

    def get_context_data(self, **kwargs):
        context = super(MemberDetailView, self).get_context_data(**kwargs)
        context['balance'] = self.object.balance
        shares = Share.objects.filter(Q(member=self.object) |
                                      (Q(expense__member=self.object) &
                                       Q(expense__is_payment=True))
                                      ).order_by('-expense__paid_at')
        shares = shares.select_related('expense').distinct()
        #import pdb; pdb.set_trace()
        context['recent_shares'] = shares
        return context
