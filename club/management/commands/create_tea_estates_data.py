"""
Management command to generate sample Tea Estates data for Melvins Club.
Run: python manage.py create_tea_estates_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from club.models import TeaEstate, EstateCollection, EstateCard


class Command(BaseCommand):
    help = 'Creates sample Tea Estates, Collections, and Cards for Melvins Club'

    def handle(self, *args, **options):
        self.stdout.write('Creating Tea Estates...')
        
        # Create Tea Estates representing real Kenyan tea regions
        estates_data = [
            {
                'name': 'Kericho Valley Estate',
                'region': 'Kericho',
                'description': 'Nestled in the rolling hills of Kenya\'s premier tea-growing region, Kericho Valley Estate produces some of the finest black teas in the world. The consistent rainfall and rich volcanic soil create perfect growing conditions.',
                'elevation': '2,100m above sea level',
                'tasting_notes': 'Bright golden liquor with malty undertones, hints of honey and citrus',
                'brewing_tips': 'Brew at 95°C for 3-4 minutes. Best enjoyed with a splash of milk.',
                'harvest_season': 'Year-round, peak harvest January-March',
                'latitude': -0.3689,
                'longitude': 35.2863,
            },
            {
                'name': 'Nandi Highlands Estate',
                'region': 'Nandi Hills',
                'description': 'The highland mists of Nandi create a unique microclimate where tea bushes thrive. This estate has been producing award-winning teas since 1924, combining tradition with modern sustainability practices.',
                'elevation': '1,900m above sea level',
                'tasting_notes': 'Full-bodied with robust character, notes of black pepper and stone fruit',
                'brewing_tips': 'Use fresh, filtered water at 90°C. Steep for 4 minutes for optimal flavor.',
                'harvest_season': 'March-May (main), October-December (secondary)',
                'latitude': 0.1833,
                'longitude': 35.1333,
            },
            {
                'name': 'Mount Kenya Reserve',
                'region': 'Mount Kenya',
                'description': 'Growing in the shadow of Africa\'s second-highest peak, Mount Kenya Reserve produces rare high-altitude teas with exceptional depth and complexity. The snow-fed streams and mineral-rich soils create teas of extraordinary quality.',
                'elevation': '2,400m above sea level',
                'tasting_notes': 'Delicate floral notes with muscatel character, clean finish',
                'brewing_tips': 'Slightly cooler water at 85°C brings out the delicate notes. Steep 3 minutes.',
                'harvest_season': 'April-June (first flush), September-November (second flush)',
                'latitude': -0.1521,
                'longitude': 37.3084,
            },
            {
                'name': 'Limuru Heritage Estate',
                'region': 'Limuru',
                'description': 'One of Kenya\'s oldest tea estates, Limuru Heritage represents over a century of tea cultivation. The cool highland climate and red volcanic soils produce teas with distinctive character and remarkable consistency.',
                'elevation': '2,200m above sea level',
                'tasting_notes': 'Brisk and lively with hints of fresh grass and wildflowers',
                'brewing_tips': 'Perfect for afternoon tea. Brew 3-4 minutes, excellent with lemon.',
                'harvest_season': 'Year-round production',
                'latitude': -1.1112,
                'longitude': 36.6460,
            },
            {
                'name': 'Sotik Valley Plantation',
                'region': 'Sotik',
                'description': 'Sotik Valley\'s terraced hillsides produce teas of remarkable sweetness. The morning mists and afternoon sunshine create optimal conditions for developing the tea\'s natural sugars.',
                'elevation': '1,850m above sea level',
                'tasting_notes': 'Sweet and mellow with notes of caramel and toasted nuts',
                'brewing_tips': 'Best enjoyed without milk to appreciate the natural sweetness. Brew at 95°C.',
                'harvest_season': 'February-April, August-October',
                'latitude': -0.6833,
                'longitude': 35.1167,
            },
            {
                'name': 'Kisii Highlands Garden',
                'region': 'Kisii',
                'description': 'Small-holder farmers in Kisii produce some of Kenya\'s most aromatic teas. The unique combination of altitude, rainfall, and artisanal processing creates teas with distinctive personality.',
                'elevation': '1,700m above sea level',
                'tasting_notes': 'Aromatic with jasmine-like fragrances, smooth body',
                'brewing_tips': 'Lower temperature (85°C) for 2-3 minutes preserves the delicate aromas.',
                'harvest_season': 'March-May, September-November',
                'latitude': -0.6817,
                'longitude': 34.7658,
            },
            {
                'name': 'Nyambene Forest Reserve',
                'region': 'Meru',
                'description': 'Adjacent to the Nyambene Forest, this estate benefits from the biodiversity that surrounds it. Shade-grown teas develop slowly, concentrating flavors and creating exceptional depth.',
                'elevation': '1,950m above sea level',
                'tasting_notes': 'Complex with earthy undertones, notes of dark chocolate and dried fruit',
                'brewing_tips': 'A stronger brew (4-5 minutes) brings out the complexity. Excellent with milk.',
                'harvest_season': 'April-June',
                'latitude': 0.0833,
                'longitude': 37.8333,
            },
            {
                'name': 'Aberdare Mist Estate',
                'region': 'Nyeri',
                'description': 'High in the Aberdare Range, this estate produces teas shrouded in mountain mists. The slow growth at altitude creates leaves packed with flavor compounds.',
                'elevation': '2,300m above sea level',
                'tasting_notes': 'Silky texture with notes of apricot and fresh mountain herbs',
                'brewing_tips': 'Medium strength brewing at 90°C for 3 minutes. Beautiful standalone tea.',
                'harvest_season': 'March-May, September-October',
                'latitude': -0.4272,
                'longitude': 36.9519,
            },
            {
                'name': 'Cherangani Hills Estate',
                'region': 'Trans-Nzoia',
                'description': 'The remote Cherangani Hills produce wild-character teas with intense flavors. Minimal intervention farming lets the tea express the true terroir of this dramatic landscape.',
                'elevation': '2,500m above sea level',
                'tasting_notes': 'Bold and robust with smoky undertones, long finish',
                'brewing_tips': 'Strong brewing recommended. Perfect for chai with spices.',
                'harvest_season': 'April-June',
                'latitude': 1.0833,
                'longitude': 35.5000,
            },
            {
                'name': 'Bomet Golden Estate',
                'region': 'Bomet',
                'description': 'Known for producing golden-tipped teas, Bomet Golden Estate is famed for its premium Orthodox quality. Hand-picked leaves are processed with exceptional care.',
                'elevation': '2,000m above sea level',
                'tasting_notes': 'Honey-like sweetness with notes of biscuit and cream',
                'brewing_tips': 'For golden tips, use 80°C water and steep 2-3 minutes only.',
                'harvest_season': 'March-May (best for golden tips)',
                'latitude': -0.7833,
                'longitude': 35.3417,
            },
            {
                'name': 'Embu Sunrise Plantation',
                'region': 'Embu',
                'description': 'Catching the first rays of African sunrise, Embu plantations produce teas of remarkable brightness. The combination of volcanic soils and equatorial sunshine creates vibrant flavors.',
                'elevation': '1,800m above sea level',
                'tasting_notes': 'Bright and zesty with citrus notes and a clean, refreshing finish',
                'brewing_tips': 'Perfect for iced tea. Brew strong and pour over ice.',
                'harvest_season': 'Year-round',
                'latitude': -0.5389,
                'longitude': 37.4500,
            },
            {
                'name': 'Murang\'a Highland Gardens',
                'region': 'Murang\'a',
                'description': 'The green hills of Murang\'a have produced tea for generations. Family-owned plots combine traditional knowledge with pride in quality.',
                'elevation': '1,750m above sea level',
                'tasting_notes': 'Well-balanced with gentle astringency, notes of toast and stone fruit',
                'brewing_tips': 'Classic all-purpose brewing. 95°C for 3-4 minutes.',
                'harvest_season': 'February-April, August-October',
                'latitude': -0.7167,
                'longitude': 37.1500,
            },
        ]
        
        estates = []
        for data in estates_data:
            estate, created = TeaEstate.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            estates.append(estate)
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created: {estate.name}'))
            else:
                self.stdout.write(f'  Already exists: {estate.name}')
        
        # Create Collection
        self.stdout.write('\nCreating Collection...')
        
        collection, created = EstateCollection.objects.get_or_create(
            name='Golden Harvest Collection',
            defaults={
                'theme': 'Peak Season Yields',
                'description': 'Experience the finest teas from Kenya\'s premier growing regions. Collect all 12 Estate Cards from our inaugural Golden Harvest Collection and unlock exclusive rewards!',
                'start_date': timezone.now() - timedelta(days=1),
                'end_date': timezone.now() + timedelta(days=90),
                'is_active': True,
                'completion_reward_points': 1000,
                'completion_reward_description': 'Claim 1,000 bonus points plus a chance to win a tea tasting experience!',
                'total_cards': 12,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'  Created: {collection.name}'))
        else:
            self.stdout.write(f'  Already exists: {collection.name}')
        
        # Create Cards
        self.stdout.write('\nCreating Cards...')
        
        # Rarity distribution: 6 common, 4 uncommon, 2 rare
        rarity_assignments = [
            'common', 'common', 'common', 'common', 'common', 'common',
            'uncommon', 'uncommon', 'uncommon', 'uncommon',
            'rare', 'rare'
        ]
        
        frame_colors = {
            'common': '#E3DCD2',
            'uncommon': '#01453a',
            'rare': '#CC8B65'
        }
        
        for i, (estate, rarity) in enumerate(zip(estates[:12], rarity_assignments), 1):
            card, created = EstateCard.objects.get_or_create(
                collection=collection,
                card_number=i,
                defaults={
                    'estate': estate,
                    'rarity': rarity,
                    'title': f'{estate.name} - {rarity.title()} Edition',
                    'flavor_text': estate.description[:150] + '...',
                    'frame_color': frame_colors[rarity],
                    'drop_weight': 1.0 if rarity != 'rare' else 0.8,
                }
            )
            if created:
                symbol = '⭐' if rarity == 'rare' else ('💎' if rarity == 'uncommon' else '🍃')
                self.stdout.write(self.style.SUCCESS(f'  {symbol} Created Card #{i}: {card.title}'))
            else:
                self.stdout.write(f'  Already exists: Card #{i}')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Sample data creation complete!'))
        self.stdout.write(f'\n  📊 Summary:')
        self.stdout.write(f'     • {TeaEstate.objects.count()} Tea Estates')
        self.stdout.write(f'     • {EstateCollection.objects.count()} Collections')
        self.stdout.write(f'     • {EstateCard.objects.count()} Cards')
        self.stdout.write(f'\n  🎮 The Golden Harvest Collection is now active!')

