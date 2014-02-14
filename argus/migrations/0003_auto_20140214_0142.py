# encoding: utf8
from django.db import models, migrations


class Migration(migrations.Migration):
    
    dependencies = [
        ('argus', '0002_auto_20140206_0918'),
    ]

    operations = [
        migrations.AlterField(
            model_name='share',
            name='portion',
            field=models.DecimalField(max_digits=5, decimal_places=4),
        ),
        migrations.AlterField(
            model_name='group',
            name='custom_slug',
            field=models.SlugField(max_length=30, blank=True),
        ),
        migrations.AlterField(
            model_name='group',
            name='auto_slug',
            field=models.SlugField(max_length=15),
        ),
        migrations.AlterField(
            model_name='group',
            name='email',
            field=models.EmailField(max_length=75, blank=True),
        ),
    ]
