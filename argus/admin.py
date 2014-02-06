from django.contrib import admin

from argus.models import (Group, Member, Recipient, Category, Expense,
                          Share)


class MemberInline(admin.TabularInline):
    model = Member


class RecipientInline(admin.TabularInline):
    model = Recipient


class CategoryInline(admin.TabularInline):
    model = Category


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    inlines = [MemberInline, RecipientInline, CategoryInline]


class ShareInline(admin.TabularInline):
    model = Share


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    inlines = [ShareInline]
