"""
Management command to seed the permanent "Tea Estates of Kenya" base collection
Run with: python manage.py seed_base_collection
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from club.models import EstateCollection, EstateCard, TeaEstate

class Command(BaseCommand):
    help = 'Seed permanent "Tea Estates of Kenya" base collection'

    def handle(self, *args, **options):
        self.stdout.write("🍵 Creating permanent 'Tea Estates of Kenya' collection...")

        # Create or update base collection (runs for 10 years - effectively permanent)
        collection, created = EstateCollection.objects.update_or_create(
            name="Tea Estates of Kenya",
            defaults={
                'theme': "Discover Kenya's Finest Tea Regions",
                'description': "Your journey through Kenya's legendary tea estates. Collect all 12 cards to unlock exclusive rewards and prove your tea expertise!",
                'start_date': timezone.now(),
                'end_date': timezone.now() + timedelta(days=3650),  # 10 years
                'is_active': True,
                'total_cards': 12,
                'completion_reward_points': 500,
                'completion_reward_description': "Complete the base collection to earn: 500 bonus points + Exclusive Melvins Tea Connoisseur Badge + Free premium tea gift box!"
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"✅ Created collection: {collection.name}"))
        else:
            self.stdout.write(self.style.WARNING(f"♻️  Updated existing collection: {collection.name}"))

        # Define 12 cards representing major Kenyan tea regions
        cards_data = [
            # Common cards (60% - 7 cards)
            {
                'estate_name': 'Kericho Estate',
                'region': 'Rift Valley',
                'card_number': 1,
                'rarity': 'common',
                'title': 'Golden Slopes',
                'flavor_text': 'Kenya\'s tea capital, where rolling hills meet golden sunshine',
            },
            {
                'estate_name': 'Nandi Hills Estate',
                'region': 'Rift Valley',
                'card_number': 2,
                'rarity': 'common',
                'title': 'Highland Heritage',
                'flavor_text': 'Historic estate producing smooth, balanced teas since 1912',
            },
            {
                'estate_name': 'Sotik Valleys',
                'region': 'Rift Valley',
                'card_number': 3,
                'rarity': 'common',
                'title': 'Valley Mist',
                'flavor_text': 'Morning fog creates the perfect microclimate for delicate leaves',
            },
            {
                'estate_name': 'Kangaita Estate',
                'region': 'Central Kenya',
                'card_number': 4,
                'rarity': 'common',
                'title': 'Mountain Fresh',
                'flavor_text': 'Crisp highland air produces bright, refreshing character',
            },
            {
                'estate_name': 'Limuru Estate',
                'region': 'Central Kenya',
                'card_number': 5,
                'rarity': 'common',
                'title': 'Colonial Legacy',
                'flavor_text': 'One of Kenya\'s oldest estates, crafting tea since 1903',
            },
            {
                'estate_name': 'Tinderet Estate',
                'region': 'Western Kenya',
                'card_number': 6,
                'rarity': 'common',
                'title': 'Western Jewel',
                'flavor_text': 'Rich volcanic soil yields full-bodied, robust flavor',
            },
            {
                'estate_name': 'Marinyn Estate',
                'region': 'Rift Valley',
                'card_number': 7,
                'rarity': 'common',
                'title': 'Sunrise Harvest',
                'flavor_text': 'First light picking ensures maximum freshness and aroma',
            },
            
            # Uncommon cards (30% - 3 cards)
            {
                'estate_name': 'Aberdare Range Estate',
                'region': 'Central Highlands',
                'card_number': 8,
                'rarity': 'uncommon',
                'title': 'Cloud Forest Reserve',
                'flavor_text': 'Grown amidst pristine mountain forests at 2,100m elevation',
            },
            {
                'estate_name': 'Mau Summit Estate',
                'region': 'Rift Valley',
                'card_number': 9,
                'rarity': 'uncommon',
                'title': 'Peak Selection',
                'flavor_text': 'Extreme altitude creates concentrated, complex flavors',
            },
            {
                'estate_name': 'Nyambene Hills',
                'region': 'Eastern Kenya',
                'card_number': 10,
                'rarity': 'uncommon',
                'title': 'Eastern Promise',
                'flavor_text': 'Unique terroir produces distinctive fruity undertones',
            },
            
            # Rare cards (10% - 2 cards)
            {
                'estate_name': 'Mount Kenya Estate',
                'region': 'Mount Kenya Foothills',
                'card_number': 11,
                'rarity': 'rare',
                'title': 'Glacial Peaks',
                'flavor_text': '⭐ Kenya\'s highest tea estate! Snowmelt irrigation creates unmatched purity',
            },
            {
                'estate_name': 'Kakamega Rainforest Estate',
                'region': 'Western Kenya',
                'card_number': 12,
                'rarity': 'rare',
                'title': 'Rainforest Secret',
                'flavor_text': '⭐ RARE: Kenya\'s only rainforest tea! Wild ecosystem creates magical notes',
            },
        ]

        created_count = 0
        updated_count = 0

        for card_data in cards_data:
            # Get or create the estate
            estate, _ = TeaEstate.objects.get_or_create(
                name=card_data['estate_name'],
                defaults={
                    'region': card_data['region'],
                    'elevation': '1,800m' if card_data['rarity'] == 'common' else ('2,100m' if card_data['rarity'] == 'uncommon' else '2,400m above sea level'),
                    'description': f"Premium {card_data['region']} estate producing exceptional {card_data['rarity']} grade tea."
                }
            )

            # Create or update the card
            card, card_created = EstateCard.objects.update_or_create(
                collection=collection,
                card_number=card_data['card_number'],
                defaults={
                    'estate': estate,
                    'rarity': card_data['rarity'],
                    'title': card_data['title'],
                    'flavor_text': card_data['flavor_text'],
                    'drop_weight': 1.0,  # Standard weight for base collection
                    'active': True,
                    'frame_color': self.get_rarity_color(card_data['rarity']),
                }
            )

            if card_created:
                created_count += 1
                self.stdout.write(f"  ✨ Created: {card}")
            else:
                updated_count += 1
                self.stdout.write(f"  🔄 Updated: {card}")

        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"🎉 Tea Estates of Kenya Collection Ready!"))
        self.stdout.write(f"   📊 Statistics:")
        self.stdout.write(f"      • Collection: {collection.name}")
        self.stdout.write(f"      • Status: Permanent Base Collection")
        self.stdout.write(f"      • Cards Created: {created_count}")
        self.stdout.write(f"      • Cards Updated: {updated_count}")
        self.stdout.write(f"      • Total Cards: {collection.cards.count()}")
        
        # Rarity breakdown
        common = collection.cards.filter(rarity='common').count()
        uncommon = collection.cards.filter(rarity='uncommon').count()
        rare = collection.cards.filter(rarity='rare').count()
        
        self.stdout.write(f"   🎴 Rarity Distribution:")
        self.stdout.write(f"      • Common: {common} cards (~60% drop rate)")
        self.stdout.write(f"      • Uncommon: {uncommon} cards (~30% drop rate)")
        self.stdout.write(f"      • Rare: {rare} cards (~10% drop rate)")
        self.stdout.write("="*60)
        
        self.stdout.write(self.style.SUCCESS("\n✅ Base collection ready! This will always be available to users."))

    def get_rarity_color(self, rarity):
        """Return hex color for card frame based on rarity"""
        colors = {
            'common': '#8B4513',    # Saddle Brown
            'uncommon': '#4169E1',  # Royal Blue
            'rare': '#FFD700',      # Gold
        }
        return colors.get(rarity, '#013328')
