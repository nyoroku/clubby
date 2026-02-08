import os
import sys
import django

# Setup Django
sys.path.insert(0, r'c:\Users\Administrator\PycharmProjects\clubby')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clubby.settings')
django.setup()

from club.models import EstateCollection, EstateCard, TeaEstate, PackCode
from django.utils import timezone
from datetime import timedelta
import random

print('\n=== CREATING TEA ESTATES DATA ===\n')

# Create or get the main collection
collection, created = EstateCollection.objects.get_or_create(
    name='Kenya Tea Estates',
    defaults={
        'theme': 'Founders Edition',
        'description': 'Discover the legendary tea estates of Kenya',
        'total_cards': 12,
        'completion_reward_points': 500,
        'is_active': True,
        'start_date': timezone.now() - timedelta(days=30),
        'end_date': timezone.now() + timedelta(days=365),
    }
)

if created:
    print(f'✅ Created collection: {collection.name}')
else:
    print(f'📌 Collection exists: {collection.name}')

# Kenyan Tea Estates
tea_estates_data = [
    {'name': 'Kericho Highlands', 'region': 'Kericho', 'rarity': 'common', 'description': 'Rolling hills of the Kericho tea country'},
    {'name': 'Nandi Hills', 'region': 'Nandi', 'rarity': 'common', 'description': 'Famous for its purple tea'},
    {'name': 'Limuru Estate', 'region': 'Kiambu', 'rarity': 'common', 'description': 'Historic estate near Nairobi'},
    {'name': 'Mount Kenya', 'region': 'Central', 'rarity': 'uncommon', 'description': 'High altitude premium tea'},
    {'name': 'Sotik Valley', 'region': 'Bomet', 'rarity': 'common', 'description': 'Valley tea estates'},
    {'name': 'Nyambene Hills', 'region': 'Meru', 'rarity': 'uncommon', 'description': 'Northern tea frontier'},
    {'name': 'Kiambu Green', 'region': 'Kiambu', 'rarity': 'common', 'description': 'Classic Kiambu green tea'},
    {'name': 'Kisii Highlands', 'region': 'Kisii', 'rarity': 'uncommon', 'description': 'Gusii tea tradition'},
    {'name': 'Trans-Nzoia Sunrise', 'region': 'Trans-Nzoia', 'rarity': 'common', 'description': 'Western Kenya sunrise tea'},
    {'name': 'Murang\'a Mist', 'region': 'Murang\'a', 'rarity': 'uncommon', 'description': 'Misty mountain tea'},
    {'name': 'Kapkatet Gold', 'region': 'Kericho', 'rarity': 'rare', 'description': 'Premium golden tea'},
    {'name': 'Michuki Reserve', 'region': 'Central', 'rarity': 'rare', 'description': 'Exclusive limited edition'},
]

cards_created = 0
for i, data in enumerate(tea_estates_data):
    # First create/get the TeaEstate
    estate, _ = TeaEstate.objects.get_or_create(
        name=data['name'],
        defaults={
            'region': data['region'],
            'description': data['description'],
            'active': True,
        }
    )
    
    # Then create/get the EstateCard
    card, created = EstateCard.objects.get_or_create(
        card_number=i+1,
        collection=collection,
        defaults={
            'estate': estate,
            'rarity': data['rarity'],
            'active': True,
        }
    )
    if created:
        cards_created += 1
        print(f'  🃏 Card #{i+1}: {data["name"]} ({data["rarity"]})')

print(f'\n✅ Created {cards_created} cards')


# Create pack codes
print('\n=== CREATING PACK CODES ===\n')

codes_created = 0
for i in range(20):
    code = f'MELV{str(i+1).zfill(4)}'
    if not PackCode.objects.filter(code=code).exists():
        points = random.choice([20, 25, 30, 35, 50])
        PackCode.objects.create(
            code=code,
            sku='Melvins Premium',
            points=points,
            used=False
        )
        codes_created += 1
        print(f'  📦 {code} ({points} pts)')

print(f'\n✅ Created {codes_created} pack codes')
print('\n=== READY! Use codes MELV0001 to MELV0020 ===\n')
