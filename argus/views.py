from django.db import models
from django.views.generic import DetailView

from argus.models import Member


class MemberView(DetailView):
    model = Member
    template_name = 'argus/member.html'
    context_object_name = 'member'

    def get_queryset(self):
        qs = super(MemberView, self).get_queryset()
        return qs.filter(models.Q(group__auto_slug=self.kwargs['group_slug']) |
                         models.Q(group__custom_slug=self.kwargs['group_slug']))

    def get_context_data(self, **kwargs):
        context = super(MemberView, self).get_context_data(**kwargs)
        total_expense = self.object.expenses.aggregate(models.Sum('cost'))['cost__sum'] or 0
        total_share = self.object.shares.aggregate(models.Sum('amount'))['amount__sum'] or 0
        
        owed = total_share - total_expense
        context['owed'] = owed
        return context
