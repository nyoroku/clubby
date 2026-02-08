from django.core.management.base import BaseCommand
from club.models import EstateCollection, EstateCard
from django.utils import timezone

class Command(BaseCommand):
    help = 'Debug Estate Collection Data'

    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write(f"Current Time: {now}")
        
        collections = EstateCollection.objects.all()
        self.stdout.write(f"Total Collections: {collections.count()}")
        
        active = collections.filter(is_active=True, start_date__lte=now, end_date__gte=now)
        self.stdout.write(f"Active & Valid Collections: {active.count()}")
        
        for c in collections:
            self.stdout.write(f" - {c.name}: Active={c.is_active}, Start={c.start_date}, End={c.end_date}")
            
        cards = EstateCard.objects.all()
        self.stdout.write(f"Total Cards: {cards.count()}")
        
        active_cards = cards.filter(active=True)
        self.stdout.write(f"Active Cards: {active_cards.count()}")
