# encoding: utf8
from django.db import models, migrations


def copy_manualness(apps, schema_editor):
    Transaction = apps.get_model("argus", "Transaction")
    fractions = Transaction.objects.filter(split='manual',
                                           share__fraction_is_manual=True)
    fractions.update(split='percent')
    amounts = Transaction.objects.filter(split='manual',
                                         share__amount_is_manual=True)
    amounts.update(split='amount')


class Migration(migrations.Migration):

    dependencies = [
        ('argus', '0005_switch_to_numerator_denominator'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='split',
            field=models.CharField(default='even', max_length=7, choices=[('simple', u'Simple payment'), ('even', u'Even split'), ('percent', u'Manual percentages'), ('amount', u'Manual amounts'), ('shares', u'Manual shares')]),
        ),
        migrations.RunPython(copy_manualness),
        migrations.RemoveField(
            model_name='share',
            name='amount_is_manual',
        ),
        migrations.RemoveField(
            model_name='share',
            name='fraction_is_manual',
        ),
    ]
