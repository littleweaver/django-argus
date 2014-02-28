# encoding: utf8
from django.db import models, migrations
import django.utils.timezone
import django.core.validators


class Migration(migrations.Migration):
    
    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Group',
            fields=[
                (u'id', models.AutoField(verbose_name=u'ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.CharField(unique=True, max_length=50, validators=[django.core.validators.RegexValidator('[\\w_~\\.-]+')])),
                ('name', models.CharField(max_length=64, blank=True)),
                ('email', models.EmailField(max_length=75, blank=True)),
                ('confirmed_email', models.EmailField(max_length=75, blank=True)),
                ('password', models.CharField(max_length=128, blank=True)),
                ('use_categories', models.BooleanField(default=False)),
                ('currency', models.CharField(default='USD', max_length=3)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                (u'id', models.AutoField(verbose_name=u'ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=64)),
                ('group', models.ForeignKey(to='argus.Group', to_field=u'id')),
            ],
            options={
                u'verbose_name_plural': 'categories',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Party',
            fields=[
                (u'id', models.AutoField(verbose_name=u'ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
                ('group', models.ForeignKey(to='argus.Group', to_field=u'id')),
                ('party_type', models.CharField(default='source_sink', max_length=11, choices=[('source', u'Income source'), ('sink', u'Transaction source'), ('source_sink', u'Transaction and income source'), ('member', u'Member')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                (u'id', models.AutoField(verbose_name=u'ID', serialize=False, auto_created=True, primary_key=True)),
                ('source', models.ForeignKey(to='argus.Party', to_field=u'id')),
                ('memo', models.CharField(max_length=64)),
                ('amount', models.DecimalField(max_digits=11, decimal_places=2)),
                ('paid_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('category', models.ForeignKey(to_field=u'id', blank=True, to='argus.Category', null=True)),
                ('notes', models.TextField(blank=True)),
                ('split', models.CharField(default='manual', max_length=7, choices=[('simple', u'Simple payment'), ('even', u'Even split'), ('manual', u'Manual entry')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Share',
            fields=[
                (u'id', models.AutoField(verbose_name=u'ID', serialize=False, auto_created=True, primary_key=True)),
                ('transaction', models.ForeignKey(to='argus.Transaction', to_field=u'id')),
                ('party', models.ForeignKey(to='argus.Party', to_field=u'id')),
                ('portion', models.DecimalField(max_digits=5, decimal_places=4)),
                ('portion_is_manual', models.BooleanField(default=False)),
                ('amount', models.DecimalField(max_digits=11, decimal_places=2)),
                ('amount_is_manual', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
