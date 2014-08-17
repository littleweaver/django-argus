from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.forms.models import BaseModelFormSet, modelformset_factory
from django.template import loader
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
import floppyforms as forms

from argus.models import (Group, Transaction, Party, Share, Category,
                          URL_SAFE_CHARS)
from argus.tokens import token_generators


class PartyForm(forms.ModelForm):
    class Meta:
        widgets = {
            'name': forms.TextInput,
        }


class BaseGroupCreateFormSet(BaseModelFormSet):

    def clean(self):
        super(BaseGroupCreateFormSet, self).clean()
        filled = sum([1 if form.cleaned_data else 0
                      for form in self.forms])
        if filled < 2:
            raise forms.ValidationError("Please enter the name of at least "
                                        "two members to get started.")

    def save(self):
        while True:
            slug = get_random_string(length=6, allowed_chars=URL_SAFE_CHARS)
            if not Group.objects.filter(slug=slug).exists():
                group = Group.objects.create(slug=slug)
                category = Category.objects.create(name=Category.DEFAULT_NAME,
                                                   group=group)
                group.default_category = category
                group.save()
                break
        for form in self.forms:
            form.instance.group = group
            form.instance.party_type = Party.MEMBER
            if form.instance.name:
                form.save()
        return group
    save.alters_data = True


GroupCreateFormSet = modelformset_factory(
    Party,
    form=PartyForm,
    formset=BaseGroupCreateFormSet,
    extra=0,
    min_num=1,
    fields=('name',))


class GroupSlugInput(forms.SlugInput):
    def get_context(self, name, value, attrs):
        context = super(GroupSlugInput, self).get_context(name, value, attrs)
        context['attrs']['pattern'] = Group.SLUG_REGEX
        return context


class GroupForm(forms.ModelForm):
    subject_template_name = "argus/mail/group_email_confirm_subject.txt"
    body_template_name = "argus/mail/group_email_confirm_body.txt"
    html_email_template_name = None
    generator = token_generators['email_confirm']

    class Meta:
        model = Group
        exclude = ('password', 'confirmed_email', 'created',)
        widgets = {
            'slug': GroupSlugInput,
            'name': forms.TextInput,
            'email': forms.EmailInput,
            'currency': forms.TextInput,
            'default_category': forms.Select,
        }

    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(GroupForm, self).__init__(*args, **kwargs)
        self.fields['default_category'].queryset = self.instance.categories.all()
        self.fields['default_category'].empty_label = None
        self.fields['default_category'].required = True

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
        widgets = {
            'name': forms.TextInput,
        }

    def __init__(self, group, *args, **kwargs):
        self.group = group
        super(GroupRelatedForm, self).__init__(*args, **kwargs)

    def _post_clean(self):
        super(GroupRelatedForm, self)._post_clean()
        self.instance.group = self.group


class TransactionForm(forms.ModelForm):
    sharers = forms.ModelMultipleChoiceField(Party)

    class Meta:
        model = Transaction
        widgets = {
            'paid_by': forms.Select,
            'paid_to': forms.Select,
            'memo': forms.TextInput,
            'amount': forms.NumberInput(attrs={'step': 0.01}),
            'paid_at': forms.DateTimeInput,
            'category': forms.Select,
            'notes': forms.Textarea,
            'split': forms.RadioSelect,
            'sharers': forms.CheckboxSelectMultiple,
        }

    def __init__(self, group, *args, **kwargs):
        super(TransactionForm, self).__init__(*args, **kwargs)
        self.group = group

        self.fields['category'].queryset = group.categories.all()
        self.fields['category'].initial = group.default_category_id

        self.members = group.parties.filter(party_type=Party.MEMBER)
        self.fields['paid_by'].queryset = self.members
        self.fields['paid_by'].empty_label = None
        self.fields['paid_to'].queryset = group.parties.all()
        self.fields['sharers'].queryset = self.members
        self.initial['sharers'] = self.members

        for member in self.members:
            field = forms.DecimalField(decimal_places=2, min_value=0,
                                       initial=0, label=member.name)
            field.member = member
            field.widget.attrs['step'] = 0.01
            self.fields['member{}'.format(member.pk)] = field

        if self.instance.pk and self.instance.is_manual():
            for share in self.instance.shares.all():
                field = 'member{}'.format(share.party_id)
                self.fields[field].initial = float(share.numerator) / 100

    def clean(self):
        cleaned_data = super(TransactionForm, self).clean()
        split = cleaned_data['split']
        if cleaned_data['paid_by'] == cleaned_data['paid_to']:
            raise forms.ValidationError("A party cannot pay themselves.")
        if split == Transaction.SIMPLE:
            if not cleaned_data.get('paid_to'):
                raise forms.ValidationError("Simple transactions must be paid "
                                            "to someone.")
        elif split == Transaction.EVEN:
            if cleaned_data['paid_to'] in cleaned_data['sharers']:
                raise forms.ValidationError("A member cannot share in a "
                                            "payment to themselves.")
        else:
            if cleaned_data.get('member{}'.format(cleaned_data['paid_to'].pk)):
                raise forms.ValidationError("A member cannot share in a "
                                            "payment to themselves.")
            amounts = [cleaned_data['member{}'.format(member.pk)]
                       for member in self.members
                       if cleaned_data['member{}'.format(member.pk)]]
            cleaned_total = sum(amounts)
            if split == Transaction.PERCENT:
                if cleaned_total != 100:
                    raise forms.ValidationError("Percentages must add up to "
                                                "100.00%.")
            if split == Transaction.AMOUNT:
                if cleaned_total != cleaned_data['amount']:
                    raise forms.ValidationError("Share amounts must add up to "
                                                "total cost.")

        return cleaned_data

    def save(self):
        created = not self.instance.pk
        instance = super(TransactionForm, self).save()
        if not created:
            instance.shares.all().delete()
        if instance.split == Transaction.SIMPLE:
            if not instance.paid_to.is_member():
                Share.objects.create(
                    transaction=instance,
                    party=instance.paid_by,
                    numerator=1,
                    denominator=1,
                    amount=instance.amount)
        elif instance.split == Transaction.EVEN:
            shares = [(member, 1) for member in self.cleaned_data['sharers']]
            Share.objects.create_split(instance, shares)
        else:
            cd = self.cleaned_data
            member_numerators = [(member, cd['member{}'.format(member.pk)] * 100)
                                 for member in self.members
                                 if cd['member{}'.format(member.pk)]]
            Share.objects.create_split(instance, member_numerators)
        return instance
