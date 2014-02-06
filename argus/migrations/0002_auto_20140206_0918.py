# encoding: utf8
from django.db import models, migrations


class Migration(migrations.Migration):
    
    dependencies = [
        ('argus', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Payment',
        ),
        migrations.AddField(
            model_name='expense',
            name='is_payment',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='share',
            name='portion_is_manual',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='share',
            name='portion',
            field=models.DecimalField(default=0, max_digits=4, decimal_places=4),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='expense',
            name='is_even',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='share',
            name='amount_is_manual',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.RemoveField(
            model_name='share',
            name='percentage',
        ),
        migrations.AlterField(
            model_name='expense',
            name='recipient',
            field=models.ForeignKey(to_field=u'id', blank=True, to='argus.Recipient', null=True),
        ),
    ]
