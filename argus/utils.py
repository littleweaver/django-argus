from django.middleware.csrf import rotate_token

from argus.models import Group


def login(request, group):
	if Group.SESSION_KEY in request.session:
		if request.session[Group.SESSION_KEY] != group.pk:
			# If someone is logged in as a different group, create a new,
			# empty session.
			request.session.flush()
	else:
		request.session.cycle_key()
	request.session[Group.SESSION_KEY] = group.pk
	rotate_token(request)


def logout(request):
	request.session.flush()
