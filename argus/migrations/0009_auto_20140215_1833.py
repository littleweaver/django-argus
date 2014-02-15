# encoding: utf8
from django.db import models, migrations


class Migration(migrations.Migration):
    
    dependencies = [
        ('argus', '0008_auto_20140215_0803'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='split',
            field=models.CharField(default='manual', max_length=7, choices=[('payment', u'Member-to-member payment'), ('even', u'Even split'), ('manual', u'Manual entry')]),
            preserve_default=True,
        ),
        migrations.RemoveField(
            model_name='expense',
            name='is_payment',
        ),
        migrations.RemoveField(
            model_name='expense',
            name='is_even',
        ),
        migrations.AlterField(
            model_name='expense',
            name='memo',
            field=models.CharField(max_length=64, blank=True),
        ),
    ]
