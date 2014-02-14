# encoding: utf8
from django.db import models, migrations


class Migration(migrations.Migration):
    
    dependencies = [
        ('argus', '0006_auto_20140214_0841'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='confirmed_email',
            field=models.EmailField(default='', max_length=75, blank=True),
            preserve_default=False,
        ),
    ]
