import datetime
import hashlib

from django.conf import settings
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.template import loader
from django.views.generic import (DetailView, ListView, RedirectView,
                                  UpdateView, FormView, TemplateView)
from django.views.generic.edit import BaseUpdateView

from argus.forms import (GroupForm, GroupAuthenticationForm,
                         GroupChangePasswordForm)
from argus.models import Member, Group, Share
from argus.tokens import token_generators
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


class TokenView(DetailView):
    generator = None
    subject_template_name = None
    body_template_name = None
    html_email_template_name = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        email_context = self.get_email_context(context)
        self.send_email(email_context)
        return self.render_to_response(context)

    def get_email(self):
        raise NotImplementedError

    def get_email_context(self, base_context):
        context = base_context.copy()
        context.update({
            'email': self.get_email(),
            'site': get_current_site(self.request),
            'token': self.generator.make_token(self.object),
            'protocol': 'https' if self.request.is_secure() else 'http'
        })
        return context

    def send_email(self, email_context):
        from_email = settings.DEFAULT_FROM_EMAIL
        subject = loader.render_to_string(self.subject_template_name, email_context)
            # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(self.body_template_name, email_context)

        if self.html_email_template_name:
            html_email = loader.render_to_string(html_email_template_name, email_context)
        else:
            html_email = None
        send_mail(subject, body, from_email, [email_context['email']], html_message=html_email)


class GroupPasswordResetTokenView(TokenView):
    model = Group
    context_object_name = "group"
    generator = token_generators['password_reset']
    subject_template_name = "argus/mail/group_password_reset_subject.txt"
    body_template_name = "argus/mail/group_password_reset_body.txt"
    template_name = "argus/group_password_reset_sent.html"

    def get_object(self):
        obj = super(GroupPasswordResetTokenView, self).get_object()
        if not obj.password:
            raise Http404("Cannot reset password for passwordless group.")
        if not obj.confirmed_email:
            raise Http404("Confirmed email required to reset password.")
        return obj

    def get_email(self):
        return self.object.confirmed_email


class GroupPasswordResetConfirmView(FormView):
    generator = token_generators['password_reset']
    form_class = SetPasswordForm
    template_name = 'argus/group_password_reset_confirm.html'

    def get_form_kwargs(self):
        kwargs = super(GroupPasswordResetConfirmView, self).get_form_kwargs()
        kwargs['user'] = self.group
        return kwargs

    def dispatch(self, *args, **kwargs):
        self.group = Group.objects.get(slug=kwargs['slug'])
        if not self.generator.check_token(self.group, kwargs['token']):
            raise Http404("Token invalid or expired.")
        return super(FormView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(GroupPasswordResetConfirmView, self).get_context_data(**kwargs)
        context['group'] = self.group
        return context

    def get_success_url(self):
        return reverse('argus_group_password_reset_done', kwargs={'slug': self.group.slug})

    def form_valid(self, form):
        form.save()
        return super(GroupPasswordResetConfirmView, self).form_valid(form)


class GroupEmailConfirmView(DetailView):
    model = Group
    context_object_name = "group"
    generator = token_generators['email_confirm']
    template_name = 'argus/group_email_confirm.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.generator.check_token(self.object, self.kwargs['token']):
            raise Http404("Token invalid or expired.")
        self.object.confirmed_email = self.object.email
        self.object.save()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


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


class GroupLogoutView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        logout(self.request)
        return '/'


class GroupCreateView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        while True:
            slug = hashlib.sha1(datetime.datetime.now().isoformat()).hexdigest()[:6]
            if not Group.objects.filter(slug=slug).exists():
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

    def get_form_kwargs(self):
        kwargs = super(GroupUpdateView, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if _group_auth_needed(request, self.object):
            return _group_auth_redirect(self.object)
        return super(BaseUpdateView, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return self.request.path


class GroupChangePasswordView(UpdateView):
    model = Group
    form_class = GroupChangePasswordForm
    template_name = 'argus/group_password_change.html'

    def get_success_url(self):
        return reverse("argus_group_update", kwargs={'slug': self.object.slug})


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
