# encoding: utf8
from django.db import models, migrations


class Migration(migrations.Migration):
    
    dependencies = [
        ('argus', '0009_auto_20140215_1833'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='memo',
            field=models.CharField(max_length=64),
        ),
    ]
