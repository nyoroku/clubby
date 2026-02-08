import os
import sys
import django

# Setup Django
sys.path.insert(0, r'c:\Users\Administrator\PycharmProjects\clubby')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clubby.settings')
django.setup()

from club.models import PackCode
import random
import string

# Create 20 simple codes
codes_created = []

for i in range(20):
    # Generate simple codes like MELV0001, MELV0002, etc.
    code = f'MELV{str(i+1).zfill(4)}'
    
    # Check if exists
    if PackCode.objects.filter(code=code).exists():
        continue
        
    points = random.choice([20, 25, 30, 35, 50])
    sku = random.choice(['Melvins Premium', 'Melvins Gold', 'Melvins Family'])
    
    pack = PackCode.objects.create(
        code=code,
        sku=sku,
        points=points,
        used=False
    )
    codes_created.append(f'{code} ({points} pts)')

print('\n=== PACK CODES CREATED ===\n')
for c in codes_created:
    print(f'  {c}')
print('\n=== USE ANY CODE ABOVE ===\n')
