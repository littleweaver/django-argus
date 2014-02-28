from django import forms
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template import loader
from django.utils.translation import ugettext_lazy as _

from argus.models import Group, Transaction, Party, Share
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


class TransactionForm(forms.ModelForm):

    class Meta:
        model = Transaction
        exclude = ('split',)

    def __init__(self, group, split=Transaction.SIMPLE, *args, **kwargs):
        super(TransactionForm, self).__init__(*args, **kwargs)
        self.group = group
        self.split = split

        if not group.use_categories:
            del self.fields['category']
        else:
            self.fields['category'].queryset = group.categories.all()

        self.members = group.parties.filter(party_type=Party.MEMBER)
        self.fields['paid_by'].queryset = self.members
        self.fields['paid_by'].empty_label = None
        self.fields['paid_to'].queryset = self.group.parties.all()

    def clean(self):
        cleaned_data = super(TransactionForm, self).clean()
        if cleaned_data['paid_by'] == cleaned_data['paid_to']:
            raise forms.ValidationError("A party cannot pay themselves.")
        return cleaned_data

    def _post_clean(self):
        super(TransactionForm, self)._post_clean()
        self.instance.split = self.split


class SimpleSplitForm(TransactionForm):
    def __init__(self, *args, **kwargs):
        super(SimpleSplitForm, self).__init__(split=Transaction.SIMPLE,
                                              *args, **kwargs)
        self.fields['paid_to'].empty_label = None

    def save(self):
        instance = super(SimpleSplitForm, self).save()
        if not instance.paid_to.is_member():
            Share.objects.create(
                transaction=instance,
                party=instance.paid_by,
                portion=1,
                amount=instance.amount)
        return instance


class EvenSplitForm(TransactionForm):
    among = forms.ModelMultipleChoiceField(Party,
                                           widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, **kwargs):
        super(EvenSplitForm, self).__init__(split=Transaction.EVEN,
                                            *args, **kwargs)
        self.fields['among'].queryset = self.members
        self.fields['among'].empty_label = None
        self.initial['among'] = self.members

    def clean(self):
        cleaned_data = super(EvenSplitForm, self).clean()
        if cleaned_data['paid_to'] in cleaned_data['among']:
            raise forms.ValidationError("A member cannot share in a payment "
                                        "to themselves.")
        return cleaned_data

    def save(self):
        instance = super(EvenSplitForm, self).save()
        Share.objects.create_even(instance, self.cleaned_data['among'])
        return instance


class ManualSplitForm(TransactionForm):
    input_type = forms.ChoiceField(widget=forms.RadioSelect,
                                   choices=(('percent', _('Percent')),
                                            ('amount', _('Amount'))))

    def __init__(self, *args, **kwargs):
        super(ManualSplitForm, self).__init__(split=Transaction.MANUAL,
                                              *args, **kwargs)
        for member in self.members:
            field = forms.DecimalField(decimal_places=2, min_value=0,
                                       initial=0, label=member.name)
            field.member = member
            self.fields['member{}'.format(member.pk)] = field

    def clean(self):
        cleaned_data = super(ManualSplitForm, self).clean()
        input_type = cleaned_data['input_type']
        amounts = [cleaned_data['member{}'].format(member.pk)
                   for member in self.members]
        cleaned_total = sum(amounts)
        if input_type == 'percent':
            if cleaned_total != 100:
                raise forms.ValidationError("Percentages must add up to "
                                            "100.00%.")
        else:
            if cleaned_total != cleaned_data.amount:
                raise forms.ValidationError("Share amounts must add up to "
                                            "total cost.")
        return cleaned_data

    def save(self):
        instance = super(ManualSplitForm, self).save()
        cd = self.cleaned_data
        portion_is_manual = cd['input_type'] == 'percent'
        amount_is_manual = cd['input_type'] == 'amount'
        shares = [
            Share(transaction=instance,
                  member=member,
                  portion=(cd['member{}'.format(member.pk)] / 100
                           if portion_is_manual else
                           cd['member{}'.format(member.pk)] /
                           instance.amount),
                  amount=(cd['member{}'.format(member.pk)]
                          if amount_is_manual else instance.amount *
                          (cd['member{}'.format(member.pk)] / 100)))
            for member in self.members
        ]
        Share.objects.auto_tweak(shares, instance.amount,
                                 portion_is_manual=portion_is_manual,
                                 amount_is_manual=amount_is_manual)
        Share.objects.bulk_create(shares)
        return instance
