from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('club', '0012_alter_profile_phone'),
    ]

    operations = [
        # 1. Remove the old field from Django state ONLY (don't run SQL to drop it)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='listingpartner',
                    name='Melvins_commission_earned',
                ),
            ],
            database_operations=[
                # Use RunSQL with no-op to document we are skipping drop
                migrations.RunSQL(
                    sql=migrations.RunSQL.noop,
                    reverse_sql=migrations.RunSQL.noop
                ),
            ],
        ),
        # 2. Add the new field to both state and DB (this runs SQL to add column)
        migrations.AddField(
            model_name='listingpartner',
            name='melvins_commission_earned',
            field=models.DecimalField(decimal_places=2, default=0.0, help_text='Total commission earned by Melvins', max_digits=12),
        ),
    ]
