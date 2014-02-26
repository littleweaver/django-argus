# encoding: utf-8

from decimal import Decimal
import random

from django.contrib.auth.hashers import make_password, check_password
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from django.db import models
from django.utils.encoding import smart_text
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _


URL_SAFE_CHARS = ('abcdefghijklmnopqrstuvwxyz'
                  'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                  '0123456789-_~.')


class Group(models.Model):
    SESSION_KEY = '_argus_group_id'
    SLUG_REGEX = "[\w_~\.-]+"

    slug = models.CharField(max_length=50, unique=True,
                            validators=[RegexValidator(SLUG_REGEX)])
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

    def get_absolute_url(self):
        return reverse('argus_recipient_detail',
                       kwargs={'group_slug': self.group.slug, 'pk': self.pk})


class Category(models.Model):
    name = models.CharField(max_length=64)
    group = models.ForeignKey(Group, related_name='categories')

    class Meta:
        verbose_name_plural = 'categories'

    def __unicode__(self):
        return smart_text(self.name)

    def get_absolute_url(self):
        return reverse('argus_category_detail',
                       kwargs={'group_slug': self.group.slug, 'pk': self.pk})


class ExpenseManager(models.Manager):
    def create_payment(self, from_member, to_member, amount, **kwargs):
        if from_member == to_member:
            raise ValueError(u"A member cannot pay themselves.")
        kwargs.update({
            'cost': amount,
            'member': from_member,
            'split': Expense.PAYMENT_SPLIT,
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
            'split': Expense.EVEN_SPLIT,
        })

        expense = self.create(**kwargs)

        Share.objects.create_even(expense, member.group.members.all())

        return expense


class Expense(models.Model):
    """
    Represents an expense paid by one member which should be shared
    among some or all members.

    """
    # Payment from one member to another.
    PAYMENT_SPLIT = 'payment'
    # Even split among all members.
    EVEN_SPLIT = 'even'
    # Manual split by expense creator.
    MANUAL_SPLIT = 'manual'

    SPLIT_CHOICES = (
        (PAYMENT_SPLIT, _('Member-to-member payment')),
        (EVEN_SPLIT, _('Even split')),
        (MANUAL_SPLIT, _('Manual entry')),
    )

    member = models.ForeignKey(Member, related_name='expenses')
    recipient = models.ForeignKey(Recipient, related_name='expenses',
                                  blank=True, null=True)
    memo = models.CharField(max_length=64)
    cost = models.DecimalField(max_digits=11, decimal_places=2)
    paid_at = models.DateTimeField(default=now)
    category = models.ForeignKey(Category, blank=True, null=True,
                                 related_name='expenses')
    notes = models.TextField(blank=True)
    split = models.CharField(max_length=7,
                             choices=SPLIT_CHOICES,
                             default=MANUAL_SPLIT)

    objects = ExpenseManager()

    def __unicode__(self):
        return u"{} ({})".format(smart_text(self.memo), self.cost)


class ShareManager(models.Manager):
    def create_even(self, expense, members):
        shares = [Share(expense=expense,
                        member=member)
                  for member in members]
        self._set_even(shares, expense.cost)

        Share.objects.bulk_create(shares)

    def set_even(self, expense):
        shares = expense.shares.all()
        self._set_even(shares, expense.cost)
        for share in self.shares:
            share.save()

    def _set_even(self, shares, total_cost):
        portion = (Decimal('1.00') / len(shares)).quantize(Decimal('.0001'))
        share_amount = (total_cost / len(shares)).quantize(Decimal('.01'))

        for share in shares:
            share.portion = portion
            share.amount = share_amount
        self.auto_tweak(shares, total_cost, portion_is_manual=False,
                        amount_is_manual=False)

    def auto_tweak(self, shares, total_cost, portion_is_manual=True,
                   amount_is_manual=True):
        for share in shares:
            share.portion_is_manual = portion_is_manual
            share.amount_is_manual = amount_is_manual

        amounts, portions = zip(*[(share.amount, share.portion)
                                  for share in shares])
        amount_sum = sum(amounts)
        portion_sum = sum(portions)

        if portion_is_manual and portion_sum != 1:
            raise ValueError("Manual portions do not sum to 1.")

        if amount_is_manual and amount_sum != total_cost:
            raise ValueError("Manual amounts do not sum to cost.")

        share = random.choice(shares)

        if portion_sum != 1:
            # We already know that portion is auto.
            share.portion = 1 - (portion_sum - share.portion)

        if amount_sum != total_cost:
            # We already know that amount is auto.
            share.amount = total_cost - (amount_sum - share.amount)


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
