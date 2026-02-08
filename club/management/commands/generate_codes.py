import uuid
import os
from django.core.management.base import BaseCommand
from club.models import PackCode

class Command(BaseCommand):
    help = 'Generate batch of pack codes for printing or distribution'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of codes to generate'
        )
        parser.add_argument(
            '--points',
            type=int,
            default=10,
            help='Points value for each code'
        )
        parser.add_argument(
            '--sku',
            type=str,
            default='Melvins',
            help='SKU identifier for this batch'
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Path to save the generated codes (e.g., C:/Users/Administrator/Desktop/codes.txt)'
        )

    def handle(self, *args, **options):
        count = options['count']
        points = options['points']
        sku = options['sku']
        file_path = options['file']

        self.stdout.write(f"Generating {count} codes for SKU '{sku}' with {points} points each...")

        # Prepare objects for bulk creation
        pack_codes = []
        generated_codes_list = []

        for _ in range(count):
            # Generate code in format MEL-W-XXXXXX
            random_suffix = uuid.uuid4().hex[:8].upper()
            code = f"MEL-W-{random_suffix}"
            generated_codes_list.append(code)
            
            pack_codes.append(PackCode(
                code=code,
                sku=sku,
                points=points,
                used=False
            ))

        # Bulk create for performance
        PackCode.objects.bulk_create(pack_codes)

        self.stdout.write(self.style.SUCCESS(f"Successfully created {count} codes in database."))

        # Output logic
        if file_path:
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                
                with open(file_path, 'w') as f:
                    f.write("Code,SKU,Points\n")  # CSV Header
                    for code in generated_codes_list:
                        f.write(f"{code},{sku},{points}\n")
                
                self.stdout.write(self.style.SUCCESS(f"Codes saved to {file_path}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to save to file: {e}"))
                # Fallback to printing if file save fails
                self.stdout.write("Codes:")
                for code in generated_codes_list:
                    self.stdout.write(code)
        else:
            self.stdout.write("\nGenerated Codes:")
            self.stdout.write("-" * 40)
            for code in generated_codes_list:
                self.stdout.write(code)
            self.stdout.write("-" * 40)
