# game/apps.py

from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.core.management import call_command

class GameConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'game'

    def ready(self):
        # Only connect when this config is ready
        post_migrate.connect(load_initial_fixtures, sender=self)

def load_initial_fixtures(sender, **kwargs):
    # Only load for the 'game' app
    if sender.name != 'game':
        return
    # Load all fixtures in one call
    call_command('loaddata', 'elements', 'skills', 'regions', 'trials', verbosity=0)
