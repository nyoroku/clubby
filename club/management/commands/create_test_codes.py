from django.core.management.base import BaseCommand
from club.models import PackCode
import random
import string


class Command(BaseCommand):
    help = 'Generate test pack codes for Melvins Club'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of codes to generate (default: 10)'
        )
        parser.add_argument(
            '--points',
            type=int,
            default=25,
            help='Points per code (default: 25)'
        )
        parser.add_argument(
            '--sku',
            type=str,
            default=None,
            help='Specific SKU for all codes (default: random Melvins variety)'
        )

    def handle(self, *args, **options):
        count = options['count']
        points = options['points']
        sku_arg = options['sku']
        
        sku_options = [
            'Melvins Premium',
            'Melvins Gold',
            'Melvins Family',
            'Melvins Green',
            'Melvins Breakfast',
        ]
        
        created_codes = []
        
        for i in range(count):
            # Generate a memorable code like MELV-XXXX-XXXX
            code_part1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            code_part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            code = f'MELV-{code_part1}-{code_part2}'
            
            # Use provided SKU or pick random
            final_sku = sku_arg if sku_arg else random.choice(sku_options)
            
            # Vary points slightly
            point_value = points + random.choice([-5, 0, 0, 5, 10, 25])
            
            pack = PackCode.objects.create(
                code=code,
                sku=final_sku,
                points=max(10, point_value),  # Minimum 10 points
            )
            created_codes.append(pack)
            
        self.stdout.write(self.style.SUCCESS(f'\n✅ Created {count} pack codes:\n'))
        
        for pack in created_codes:
            self.stdout.write(f'  📦 {pack.code} ({pack.sku}) - {pack.points} pts')
        
        self.stdout.write(self.style.SUCCESS(f'\nCopy any code above and use it to scan!'))
