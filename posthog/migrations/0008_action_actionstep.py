# Generated by Django 2.2.7 on 2020-01-26 21:16

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("posthog", "0007_element"),
    ]

    operations = [
        migrations.CreateModel(
            name="Action",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(blank=True, max_length=400, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "team",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="posthog.Team"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ActionStep",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("tag_name", models.CharField(blank=True, max_length=400, null=True)),
                ("text", models.CharField(blank=True, max_length=400, null=True)),
                ("href", models.CharField(blank=True, max_length=400, null=True)),
                ("selector", models.CharField(blank=True, max_length=400, null=True)),
                ("url", models.CharField(blank=True, max_length=400, null=True)),
                ("name", models.CharField(blank=True, max_length=400, null=True)),
                (
                    "action",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="steps",
                        to="posthog.Action",
                    ),
                ),
            ],
        ),
    ]
