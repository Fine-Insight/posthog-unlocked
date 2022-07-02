# Generated by Django 3.2.5 on 2022-02-04 17:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("posthog", "0204_remove_duplicate_plugin_configs"),
    ]

    operations = [
        migrations.AddField(model_name="cohort", name="version", field=models.IntegerField(blank=True, null=True),),
        migrations.AddField(
            model_name="cohort", name="pending_version", field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="cohortpeople", name="version", field=models.IntegerField(blank=True, null=True),
        ),
    ]
