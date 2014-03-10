# encoding: utf8
from django.db import models, migrations


def percent_to_numdenom(apps, schema_editor):
    Share = apps.get_model("argus", "Share")
    for share in Share.objects.all():
        share.denominator = 10000
        share.numerator = share.portion * 10000
        share.fraction_is_manual = share.portion_is_manual
        share.save()


class Migration(migrations.Migration):

    dependencies = [
        ('argus', '0004_auto_20140301_0358'),
    ]

    operations = [
        migrations.AddField(
            model_name='share',
            name='denominator',
            field=models.PositiveIntegerField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='share',
            name='numerator',
            field=models.PositiveIntegerField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='share',
            name='fraction_is_manual',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.RunPython(percent_to_numdenom),
        migrations.RemoveField(
            model_name='share',
            name='portion_is_manual',
        ),
        migrations.RemoveField(
            model_name='share',
            name='portion',
        ),
    ]
