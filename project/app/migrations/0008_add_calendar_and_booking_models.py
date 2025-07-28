# Generated manually to fix missing DriverCalendar table

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0007_driverride_driversession_rideanalytics_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DriverCalendar',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True)),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('status', models.CharField(choices=[('available', 'Available'), ('busy', 'Busy'), ('break', 'On Break'), ('offline', 'Offline')], default='available', max_length=20)),
                ('max_rides', models.PositiveIntegerField(default=10)),
                ('current_bookings', models.PositiveIntegerField(default=0)),
                ('zone_preference', models.CharField(blank=True, max_length=100)),
                ('notes', models.TextField(blank=True)),
                ('is_recurring', models.BooleanField(default=False)),
                ('recurring_days', models.JSONField(blank=True, default=list)),
                ('break_times', models.JSONField(blank=True, default=list)),
                ('driver_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='calendar_entries', to='app.driver')),
            ],
            options={
                'ordering': ['date', 'start_time'],
                'indexes': [models.Index(fields=['driver', 'date'], name='app_drivercalendar_driver_date_idx'), models.Index(fields=['date', 'status'], name='app_drivercalendar_date_status_idx')],
                'unique_together': {('driver', 'date', 'start_time')},
            },
        ),
    ]