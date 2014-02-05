# encoding: utf8
from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):
    
    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Group',
            fields=[
                (u'id', models.AutoField(verbose_name=u'ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=75)),
                ('name', models.CharField(max_length=64)),
                ('custom_slug', models.CharField(max_length=30)),
                ('auto_slug', models.CharField(max_length=30)),
                ('password', models.CharField(max_length=128, blank=True)),
                ('use_categories', models.BooleanField(default=False)),
                ('currency', models.CharField(default='USD', max_length=3)),
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
            name='Member',
            fields=[
                (u'id', models.AutoField(verbose_name=u'ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
                ('group', models.ForeignKey(to='argus.Group', to_field=u'id')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                (u'id', models.AutoField(verbose_name=u'ID', serialize=False, auto_created=True, primary_key=True)),
                ('from_member', models.ForeignKey(to='argus.Member', to_field=u'id')),
                ('to_member', models.ForeignKey(to='argus.Member', to_field=u'id')),
                ('amount', models.DecimalField(max_digits=11, decimal_places=2)),
                ('paid_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Recipient',
            fields=[
                (u'id', models.AutoField(verbose_name=u'ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=64)),
                ('group', models.ForeignKey(to='argus.Group', to_field=u'id')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Expense',
            fields=[
                (u'id', models.AutoField(verbose_name=u'ID', serialize=False, auto_created=True, primary_key=True)),
                ('member', models.ForeignKey(to='argus.Member', to_field=u'id')),
                ('recipient', models.ForeignKey(to='argus.Recipient', to_field=u'id')),
                ('memo', models.CharField(max_length=64)),
                ('cost', models.DecimalField(max_digits=11, decimal_places=2)),
                ('paid_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('category', models.ForeignKey(to_field=u'id', blank=True, to='argus.Category', null=True)),
                ('notes', models.TextField(blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Share',
            fields=[
                (u'id', models.AutoField(verbose_name=u'ID', serialize=False, auto_created=True, primary_key=True)),
                ('expense', models.ForeignKey(to='argus.Expense', to_field=u'id')),
                ('member', models.ForeignKey(to='argus.Member', to_field=u'id')),
                ('percentage', models.FloatField(null=True, blank=True)),
                ('amount', models.DecimalField(max_digits=11, decimal_places=2)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
