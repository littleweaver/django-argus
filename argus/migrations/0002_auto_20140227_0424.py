# encoding: utf8
from django.db import models, migrations


class Migration(migrations.Migration):
    
    dependencies = [
        ('argus', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='transaction',
            old_name='source',
            new_name='paid_by',
        ),
        migrations.AddField(
            model_name='transaction',
            name='paid_to',
            field=models.ForeignKey(to_field=u'id', blank=True, to='argus.Party', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='party',
            name='party_type',
            field=models.CharField(default='sink', max_length=11, choices=[('sink', u'Expense source'), ('member', u'Member')]),
        ),
    ]
