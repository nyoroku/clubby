# Generated manually to match user's server migration
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('club', '0011_add_card_reward_points'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='phone',
            field=models.CharField(blank=True, max_length=24, null=True, unique=True),
        ),
    ]
