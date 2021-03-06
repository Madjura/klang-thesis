# Generated by Django 3.0.2 on 2020-09-28 16:05

from django.db import migrations, models
import django.db.models.deletion
import picklefield.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('dataapp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClusterResult',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250)),
                ('nouns_only', models.BooleanField(default=False)),
                ('keywords', picklefield.fields.PickledObjectField(blank=True, editable=False, null=True)),
                ('vectorizer', picklefield.fields.PickledObjectField(blank=True, editable=False, null=True)),
                ('clusterer', picklefield.fields.PickledObjectField(blank=True, editable=False, null=True)),
                ('external', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='ClusterResultCombo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('nouns_only', models.BooleanField(default=False)),
                ('keywords', picklefield.fields.PickledObjectField(blank=True, editable=False, null=True)),
                ('vectorizer', picklefield.fields.PickledObjectField(blank=True, editable=False, null=True)),
                ('clusterer', picklefield.fields.PickledObjectField(blank=True, editable=False, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='KlangInput',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model', picklefield.fields.PickledObjectField(editable=False)),
                ('name', models.CharField(max_length=250, unique=True)),
                ('clusters', models.ManyToManyField(to='klangapp.ClusterResult')),
            ],
        ),
        migrations.CreateModel(
            name='KlangInputCombo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model', picklefield.fields.PickledObjectField(editable=False)),
                ('name', models.CharField(max_length=250, unique=True)),
                ('clusters', models.ManyToManyField(to='klangapp.ClusterResultCombo')),
            ],
        ),
        migrations.CreateModel(
            name='PreprocessedText',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250)),
                ('nouns_only', models.BooleanField(default=False)),
                ('texts', picklefield.fields.PickledObjectField(blank=True, editable=False, null=True)),
                ('external', models.BooleanField(default=False)),
                ('end', models.DateTimeField(blank=True, null=True)),
                ('start', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'unique_together': {('name', 'nouns_only', 'external', 'start', 'end')},
            },
        ),
        migrations.CreateModel(
            name='PreprocessedDocument',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nouns_only', models.BooleanField(default=False)),
                ('texts', picklefield.fields.PickledObjectField(blank=True, editable=False, null=True)),
                ('text', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dataapp.TextEx')),
            ],
        ),
        migrations.CreateModel(
            name='KlangOutputCombo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('relations', picklefield.fields.PickledObjectField(editable=False)),
                ('klang_input', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='klangapp.KlangInputCombo')),
            ],
        ),
        migrations.CreateModel(
            name='KlangOutput',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('relations', picklefield.fields.PickledObjectField(editable=False)),
                ('klang_input', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='klangapp.KlangInput')),
            ],
        ),
        migrations.AddField(
            model_name='clusterresult',
            name='texts',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='klangapp.PreprocessedText'),
        ),
        migrations.AlterUniqueTogether(
            name='clusterresult',
            unique_together={('name', 'nouns_only', 'external', 'texts')},
        ),
    ]
