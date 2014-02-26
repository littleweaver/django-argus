from django import forms
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template import loader
from django.utils.translation import ugettext_lazy as _

from argus.models import Group, Expense, Member, Recipient, Share
from argus.tokens import token_generators


class GroupForm(forms.ModelForm):
    subject_template_name = "argus/mail/group_email_confirm_subject.txt"
    body_template_name = "argus/mail/group_email_confirm_body.txt"
    html_email_template_name = None
    generator = token_generators['email_confirm']

    class Meta:
        model = Group
        exclude = ('password', 'confirmed_email', 'created',)

    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(GroupForm, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        instance = super(GroupForm, self).save(*args, **kwargs)
        if 'email' in self.changed_data:
            # Send confirmation link.
            context = {
                'group': instance,
                'email': instance.email,
                'site': get_current_site(self.request),
                'token': self.generator.make_token(instance),
                'protocol': 'https' if self.request.is_secure() else 'http',
            }
            from_email = settings.DEFAULT_FROM_EMAIL

            subject = loader.render_to_string(self.subject_template_name,
                                              context)
            # Email subject *must not* contain newlines
            subject = ''.join(subject.splitlines())
            body = loader.render_to_string(self.body_template_name, context)

            if self.html_email_template_name:
                html_email = loader.render_to_string(self.html_email_template_name,
                                                     context)
            else:
                html_email = None
            send_mail(subject, body, from_email, [instance.email],
                      html_message=html_email)
        return instance


class GroupAuthenticationForm(forms.Form):
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)

    def __init__(self, group, request, *args, **kwargs):
        self._group = group
        self.request = request
        super(GroupAuthenticationForm, self).__init__(*args, **kwargs)

    def clean(self):
        password = self.cleaned_data.get('password')
        if password:
            if self._group.check_password(password):
                self.group = self._group
            else:
                raise forms.ValidationError("Incorrect password.")
        return self.cleaned_data


class GroupChangePasswordForm(forms.ModelForm):
    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
        'password_incorrect': _("Your old password was entered incorrectly. "
                                "Please enter it again."),
    }
    old_password = forms.CharField(label=_("Old password"),
                                   widget=forms.PasswordInput)
    new_password1 = forms.CharField(label=_("New password"),
                                    widget=forms.PasswordInput)
    new_password2 = forms.CharField(label=_("New password confirmation"),
                                    widget=forms.PasswordInput)

    class Meta:
        model = Group
        fields = ()

    def __init__(self, *args, **kwargs):
        super(GroupChangePasswordForm, self).__init__(*args, **kwargs)
        if not self.instance.password:
            del self.fields['old_password']

    def clean_old_password(self):
        """
        Validates that the old_password field is correct (if present).
        """
        old_password = self.cleaned_data["old_password"]
        if not self.instance.check_password(old_password):
            raise forms.ValidationError(
                self.error_messages['password_incorrect'],
                code='password_incorrect',
            )
        return old_password

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(
                    self.error_messages['password_mismatch'],
                    code='password_mismatch',
                )
        return password2

    def save(self, commit=True):
        self.instance.set_password(self.cleaned_data['new_password1'])
        if commit:
            self.instance.save()
        return self.instance


class GroupRelatedForm(forms.ModelForm):
    class Meta:
        exclude = ('group',)

    def __init__(self, group, *args, **kwargs):
        self.group = group
        super(GroupRelatedForm, self).__init__(*args, **kwargs)

    def _post_clean(self):
        super(GroupRelatedForm, self)._post_clean()
        self.instance.group = self.group


class BaseExpenseForm(forms.ModelForm):
    member = forms.ModelChoiceField(Member, widget=forms.RadioSelect)

    class Meta:
        model = Expense

    def __init__(self, group, *args, **kwargs):
        super(BaseExpenseForm, self).__init__(*args, **kwargs)
        # Do this here for DRY.
        del self.fields['split']
        if not group.use_categories:
            del self.fields['category']
        else:
            self.fields['category'].queryset = group.categories.all()
        self.fields['member'].queryset = group.members.all()
        self.fields['member'].empty_label = None
        self.group = group


class PaymentForm(BaseExpenseForm):
    recipient = forms.ModelChoiceField(Member, widget=forms.RadioSelect)

    class Meta:
        model = Expense
        exclude = ('recipient',)

    def __init__(self, *args, **kwargs):
        super(PaymentForm, self).__init__(*args, **kwargs)
        self.fields['recipient'].queryset = self.group.members.all()
        self.fields['recipient'].empty_label = None

    def clean(self):
        cleaned_data = super(PaymentForm, self).clean()
        if cleaned_data['member'] == cleaned_data['recipient']:
            raise forms.ValidationError("A member cannot pay themselves.")

    def _post_clean(self):
        super(PaymentForm, self)._post_clean()
        self.instance.split = Expense.PAYMENT_SPLIT

    def save(self):
        expense = super(PaymentForm, self).save()
        Share.objects.create(expense=expense,
                             member=self.cleaned_data['recipient'],
                             portion=1,
                             portion_is_manual=False,
                             amount=expense.cost,
                             amount_is_manual=False)
        return expense


