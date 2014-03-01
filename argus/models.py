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
    currency = models.CharField(max_length=3, default='USD')
    default_category = models.OneToOneField('Category', blank=True, null=True,
                                            related_name='default_for')

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


class PartyManager(models.Manager):
    use_for_related_fields = True

    def members(self):
        return self.filter(party_type=Party.MEMBER)

    def sinks(self):
        return self.filter(party_type=Party.SINK)


class Party(models.Model):
    SINK = 'sink'
    MEMBER = 'member'

    TYPE_CHOICES = (
        (SINK, _('Expense source')),
        (MEMBER, _('Member')),
    )
    name = models.CharField(max_length=128)
    group = models.ForeignKey(Group, related_name='parties')
    party_type = models.CharField(max_length=11, choices=TYPE_CHOICES,
                                  default=SINK)

    objects = PartyManager()

    def __unicode__(self):
        return smart_text(self.name)

    def get_absolute_url(self):
        return reverse("argus_party_detail",
                       kwargs={
                           "group_slug": self.group.slug,
                           "pk": self.pk
                       })

    @property
    def balance(self):
        if not hasattr(self, '_balance'):
            paid = -1 * (self.transactions_paid.aggregate(models.Sum('amount'))['amount__sum'] or 0)
            received = self.transactions_received.aggregate(models.Sum('amount'))['amount__sum'] or 0
            shares = self.shares.aggregate(models.Sum('amount'))['amount__sum'] or 0
            self._balance = sum((shares, paid, received))
        return self._balance

    def is_member(self):
        return self.party_type == Party.MEMBER


class Category(models.Model):
    DEFAULT_NAME = _("Uncategorized")
    name = models.CharField(max_length=64)
    group = models.ForeignKey(Group, related_name='categories')

    class Meta:
        verbose_name_plural = 'categories'

    def __unicode__(self):
        return smart_text(self.name)

    def get_absolute_url(self):
        return reverse('argus_category_detail',
                       kwargs={'group_slug': self.group.slug, 'pk': self.pk})


class TransactionManager(models.Manager):
    def create_payment(self, paid_by, paid_to, amount, **kwargs):
        if paid_by == paid_to:
            raise ValueError(u"A party cannot pay themselves.")
        kwargs.update({
            'amount': amount,
            'paid_by': paid_by,
            'paid_to': paid_to,
            'split': Transaction.SIMPLE,
        })
        if 'memo' not in kwargs:
            kwargs['memo'] = (_("Payment: ") + paid_by.name +
                              " -> " + paid_to.name)
        return self.create(**kwargs)

    def create_even(self, paid_by, paid_to, amount, memo,
                    members=None, **kwargs):
        kwargs.update({
            'paid_by': paid_by,
            'amount': amount,
            'memo': memo,
            'split': Transaction.EVEN,
        })

        transaction = self.create(**kwargs)

        if members is None:
            members = paid_by.group.parties.filter(party_type=Party.MEMBER)

        Share.objects.create_even(transaction, members)

        return transaction


class Transaction(models.Model):
    """
    Represents an transaction paid by one member which should be shared
    among some or all members.

    """
    # Payment from one party to another.
    SIMPLE = 'simple'
    # Even split among all members.
    EVEN = 'even'
    # Manual split by transaction creator.
    MANUAL = 'manual'

    SPLIT_CHOICES = (
        (SIMPLE, _('Simple payment')),
        (EVEN, _('Even split')),
        (MANUAL, _('Manual entry')),
    )

    paid_by = models.ForeignKey(Party, related_name='transactions_paid')
    paid_to = models.ForeignKey(Party, related_name='transactions_received',
                                blank=True, null=True)
    memo = models.CharField(max_length=64)
    amount = models.DecimalField(max_digits=11, decimal_places=2)
    paid_at = models.DateTimeField(default=now)
    category = models.ForeignKey(Category, related_name='transactions')
    notes = models.TextField(blank=True)
    split = models.CharField(max_length=7,
                             choices=SPLIT_CHOICES,
                             default=MANUAL)

    objects = TransactionManager()

    def __unicode__(self):
        return u"{} ({})".format(smart_text(self.memo), self.cost)


class ShareManager(models.Manager):
    def create_even(self, transaction, members):
        shares = [Share(transaction=transaction,
                        party=member)
                  for member in members]
        self._set_even(shares, transaction.amount)

        Share.objects.bulk_create(shares)

    def set_even(self, transaction):
        shares = transaction.shares.all()
        self._set_even(shares, transaction.amount)
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
    Represents a share of an transaction that goes to a given party

    """
    transaction = models.ForeignKey(Transaction, related_name='shares')
    party = models.ForeignKey(Party, related_name='shares')
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
