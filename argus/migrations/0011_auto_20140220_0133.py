# encoding: utf8
from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):
    
    dependencies = [
        ('argus', '0010_auto_20140215_1847'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='slug',
            field=models.CharField(unique=True, max_length=50, validators=[django.core.validators.RegexValidator('[abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_~.]+')]),
        ),
    ]
