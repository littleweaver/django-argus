# encoding: utf-8

from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.db import models
from django.utils.encoding import smart_text
from django.utils.timezone import now


class Group(models.Model):
    email = models.EmailField()
    name = models.CharField(max_length=64)
    custom_slug = models.CharField(max_length=30)
    auto_slug = models.CharField(max_length=30)
    password = models.CharField(max_length=128, blank=True)
    use_categories = models.BooleanField(default=False)
    currency = models.CharField(max_length=3, default='USD')

    def __unicode__(self):
        return smart_text(self.name)

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
    group = models.ForeignKey(Group)

    def __unicode__(self):
        return smart_text(self.name)


class Recipient(models.Model):
    name = models.CharField(max_length=64)
    group = models.ForeignKey(Group)

    def __unicode__(self):
        return smart_text(self.name)


class Category(models.Model):
    name = models.CharField(max_length=64)
    group = models.ForeignKey(Group)

    class Meta:
        verbose_name_plural = 'categories'

    def __unicode__(self):
        return smart_text(self.name)


class Expense(models.Model):
    """
    Represents an expense paid by one member which should be shared
    among all members.

    """
    member = models.ForeignKey(Member, related_name='expenses')
    recipient = models.ForeignKey(Recipient, related_name='expenses')
    memo = models.CharField(max_length=64)
    cost = models.DecimalField(max_digits=11, decimal_places=2)
    paid_at = models.DateTimeField(default=now)
    category = models.ForeignKey(Category, blank=True, null=True)
    notes = models.TextField(blank=True)

    def __unicode__(self):
        return u"{} ({})".format(smart_text(self.memo), self.cost)


class Share(models.Model):
    """
    Represents a share of an expense that a given member is responsible
    for.

    """
    expense = models.ForeignKey(Expense, related_name='shares')
    member = models.ForeignKey(Member, related_name='shares')
    percentage = models.FloatField(blank=True, null=True)
    # If percentage is provided, this is calculated. Otherwise, flat.
    amount = models.DecimalField(max_digits=11, decimal_places=2)


class Payment(models.Model):
    from_member = models.ForeignKey(Member, related_name='payments_from')
    to_member = models.ForeignKey(Member, related_name='payments_to')
    amount = models.DecimalField(max_digits=11, decimal_places=2)
    paid_at = models.DateTimeField(default=now)

    def __unicode__(self):
        return u'{}'.format(self.amount)
