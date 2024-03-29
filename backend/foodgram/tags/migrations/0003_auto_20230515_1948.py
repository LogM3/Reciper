# Generated by Django 3.2.18 on 2023-05-15 16:48

import tags.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tags', '0002_alter_tag_color'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tag',
            options={'ordering': ['id'], 'verbose_name': 'Тег', 'verbose_name_plural': 'Теги'},
        ),
        migrations.AlterField(
            model_name='tag',
            name='color',
            field=models.CharField(max_length=7, validators=[tags.validators.hex_color_validate], verbose_name='Цвет'),
        ),
        migrations.AlterField(
            model_name='tag',
            name='name',
            field=models.CharField(max_length=200, unique=True, verbose_name='Название'),
        ),
        migrations.AlterField(
            model_name='tag',
            name='slug',
            field=models.SlugField(max_length=200, verbose_name='Слаг'),
        ),
    ]