class RecipientExpenseForm(BaseExpenseForm):
    recipient = forms.ModelChoiceField(Recipient, widget=forms.RadioSelect)

    def __init__(self, *args, **kwargs):
        super(RecipientExpenseForm, self).__init__(*args, **kwargs)
        self.fields['recipient'].queryset = self.group.recipients.all()
        self.fields['recipient'].empty_label = None


class EvenSplitForm(RecipientExpenseForm):
    among = forms.ModelMultipleChoiceField(Member,
                                           widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, **kwargs):
        super(EvenSplitForm, self).__init__(*args, **kwargs)
        all_members = self.group.members.all()
        self.fields['among'].queryset = all_members
        self.fields['among'].empty_label = None
        self.initial['among'] = all_members

    def _post_clean(self):
        super(EvenSplitForm, self)._post_clean()
        self.instance.split = Expense.EVEN_SPLIT

    def save(self):
        expense = super(EvenSplitForm, self).save()
        Share.objects.create_even(expense, self.cleaned_data['among'])
        return expense


class ManualSplitForm(RecipientExpenseForm):
    input_type = forms.ChoiceField(widget=forms.RadioSelect,
                                   choices=(('percent', _('Percent')),
                                            ('amount', _('Amount'))))

    def _post_clean(self):
        super(ManualSplitForm, self)._post_clean()
        self.instance.split = Expense.MANUAL_SPLIT


class ExpenseShareForm(forms.Form):
    percent_or_amount = forms.DecimalField(decimal_places=2, min_value=0,
                                           initial=0)

    def __init__(self, member, *args, **kwargs):
        self.member = member
        super(ExpenseShareForm, self).__init__(*args, **kwargs)


class BaseExpenseShareFormSet(forms.formsets.BaseFormSet):
    def __init__(self, group, *args, **kwargs):
        self.group = group
        self.members = group.members.all()
        super(BaseExpenseShareFormSet, self).__init__(*args, **kwargs)
        self.expense_form = ManualSplitForm(group, *args, **kwargs)

    def initial_form_count(self):
        return len(self.members)

    def _construct_form(self, i, **kwargs):
        if i < self.initial_form_count():
            kwargs['member'] = self.members[i]
        return super(BaseExpenseShareFormSet,
                     self)._construct_form(i, **kwargs)

    def clean(self):
        super(BaseExpenseShareFormSet, self).clean()
        if not self.expense_form.is_valid():
            self._errors.append(self.expense_form.errors)

        forms_to_delete = self.deleted_forms
        valid_forms = [form for form in self.forms
                       if form.is_valid() and form not in forms_to_delete]

        input_type = self.expense_form.cleaned_data['input_type']
        cleaned_total = sum([form.cleaned_data['percent_or_amount']
                             for form in valid_forms])
        if input_type == 'percent':
            if cleaned_total != 100:
                raise forms.ValidationError("Percentages must add up to "
                                            "100.00%.")
        else:
            if cleaned_total != self.expense_form.instance.cost:
                raise forms.ValidationError("Share amounts must add up to "
                                            "total cost.")

    def save(self):
        expense = self.expense_form.save()
        input_type = self.expense_form.cleaned_data['input_type']
        portion_is_manual = input_type == 'percent'
        amount_is_manual = input_type == 'amount'
        shares = [
            Share(expense=expense,
                  member=form.member,
                  portion=(form.cleaned_data['percent_or_amount'] / 100
                           if portion_is_manual else
                           form.cleaned_data['percent_or_amount'] /
                           expense.cost),
                  amount=(form.cleaned_data['percent_or_amount']
                          if amount_is_manual else expense.cost *
                          (form.cleaned_data['percent_or_amount'] / 100)))
            for form in self.forms
        ]
        Share.objects.auto_tweak(shares, expense.cost,
                                 portion_is_manual=portion_is_manual,
                                 amount_is_manual=amount_is_manual)
        Share.objects.bulk_create(shares)
        return expense


ExpenseShareFormSet = forms.formsets.formset_factory(
    form=ExpenseShareForm,
    formset=BaseExpenseShareFormSet,
    extra=0)
