# encoding: utf-8

from decimal import Decimal
import random

from django.contrib.auth.hashers import make_password, check_password
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import smart_text
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _


class Group(models.Model):
    SESSION_KEY = '_argus_group_id'

    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=64, blank=True)
    email = models.EmailField(blank=True)
    confirmed_email = models.EmailField(blank=True)
    password = models.CharField(max_length=128, blank=True)
    use_categories = models.BooleanField(default=False)
    currency = models.CharField(max_length=3, default='USD')

    created = models.DateTimeField(default=now)

    def __unicode__(self):
        return smart_text(self.name or self.slug)

    def get_absolute_url(self):
        return reverse("argus_group_detail",
                       kwargs={"slug": self.slug})

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """
        Returns a boolean of whether the raw_password was correct. Handles
        hashing formats behind the scenes.

        """
        def setter(raw_password):
            self.set_password(raw_password)
            self.save(update_fields=["password"])
        return check_password(raw_password, self.password, setter)


class Member(models.Model):
    name = models.CharField(max_length=128)
    group = models.ForeignKey(Group, related_name='members')

    def __unicode__(self):
        return smart_text(self.name)

    def get_absolute_url(self):
        return reverse("argus_member_detail",
                       kwargs={
                           "group_slug": self.group.slug,
                           "pk": self.pk,
                       })

    @property
    def balance(self):
        if not hasattr(self, '_balance'):
            total_expense = self.expenses.aggregate(models.Sum('cost'))['cost__sum'] or 0
            total_share = self.shares.aggregate(models.Sum('amount'))['amount__sum'] or 0
            self._balance = total_share - total_expense
        return self._balance


class Recipient(models.Model):
    name = models.CharField(max_length=64)
    group = models.ForeignKey(Group, related_name='recipients')

    def __unicode__(self):
        return smart_text(self.name)


class Category(models.Model):
    name = models.CharField(max_length=64)
    group = models.ForeignKey(Group, related_name='categories')

    class Meta:
        verbose_name_plural = 'categories'

    def __unicode__(self):
        return smart_text(self.name)


class ExpenseManager(models.Manager):
    def create_payment(self, from_member, to_member, amount, **kwargs):
        if from_member == to_member:
            raise ValueError(u"A member cannot pay themselves.")
        kwargs.update({
            'cost': amount,
            'member': from_member,
            'is_payment': True,
        })
        if 'memo' not in kwargs:
            kwargs['memo'] = (_("Payment: ") + from_member.name +
                              " -> " + to_member.name)
        expense = self.create(**kwargs)
        Share.objects.create(
            expense=expense,
            member=to_member,
            portion=1,
            amount=amount
        )
        return expense

    def create_even(self, member, cost, memo, **kwargs):
        kwargs.update({
            'member': member,
            'cost': cost,
            'memo': memo,
            'is_even': True,
        })

        expense = self.create(**kwargs)

        Share.objects.create_even(expense, member.group.members.all())

        return expense


class Expense(models.Model):
    """
    Represents an expense paid by one member which should be shared
    among some or all members.

    """
    member = models.ForeignKey(Member, related_name='expenses')
    recipient = models.ForeignKey(Recipient, related_name='expenses',
                                  blank=True, null=True)
    memo = models.CharField(max_length=64)
    cost = models.DecimalField(max_digits=11, decimal_places=2)
    paid_at = models.DateTimeField(default=now)
    category = models.ForeignKey(Category, blank=True, null=True)
    notes = models.TextField(blank=True)
    #: Is this a payment from one member to another?
    is_payment = models.BooleanField(default=False)
    #: Is this expense evenly split among all members?
    is_even = models.BooleanField(default=False)

    objects = ExpenseManager()

    def __unicode__(self):
        return u"{} ({})".format(smart_text(self.memo), self.cost)


class ShareManager(models.Manager):
    def create_even(self, expense, members):
        shares = [Share(expense=expense,
                        member=member,
                        portion_is_manual=False,
                        amount_is_manual=False)
                  for member in members]
        self._set_even(shares, expense.cost)

        Share.objects.bulk_create(shares)

    def set_even(self, expense):
        shares = expense.shares.all()
        self._set_even(shares, expense.cost)
        for share in self.shares:
            share.save()

    def _set_even(self, shares, total_cost):
        portion = Decimal(1 / len(shares)).quantize(Decimal('.01'))
        share_amount = (total_cost * portion).quantize(Decimal('.01'))

        for share in shares:
            share.portion = portion
            share.portion_is_manual = True
            share.amount = share_amount
            share.amount_is_manual = False

        if share_amount * len(shares) < total_cost:
            share = random.choice(shares)
            share.amount = total_cost - (share_amount * (len(shares) - 1))


class Share(models.Model):
    """
    Represents a share of an expense that a given member is responsible
    for.

    """
    expense = models.ForeignKey(Expense, related_name='shares')
    member = models.ForeignKey(Member, related_name='shares')
    # Decimal less than one indicating what part of the total cost
    # this person bears.
    portion = models.DecimalField(max_digits=5, decimal_places=4)
    portion_is_manual = models.BooleanField(default=False)
    # Raw amount that the person is expected to pay.
    amount = models.DecimalField(max_digits=11, decimal_places=2)
    amount_is_manual = models.BooleanField(default=False)

    objects = ShareManager()

    @property
    def percentage(self):
        return (self.portion * 100).quantize(Decimal('.01'))
