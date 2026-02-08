# management/commands/seed_pack_codes.py

import os
import qrcode
import random
import string
from django.core.management.base import BaseCommand
from club.models import PackCode


def generate_short_code(length=8):
    """
    Generate a short, user-friendly code
    Format: XXXX-XXXX (e.g., AB3K-9M2P)
    Uses uppercase letters and numbers, excludes confusing characters (0,O,1,I,L)
    """
    # Remove confusing characters
    chars = ''.join(set(string.ascii_uppercase + string.digits) - set('0O1IL'))

    # Generate code in segments for readability
    segment1 = ''.join(random.choices(chars, k=4))
    segment2 = ''.join(random.choices(chars, k=4))

    return f"{segment1}-{segment2}"


def generate_numeric_code(length=10):
    """
    Generate a numeric-only code (like phone cards)
    Format: XXXX-XXXX-XX (e.g., 4729-8361-52)
    """
    code = ''.join(random.choices(string.digits, k=length))
    # Format with dashes for readability
    return f"{code[:4]}-{code[4:8]}-{code[8:]}"


class Command(BaseCommand):
    help = "Seed pack codes and generate QR images with short, readable codes"

    def add_arguments(self, parser):
        parser.add_argument('--n', type=int, default=100, help='Number of codes')
        parser.add_argument(
            '--format',
            type=str,
            default='alphanumeric',
            choices=['alphanumeric', 'numeric'],
            help='Code format: alphanumeric (AB3K-9M2P) or numeric (4729-8361-52)'
        )
        parser.add_argument(
            '--length',
            type=int,
            default=8,
            help='Length of code (before formatting with dashes)'
        )

    def handle(self, *args, **options):
        n = options['n']
        code_format = options['format']
        code_length = options['length']

        out_dir = os.path.join('media', 'pack_qr')
        os.makedirs(out_dir, exist_ok=True)

        created_count = 0
        attempts = 0
        max_attempts = n * 10  # Prevent infinite loop

        self.stdout.write(f"Generating {n} pack codes ({code_format} format)...")

        while created_count < n and attempts < max_attempts:
            attempts += 1

            # Generate code based on format
            if code_format == 'numeric':
                new_code = generate_numeric_code(code_length)
            else:  # alphanumeric
                new_code = generate_short_code(code_length)

            # Check if code already exists
            if PackCode.objects.filter(code=new_code).exists():
                continue

            # Create pack code with custom code
            p = PackCode.objects.create(code=new_code)

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(p.code)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Save with sanitized filename (remove dashes for filename)
            safe_filename = p.code.replace('-', '_')
            fname = os.path.join(out_dir, f"{safe_filename}.png")
            img.save(fname)

            created_count += 1

            if created_count % 10 == 0:
                self.stdout.write(f"Created {created_count}/{n} codes...")

        if created_count == n:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✓ Successfully created {n} pack codes and QR images in {out_dir}"
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Format: {code_format}"
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Example codes: {PackCode.objects.order_by('-id')[:3].values_list('code', flat=True)}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠ Only created {created_count}/{n} codes after {attempts} attempts"
                )
            )
