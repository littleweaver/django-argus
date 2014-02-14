# encoding: utf8
from django.db import models, migrations


class Migration(migrations.Migration):
    
    dependencies = [
        ('argus', '0003_auto_20140214_0142'),
    ]

    operations = [
        migrations.RenameField(
            model_name='group',
            old_name='auto_slug',
            new_name='slug'
        ),
        migrations.RemoveField(
            model_name='group',
            name='custom_slug',
        ),
    ]
