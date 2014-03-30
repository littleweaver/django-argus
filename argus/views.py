from django.conf import settings
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.forms.models import modelform_factory
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template import loader
from django.views.generic import (DetailView, TemplateView, RedirectView,
                                  UpdateView, FormView, CreateView)
from django.views.generic.edit import BaseUpdateView

from argus.forms import (GroupForm, GroupAuthenticationForm,
                         GroupChangePasswordForm, GroupRelatedForm,
                         TransactionForm, GroupCreateFormSet)
from argus.models import Party, Group, Transaction, Category
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
        subject = loader.render_to_string(self.subject_template_name,
                                          email_context)
            # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(self.body_template_name, email_context)

        if self.html_email_template_name:
            html_email = loader.render_to_string(self.html_email_template_name,
                                                 email_context)
        else:
            html_email = None
        send_mail(subject, body, from_email, [email_context['email']],
                  html_message=html_email)


class GroupPasswordResetTokenView(TokenView):
    model = Group
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

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() in self.http_method_names:
            self.group = Group.objects.get(slug=kwargs['slug'])
            if not self.generator.check_token(self.group, kwargs['token']):
                raise Http404("Token invalid or expired.")
        return super(FormView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(GroupPasswordResetConfirmView, self
                        ).get_context_data(**kwargs)
        context['group'] = self.group
        return context

    def get_success_url(self):
        return reverse('argus_group_password_reset_done',
                       kwargs={'slug': self.group.slug})

    def form_valid(self, form):
        form.save()
        return super(GroupPasswordResetConfirmView, self).form_valid(form)


class GroupEmailConfirmView(DetailView):
    model = Group
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


class GroupCreateView(CreateView):
    form_class = GroupCreateFormSet
    template_name = 'argus/group_create.html'

    def get_form_kwargs(self):
        kwargs = super(GroupCreateView, self).get_form_kwargs()
        kwargs['queryset'] = Party.objects.none()
        del kwargs['instance']
        return kwargs

    def get_form_class(self):
        return self.form_class

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        # Temporary, to make testing easier.
        context = super(GroupCreateView, self).get_context_data(**kwargs)
        context['groups'] = Group.objects.all()
        return context


class TransactionFormMixin(object):
    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() in self.http_method_names:
            self.group = self.get_group()
            if _group_auth_needed(request, self.group):
                return _group_auth_redirect(self.group)
        return super(TransactionFormMixin, self).dispatch(request, *args,
                                                          **kwargs)

    def get_group(self):
        return get_object_or_404(Group, slug=self.kwargs['group_slug'])

    def get_transaction_form(self, pk=None):
        if pk:
            self.transaction = get_object_or_404(Transaction, pk=pk)
        else:
            self.transaction = None
        kwargs = {
            'group': self.group,
            'instance': self.transaction,
        }
        if self.request.method == 'POST':
            kwargs['data'] = self.request.POST

        return TransactionForm(**kwargs)

    def get_context_data(self, **kwargs):
        context = super(TransactionFormMixin, self).get_context_data(**kwargs)
        form = self.get_transaction_form()
        context['form'] = form
        context['group'] = self.group
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = context['form']
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(self.group.get_absolute_url())
        return self.render_to_response(context)


class TransactionUpdateView(TransactionFormMixin, TemplateView):
    template_name = 'argus/transaction_update.html'

    def get_transaction_form(self, pk=None):
        pk = self.kwargs['pk']
        return super(TransactionUpdateView, self).get_transaction_form(pk)


class TransactionListView(TransactionFormMixin, TemplateView):
    template_name = 'argus/transaction_list.html'

    def get_group(self):
        qs = Group.objects.prefetch_related('parties', 'categories')
        return get_object_or_404(qs, slug=self.kwargs['group_slug'])

    def get_transactions(self):
        return Transaction.objects.filter(paid_by__group=self.group
                                          ).order_by('-paid_at'
                                          ).prefetch_related('shares')

    def get_context_data(self, **kwargs):
        context = super(TransactionListView, self).get_context_data(**kwargs)
        context['recent_transactions'] = self.get_transactions()
        context['members'] = [p for p in self.group.parties.all()
                              if p.party_type == Party.MEMBER]
        return context


class GroupDetailView(TransactionListView):
    template_name = 'argus/group_detail.html'


class GroupRelatedDetailView(TransactionListView):
    def get_group(self):
        group = super(GroupRelatedDetailView, self).get_group()
        self.object = get_object_or_404(self.model,
                                        group=group,
                                        pk=self.kwargs['pk'])
        return group

    def get_context_data(self, **kwargs):
        context = super(GroupRelatedDetailView, self).get_context_data(**kwargs)
        context_object_name = getattr(self, 'context_object_name',
                                      self.model._meta.verbose_name.lower())
        context[context_object_name] = self.object
        context['balance'] = self.get_balance()
        return context

    def get_balance(self):
        raise NotImplementedError


class PartyDetailView(GroupRelatedDetailView):
    model = Party
    template_name = 'argus/party_detail.html'

    def get_balance(self):
        return self.object.balance

    def get_transactions(self):
        return Transaction.objects.filter(Q(shares__party=self.object) |
                                          Q(paid_by=self.object) |
                                          Q(paid_to=self.object)
                                          ).order_by('-paid_at'
                                          ).distinct()


class CategoryDetailView(GroupRelatedDetailView):
    model = Category
    template_name = 'argus/category_detail.html'

    def get_balance(self):
        transactions = self.get_transactions()
        return transactions.aggregate(models.Sum('amount'))['amount__sum']

    def get_transactions(self):
        return self.object.transactions.order_by('-paid_at')


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
        return reverse('argus_group_update', kwargs={'slug': self.object.slug})


class GroupChangePasswordView(UpdateView):
    model = Group
    form_class = GroupChangePasswordForm
    template_name = 'argus/group_password_change.html'

    def get_success_url(self):
        return reverse("argus_group_update", kwargs={'slug': self.object.slug})


class GroupRelatedFormMixin(object):
    form_class = GroupRelatedForm

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() in self.http_method_names:
            try:
                self.group = Group.objects.get(slug=kwargs['group_slug'])
            except Group.DoesNotExist:
                raise Http404("Group does not exist.")
            if _group_auth_needed(request, self.group):
                return _group_auth_redirect(self.group)
        return super(GroupRelatedFormMixin, self).dispatch(request,
                                                           *args,
                                                           **kwargs)

    def get_form_class(self):
        return modelform_factory(self.model, self.form_class)

    def get_form_kwargs(self):
        kwargs = super(GroupRelatedFormMixin, self).get_form_kwargs()
        kwargs['group'] = self.group
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(GroupRelatedFormMixin, self
                        ).get_context_data(**kwargs)
        context['group'] = context['form'].group
        return context


class GroupRelatedCreateView(GroupRelatedFormMixin, CreateView):
    def get_success_url(self):
        return self.object.group.get_absolute_url()


class GroupRelatedUpdateView(GroupRelatedFormMixin, UpdateView):
    def get_success_url(self):
        return self.object.get_absolute_url()
