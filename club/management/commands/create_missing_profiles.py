from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from club.models import Profile

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates missing profiles for users'

    def handle(self, *args, **kwargs):
        users = User.objects.all()
        created_count = 0
        
        for user in users:
            try:
                # Check if profile exists
                profile = user.profile
                self.stdout.write(self.style.SUCCESS(f'Profile exists for user: {user.username}'))
            except Profile.DoesNotExist:
                # Create profile if missing
                Profile.objects.create(user=user)
                created_count += 1
                self.stdout.write(self.style.WARNING(f'Created missing profile for user: {user.username}'))
                
        self.stdout.write(self.style.SUCCESS(f'Successfully created {created_count} missing profiles'))
