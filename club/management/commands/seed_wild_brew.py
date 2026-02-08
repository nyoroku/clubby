"""
Management command to seed "The Wild Brew" limited edition collection
Run with: python manage.py seed_wild_brew
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from club.models import EstateCollection, EstateCard, TeaEstate

class Command(BaseCommand):
    help = 'Seed "The Wild Brew" limited edition seasonal collection'

    def handle(self, *args, **options):
        self.stdout.write("🌿 Creating 'The Wild Brew' seasonal collection...")

        # Create or update collection
        collection, created = EstateCollection.objects.update_or_create(
            name="The Wild Brew",
            defaults={
                'theme': "Experimental & Fusion Blends",
                'description': "Discover our most innovative tea creations. Limited time collection featuring experimental processing methods and rare fusion blends. Available until March 31st!",
                'start_date': timezone.now(),
                'end_date': timezone.now() + timedelta(days=90),  # 3 months
                'is_active': True,
                'total_cards': 8,
                'completion_reward_points': 1000,
                'completion_reward_description': "Complete The Wild Brew collection to win: Weekend trip to Melvins Tea Estate + 1 year supply of premium tea + entry into KES 50,000 grand prize draw!"
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"✅ Created collection: {collection.name}"))
        else:
            self.stdout.write(self.style.WARNING(f"♻️  Updated existing collection: {collection.name}"))

        # Define the 8 cards with varying rarities
        cards_data = [
            {
                'estate_name': 'Kangaita Estate',
                'card_number': 1,
                'rarity': 'common',
                'title': 'Moonlight Dew',
                'flavor_text': 'Hand-picked under moonlight for enhanced floral notes',
                'drop_weight': 1.0,
            },
            {
                'estate_name': 'Kericho Highlands',
                'card_number': 2,
                'rarity': 'common',
                'title': 'Highland Fusion',
                'flavor_text': 'Traditional blend meets modern processing',
                'drop_weight': 1.0,
            },
            {
                'estate_name': 'Nandi Hills Estate',
                'card_number': 3,
                'rarity': 'uncommon',
                'title': 'Sunrise Oxidation',
                'flavor_text': 'Unique dawn-oxidation method creates honey notes',
                'drop_weight': 1.0,
            },
            {
                'estate_name': 'Sotik Valleys',
                'card_number': 4,
                'rarity': 'uncommon',
                'title': 'Valley Mist Reserve',
                'flavor_text': 'Fog-kissed leaves with delicate cloudberry hints',
                'drop_weight': 1.0,
            },
            {
                'estate_name': 'Limuru Estate',
                'card_number': 5,
                'rarity': 'uncommon',
                'title': 'Cold Brew Craft',
                'flavor_text': 'Revolutionary cold-processing technique',
                'drop_weight': 0.8,
            },
            {
                'estate_name': 'Tinderet Slopes',
                'card_number': 6,
                'rarity': 'rare',
                'title': 'Volcanic Terroir',
                'flavor_text': 'Grown in volcanic soil - rich mineral complexity',
                'drop_weight': 1.0,
            },
            {
                'estate_name': 'Aberdare Range',
                'card_number': 7,
                'rarity': 'rare',
                'title': 'Alpine Wildfire',
                'flavor_text': 'Smoked over indigenous hardwood for bold character',
                'drop_weight': 0.5,  # Half as common as other rares
            },
            {
                'estate_name': 'Mount Kenya Estate',
                'card_number': 8,
                'rarity': 'rare',
                'title': 'Glacier Harvest',
                'flavor_text': '⭐ ULTRA RARE: Grown at 2,400m elevation. Only 50 in existence!',
                'drop_weight': 0.1,  # Ultra rare - 10x harder to get than normal rare
            },
        ]

        created_count = 0
        updated_count = 0

        for card_data in cards_data:
            # Get or create the estate
            estate_name = card_data.pop('estate_name')
            estate, _ = TeaEstate.objects.get_or_create(
                name=estate_name,
                defaults={
                    'region': 'Central Kenya',
                    'elevation': '2,000m above sea level',
                    'description': f'Premium estate producing exceptional tea.'
                }
            )

            # Create or update the card
            card, created = EstateCard.objects.update_or_create(
                collection=collection,
                card_number=card_data['card_number'],
                defaults={
                    'estate': estate,
                    'rarity': card_data['rarity'],
                    'title': card_data['title'],
                    'flavor_text': card_data['flavor_text'],
                    'drop_weight': card_data['drop_weight'],
                    'active': True,
                    'frame_color': self.get_rarity_color(card_data['rarity']),
                }
            )

            if created:
                created_count += 1
                self.stdout.write(f"  ✨ Created: {card}")
            else:
                updated_count += 1
                self.stdout.write(f"  🔄 Updated: {card}")

        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"🎉 The Wild Brew Collection Ready!"))
        self.stdout.write(f"   📊 Statistics:")
        self.stdout.write(f"      • Collection: {collection.name}")
        self.stdout.write(f"      • Active: {'Yes ✅' if collection.is_active else 'No ❌'}")
        self.stdout.write(f"      • Duration: {collection.start_date.date()} → {collection.end_date.date()}")
        self.stdout.write(f"      • Cards Created: {created_count}")
        self.stdout.write(f"      • Cards Updated: {updated_count}")
        self.stdout.write(f"      • Total Cards: {collection.cards.count()}")
        
        # Rarity breakdown
        common = collection.cards.filter(rarity='common').count()
        uncommon = collection.cards.filter(rarity='uncommon').count()
        rare = collection.cards.filter(rarity='rare').count()
        
        self.stdout.write(f"   🎴 Rarity Distribution:")
        self.stdout.write(f"      • Common: {common} cards (60% drop rate)")
        self.stdout.write(f"      • Uncommon: {uncommon} cards (30% drop rate)")
        self.stdout.write(f"      • Rare: {rare} cards (10% drop rate)")
        self.stdout.write("="*60)
        
        self.stdout.write(self.style.SUCCESS("\n✅ Setup complete! Users can now discover Wild Brew cards when scanning packs."))

    def get_rarity_color(self, rarity):
        """Return hex color for card frame based on rarity"""
        colors = {
            'common': '#8B4513',    # Saddle Brown
            'uncommon': '#4169E1',  # Royal Blue
            'rare': '#FFD700',      # Gold
        }
        return colors.get(rarity, '#013328')
