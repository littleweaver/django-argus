# encoding: utf8
from django.db import models, migrations
from django.utils.translation import ugettext_lazy as _


DEFAULT_NAME = _("Uncategorized")

def noop(apps, schema_editor):
    pass


def create_default_category(apps, schema_editor):
    Group = apps.get_model("argus", "Group")
    Category = apps.get_model("argus", "Category")

    for group in Group.objects.all():
        Category.objects.get_or_create(name=DEFAULT_NAME,
                                       group=group)


def add_default_category(apps, schema_editor):
    Group = apps.get_model("argus", "Group")

    for group in Group.objects.all():
        category = group.category_set.get(name=DEFAULT_NAME)
        group.default_category = category
        group.save()


class Migration(migrations.Migration):
    
    dependencies = [
        ('argus', '0002_auto_20140227_0424'),
    ]

    operations = [
        migrations.RunPython(create_default_category, reverse_code=noop),
        migrations.AddField(
            model_name='group',
            name='default_category',
            field=models.OneToOneField(null=True, to_field=u'id', blank=True, to='argus.Category'),
            preserve_default=True,
        ),
        migrations.RemoveField(
            model_name='group',
            name='use_categories',
        ),
        migrations.RunPython(add_default_category, reverse_code=noop),
    ]
