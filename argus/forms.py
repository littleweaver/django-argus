from django import forms
from django.utils.translation import ugettext_lazy as _

from argus.models import Group


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        exclude = ('password',)


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
