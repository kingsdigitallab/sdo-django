# Generated by Django 2.2.10 on 2020-03-24 14:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('eats', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='propertyassertion',
            name='entity_relationship',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                       related_name='assertion', to='eats.EntityRelationship'),
        ),
        migrations.AlterField(
            model_name='propertyassertion',
            name='entity_type',
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='assertion', to='eats.EntityType'),
        ),
        migrations.AlterField(
            model_name='propertyassertion',
            name='existence',
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='assertion', to='eats.Existence'),
        ),
        migrations.AlterField(
            model_name='propertyassertion',
            name='generic_property',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                       related_name='assertion', to='eats.GenericProperty'),
        ),
        migrations.AlterField(
            model_name='propertyassertion',
            name='name',
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='assertion', to='eats.Name'),
        ),
        migrations.AlterField(
            model_name='propertyassertion',
            name='name_relationship',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                       related_name='assertion', to='eats.NameRelationship'),
        ),
        migrations.AlterField(
            model_name='propertyassertion',
            name='note',
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='assertion', to='eats.EntityNote'),
        ),
        migrations.AlterField(
            model_name='propertyassertion',
            name='reference',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                       related_name='assertion', to='eats.EntityReference'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='editable_authorities',
            field=models.ManyToManyField(
                blank=True, related_name='editors', to='eats.Authority'),
        ),
    ]
