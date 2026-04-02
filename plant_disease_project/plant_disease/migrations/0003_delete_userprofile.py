from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('plant_disease', '0002_passwordresettoken'),
    ]

    operations = [
        migrations.DeleteModel(
            name='UserProfile',
        ),
    ]
