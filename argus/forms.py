from django import forms

from argus.models import Group


class GroupForm(forms.ModelForm):
	class Meta:
		model = Group
		exclude = ('auto_slug', 'password')
