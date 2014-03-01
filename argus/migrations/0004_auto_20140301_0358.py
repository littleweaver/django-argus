# encoding: utf8
from django.db import models, migrations


def noop(apps, schema_editor):
    pass


def assign_default_category(apps, schema_editor):
    Group = apps.get_model("argus", "Group")
    Transaction = apps.get_model("argus", "Transaction")

    for group in Group.objects.all():
        qs = Transaction.objects.filter(paid_by__group=group,
                                        category__isnull=True)
        qs.update(category=group.default_category)


class Migration(migrations.Migration):

    dependencies = [
        ('argus', '0003_auto_20140301_0215'),
    ]

    operations = [
        migrations.RunPython(assign_default_category, reverse_code=noop),
        migrations.AlterField(
            model_name='transaction',
            name='category',
            field=models.ForeignKey(to='argus.Category', to_field=u'id'),
        ),
    ]
