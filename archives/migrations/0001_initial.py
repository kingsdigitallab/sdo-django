# Generated by Django 2.2.10 on 2020-02-13 14:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Collection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='The name by which this collection is currently known', max_length=200, verbose_name='Name')),
                ('name_supplied', models.BooleanField(help_text='Indicate if the collection name is supplied by the Schenker Documents Online project', verbose_name='Collection name supplied?')),
                ('identifier', models.CharField(blank=True, help_text='The code used to refer to this collection in shelfmarks and other identifying information', max_length=15)),
                ('description', models.TextField(blank=True, help_text='As required, other descriptive information about this collection')),
            ],
        ),
        migrations.CreateModel(
            name='Container',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content_type', models.CharField(choices=[('1', 'Correspondence'), ('2', 'Diary'), ('3', 'Lessonbook'), ('4', 'Other'), ('5', 'Mixed')], help_text='Indicate the kind of material included in this container.', max_length=1, verbose_name='Content Type')),
                ('series', models.CharField(blank=True, help_text='As required, enter the series identifier for the container', max_length=15)),
                ('box', models.CharField(blank=True, help_text='As required, enter the box identifier for the container', max_length=15)),
                ('folder', models.CharField(blank=True, help_text='As required, enter the folder identifier for the container', max_length=15, verbose_name='Folder')),
                ('description', models.TextField(blank=True, help_text='As required, other descriptive information about this container')),
                ('collection', models.ForeignKey(help_text='Select the collection to which this container belongs; click the green plus sign (+) to add a new repository to the archive', on_delete=django.db.models.deletion.CASCADE, to='archives.Collection')),
            ],
            options={
                'unique_together': {('collection', 'box', 'folder')},
            },
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('unitid', models.CharField(help_text='Alpha-numeric text string that serves as a unique reference point or control number for the digital item representing the physical material', max_length=10, verbose_name='ID')),
                ('coverage_start', models.DateField(blank=True, verbose_name='Start Date')),
                ('coverage_end', models.DateField(blank=True, null=True, verbose_name='End Date')),
                ('id_supplied', models.BooleanField(help_text='Indicate whether or not this id is supplied by the Schenker Documents Online project; leaving this unchecked indicates that the document ID is drawn from information maintained by the holding institution', verbose_name='Doc ID supplied?')),
                ('description', models.CharField(blank=True, help_text='As required, enter a brief descriptive note about this document', max_length=200)),
                ('container', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='archives.Container')),
            ],
            options={
                'unique_together': {('container', 'unitid')},
            },
        ),
        migrations.CreateModel(
            name='Repository',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Enter the current name of the repository', max_length=400)),
                ('identifier', models.CharField(blank=True, help_text='Add an identifier for this repository, e.g. NYPL', max_length=10)),
                ('rism_identifier', models.CharField(blank=True, help_text='Add the RISM identifier for this repository, e.g. US-NYp', max_length=10)),
                ('description', models.TextField(blank=True, help_text='As required, enter additional descriptive text about this repository')),
            ],
            options={
                'verbose_name_plural': 'Repositories',
            },
        ),
        migrations.CreateModel(
            name='DocumentStatements',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('statement_type', models.CharField(choices=[('1', 'Format'), ('2', 'Provenance'), ('3', 'Rights Holder'), ('4', 'License')], help_text='Indicate the kind of statement being made about this container', max_length=1)),
                ('description', models.TextField(help_text='Make a statement about this document')),
                ('document_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='document_statements', to='archives.Document')),
            ],
            options={
                'verbose_name_plural': 'Document Statements',
            },
        ),
        migrations.CreateModel(
            name='ContainerStatements',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('statement_type', models.CharField(choices=[('1', 'Format'), ('2', 'Provenance'), ('3', 'Rights Holder'), ('4', 'License')], help_text='Indicate the kind of statement being made about this container', max_length=1)),
                ('description', models.TextField(help_text='Make a statement about this container')),
                ('container_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='container_statements', to='archives.Container')),
            ],
            options={
                'verbose_name_plural': 'Container Statements',
            },
        ),
        migrations.CreateModel(
            name='CollectionStatements',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('statement_type', models.CharField(choices=[('1', 'Format'), ('2', 'Provenance'), ('3', 'Rights Holder'), ('4', 'License')], help_text='Indicate the kind of statement being made about this collection', max_length=1)),
                ('description', models.CharField(help_text='Make a statement about the collection', max_length=400)),
                ('collection_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='archives.Collection')),
            ],
            options={
                'verbose_name_plural': 'Collection Statements',
            },
        ),
        migrations.AddField(
            model_name='collection',
            name='repository',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='archives.Repository'),
        ),
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address_type', models.CharField(choices=[('1', 'Street Address'), ('2', 'Postal Address'), ('3', 'Web Address')], help_text='Indicate the kind of address', max_length=1)),
                ('address1', models.CharField(help_text='First line of the address', max_length=300, verbose_name='Address Line 1')),
                ('address2', models.CharField(blank=True, help_text='Additional address information as required', max_length=300, verbose_name='Address Line 2')),
                ('city', models.CharField(blank=True, max_length=100)),
                ('province', models.CharField(blank=True, help_text='Province, State, or other regional indicator', max_length=100, verbose_name='Province/State')),
                ('country', models.CharField(blank=True, max_length=100)),
                ('postal_code', models.CharField(blank=True, help_text='Postal, ZIP or other mailing code', max_length=12, verbose_name='Postal/Zip Code')),
                ('note', models.TextField(blank=True)),
                ('address', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='archives.Repository')),
            ],
            options={
                'verbose_name_plural': 'Addresses',
            },
        ),
        migrations.AlterUniqueTogether(
            name='collection',
            unique_together={('repository', 'name')},
        ),
    ]