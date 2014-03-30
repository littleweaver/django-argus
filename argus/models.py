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
                       kwargs={"group_slug": self.slug})

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

        Share.objects.create_split(transaction,
                                   [(member, 1) for member in members])

        return transaction


class Transaction(models.Model):
    """
    Represents an transaction paid by one member which should be shared
    among some or all members.

    """
    # Payment from one party to another.
    SIMPLE = 'simple'
    # Even split among certain members.
    EVEN = 'even'
    # Manual split by percentage.
    PERCENT = 'percent'
    # Manual split by amount.
    AMOUNT = 'amount'
    # Manual split by shares.
    SHARES = 'shares'

    SPLIT_CHOICES = (
        (SIMPLE, _('Simple payment')),
        (EVEN, _('Even split')),
        (PERCENT, _('Manual percentages')),
        (AMOUNT, _('Manual amounts')),
        (SHARES, _('Manual shares'))
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
                             default=EVEN)

    objects = TransactionManager()

    def __unicode__(self):
        return u"{} ({})".format(smart_text(self.memo), self.amount)

    def is_manual(self):
        return self.split in (self.PERCENT, self.AMOUNT, self.SHARES)


class ShareManager(models.Manager):
    def create_split(self, transaction, member_numerators):
        members, numerators = zip(*member_numerators)
        denominator = sum(numerators)
        shares = []
        for member, numerator in member_numerators:
            amount = Decimal((numerator * transaction.amount)
                             / denominator).quantize(Decimal('0.01'))
            shares.append(Share(transaction=transaction,
                                party=member,
                                numerator=numerator,
                                denominator=denominator,
                                amount=amount))

        amount_sum = sum([share.amount for share in shares])

        if amount_sum != transaction.amount:
            share = random.choice(shares)
            share.amount = transaction.amount - (amount_sum - share.amount)

        return Share.objects.bulk_create(shares)


class Share(models.Model):
    """
    Represents a share of an transaction that goes to a given party

    """
    transaction = models.ForeignKey(Transaction, related_name='shares')
    party = models.ForeignKey(Party, related_name='shares')

    # Raw amount that the person is expected to pay.
    amount = models.DecimalField(max_digits=11, decimal_places=2)

    # Integers indicating what exact portion of the total cost
    # this person bears.
    numerator = models.PositiveIntegerField()
    denominator = models.PositiveIntegerField()

    objects = ShareManager()

    @property
    def percentage(self):
        fraction = Decimal(self.numerator) / Decimal(self.denominator)
        return (fraction * 100).quantize(Decimal('.01'))
