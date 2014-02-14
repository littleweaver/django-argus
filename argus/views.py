import datetime
import hashlib

from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.views.generic import (DetailView, ListView, RedirectView,
                                  UpdateView, FormView)
from django.views.generic.edit import BaseUpdateView

from argus.forms import GroupForm, GroupAuthenticationForm
from argus.models import Member, Group, Share
from argus.utils import login, logout


def _group_auth_needed(request, group):
    if request.user.is_authenticated() and request.user.is_superuser:
        return False
    if group.password:
        auth_group_id = request.session.get(Group.SESSION_KEY)
        if auth_group_id is None or auth_group_id != group.pk:
            return True
    return False
                


def _group_auth_redirect(group):
    return HttpResponseRedirect(reverse("argus_group_login",
                                kwargs={'slug': group.slug}))


class GroupLoginView(FormView):
    form_class = GroupAuthenticationForm
    template_name = 'argus/group_login.html'

    def get_form_kwargs(self):
        kwargs = super(GroupLoginView, self).get_form_kwargs()

        qs = Group.objects.filter(slug=self.kwargs['slug'])
        try:
            self.object = qs.get()
        except Group.DoesNotExist:
            raise Http404("Group doesn't exist")

        if not self.object.password:
            raise Http404("Group doesn't have a password")

        kwargs.update({
            'group': self.object,
            'request': self.request,
        })
        return kwargs

    def form_valid(self, form):
        login(self.request, form.group)
        self.object = form.group
        return super(GroupLoginView, self).form_valid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super(GroupLoginView, self).get_context_data(**kwargs)
        context['group'] = self.object
        return context


class GroupCreateView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        while True:
            slug = hashlib.sha1(datetime.datetime.now().isoformat()).hexdigest()[:6]
            if not Group.objects.filter(slug).exists():
                group = Group.objects.create(slug=slug)
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

    def get_queryset(self):
        qs = super(GroupDetailView, self).get_queryset()
        return qs.prefetch_related('members', 'recipients', 'categories')

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if _group_auth_needed(request, self.object):
            return _group_auth_redirect(self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


class GroupUpdateView(UpdateView):
    model = Group
    form_class = GroupForm
    template_name = 'argus/group_update.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if _group_auth_needed(request, self.object):
            return _group_auth_redirect(self.object)
        return super(BaseUpdateView, self).get(request, *args, **kwargs)


class MemberDetailView(DetailView):
    model = Member
    template_name = 'argus/member_detail.html'
    context_object_name = 'member'

    def get_queryset(self):
        qs = super(MemberDetailView, self).get_queryset()
        qs = qs.select_related('group')
        return qs.filter(group__slug=self.kwargs['group_slug'])

    def get_context_data(self, **kwargs):
        context = super(MemberDetailView, self).get_context_data(**kwargs)
        context['balance'] = self.object.balance
        shares = Share.objects.filter(Q(member=self.object) |
                                      (Q(expense__member=self.object) &
                                       Q(expense__is_payment=True))
                                      ).order_by('-expense__paid_at')
        shares = shares.select_related('expense').distinct()
        context['recent_shares'] = shares
        return context

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if _group_auth_needed(request, self.object.group):
            return _group_auth_redirect(self.object.group)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)
