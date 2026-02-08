# Create this file: club/management/commands/reset_challenge.py

from django.core.management.base import BaseCommand
from club.models import Challenge, ChallengeWinner

class Command(BaseCommand):
    help = 'Reset a challenge to allow reselecting winners (DANGEROUS - use carefully!)'

    def add_arguments(self, parser):
        parser.add_argument('challenge_id', type=int, help='Challenge ID to reset')
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm you want to delete all winners',
        )

    def handle(self, *args, **options):
        challenge_id = options['challenge_id']
        confirm = options['confirm']

        try:
            challenge = Challenge.objects.get(id=challenge_id)
        except Challenge.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Challenge with ID {challenge_id} does not exist')
            )
            return

        # Count existing winners
        winners = ChallengeWinner.objects.filter(challenge=challenge)
        winner_count = winners.count()

        if winner_count == 0:
            self.stdout.write(
                self.style.WARNING(f'Challenge "{challenge.title}" has no winners to delete')
            )
            return

        self.stdout.write('=' * 60)
        self.stdout.write(f'Challenge: {challenge.title}')
        self.stdout.write(f'Current Status: {challenge.status}')
        self.stdout.write(f'Winners to Delete: {winner_count}')
        self.stdout.write('=' * 60)

        # List winners
        for winner in winners:
            self.stdout.write(
                f'  Position {winner.position}: {winner.profile.phone} '
                f'({winner.profile.first_name} {winner.profile.second_name})'
            )

        self.stdout.write('=' * 60)

        if not confirm:
            self.stdout.write(
                self.style.WARNING('\n⚠️  DRY RUN MODE - No changes made')
            )
            self.stdout.write(
                self.style.WARNING(
                    '\nTo actually reset this challenge, run:\n'
                    f'python manage.py reset_challenge {challenge_id} --confirm'
                )
            )
            return

        # Confirm with user input
        self.stdout.write(
            self.style.WARNING(
                '\n⚠️  WARNING: This will DELETE all winners and reset the challenge!'
            )
        )
        user_input = input('\nType "DELETE" to confirm: ')

        if user_input != 'DELETE':
            self.stdout.write(self.style.ERROR('\n❌ Reset cancelled'))
            return

        # Delete winners
        deleted_count, _ = winners.delete()

        # Reset challenge status
        challenge.status = 'ended'
        challenge.draw_in_progress = False
        challenge.winners_selected_at = None
        challenge.draw_completed_at = None
        challenge.total_entries = 0
        challenge.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Successfully reset challenge "{challenge.title}"'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(f'   - Deleted {deleted_count} winners')
        )
        self.stdout.write(
            self.style.SUCCESS(f'   - Status changed to: {challenge.status}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'   - draw_in_progress: {challenge.draw_in_progress}')
        )
        self.stdout.write('\n✅ You can now start a new live draw for this challenge')
