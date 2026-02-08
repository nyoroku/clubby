from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
import uuid
import random
import string

from django.contrib.auth import get_user_model

User = get_user_model()


def generate_pack_code():
    return uuid.uuid4().hex


def generate_token():
    """Generate a unique 32-character token for gifting"""
    return uuid.uuid4().hex


def generate_referral_code():
    """Generate a unique 6-character referral code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def generate_partnership_code():
    """Generate a unique 8-character partnership code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


class Partnership(models.Model):
    """Partnership/Affiliate accounts that earn from referred users' activities"""
    PARTNER_TYPE_CHOICES = [
        ('influencer', 'Influencer'),
        ('shop', 'Shop/Retailer'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True,
                                help_text="User account for partner login")
    phone = models.CharField(max_length=24, unique=True, help_text="Partner's phone number")

    # PIN Authentication
    pin = models.CharField(max_length=128, blank=True, help_text="Hashed PIN for authentication")

    # Basic Info
    name = models.CharField(max_length=100, help_text="Partnership/Business name")
    code = models.CharField(max_length=8, unique=True, blank=True, help_text="Unique partnership code")
    partner_type = models.CharField(max_length=20, choices=PARTNER_TYPE_CHOICES, default='influencer',
                                    help_text="Type of partner")
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)

    # Location (for shops)
    county = models.CharField(max_length=50, blank=True, help_text="County (for shops)")
    location_details = models.TextField(blank=True, help_text="Detailed location/address")

    # Points configuration
    points_per_scan = models.IntegerField(default=5, help_text="Points partner earns per scan by referred users")
    total_points_earned = models.IntegerField(default=0, help_text="Total points earned from referrals")

    # Status
    active = models.BooleanField(default=True)
    profile_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Optional payout tracking
    pending_payout = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                         help_text="Monetary value pending payout")
    total_payout = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                       help_text="Total paid out to partner")

    class Meta:
        verbose_name = "Partnership"
        verbose_name_plural = "Partnerships"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.code:
            max_attempts = 10
            for _ in range(max_attempts):
                code = generate_partnership_code()
                if not Partnership.objects.filter(code=code).exists():
                    self.code = code
                    break
        super().save(*args, **kwargs)

    def set_pin(self, raw_pin):
        """Hash and store PIN"""
        self.pin = make_password(raw_pin)
        self.save(update_fields=['pin'])

    def check_pin(self, raw_pin):
        """Verify PIN"""
        if not self.pin:
            return False
        return check_password(raw_pin, self.pin)

    def has_pin(self):
        """Check if PIN is set"""
        return bool(self.pin)

    def referred_users_count(self):
        """Count of users who signed up with this partnership code"""
        return self.referred_profiles.filter(profile_completed=True).count()

    def total_scans_by_referrals(self):
        """Total scans made by all referred users"""
        return Scan.objects.filter(profile__partnership=self).count()

    def is_shop(self):
        """Check if partner is a shop (can have redemptions)"""
        return self.partner_type == 'shop'

    def is_influencer(self):
        """Check if partner is an influencer"""
        return self.partner_type == 'influencer'

    def __str__(self):
        return f"{self.name} ({self.code}) - {self.get_partner_type_display()}"


class Profile(models.Model):
    BUYER_TYPE_CHOICES = [
        ('home', 'Home Use'),
        ('business', 'Business Use'),
    ]

    COUNTY_CHOICES = [
        ('mombasa', 'Mombasa'),
        ('kwale', 'Kwale'),
        ('kilifi', 'Kilifi'),
        ('tana_river', 'Tana River'),
        ('lamu', 'Lamu'),
        ('taita_taveta', 'Taita Taveta'),
        ('garissa', 'Garissa'),
        ('wajir', 'Wajir'),
        ('mandera', 'Mandera'),
        ('marsabit', 'Marsabit'),
        ('isiolo', 'Isiolo'),
        ('meru', 'Meru'),
        ('tharaka_nithi', 'Tharaka Nithi'),
        ('embu', 'Embu'),
        ('kitui', 'Kitui'),
        ('machakos', 'Machakos'),
        ('makueni', 'Makueni'),
        ('nyandarua', 'Nyandarua'),
        ('nyeri', 'Nyeri'),
        ('kirinyaga', 'Kirinyaga'),
        ('muranga', "Murang'a"),
        ('kiambu', 'Kiambu'),
        ('turkana', 'Turkana'),
        ('west_pokot', 'West Pokot'),
        ('samburu', 'Samburu'),
        ('trans_nzoia', 'Trans Nzoia'),
        ('uasin_gishu', 'Uasin Gishu'),
        ('elgeyo_marakwet', 'Elgeyo Marakwet'),
        ('nandi', 'Nandi'),
        ('baringo', 'Baringo'),
        ('laikipia', 'Laikipia'),
        ('nakuru', 'Nakuru'),
        ('narok', 'Narok'),
        ('kajiado', 'Kajiado'),
        ('kericho', 'Kericho'),
        ('bomet', 'Bomet'),
        ('kakamega', 'Kakamega'),
        ('vihiga', 'Vihiga'),
        ('bungoma', 'Bungoma'),
        ('busia', 'Busia'),
        ('siaya', 'Siaya'),
        ('kisumu', 'Kisumu'),
        ('homa_bay', 'Homa Bay'),
        ('migori', 'Migori'),
        ('kisii', 'Kisii'),
        ('nyamira', 'Nyamira'),
        ('nairobi', 'Nairobi'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=24, unique=True)

    # PIN Authentication
    pin = models.CharField(max_length=128, blank=True, help_text="Hashed PIN for authentication")

    first_name = models.CharField(max_length=50, blank=True)
    second_name = models.CharField(max_length=50, blank=True)
    county = models.CharField(max_length=50, choices=COUNTY_CHOICES, blank=True)
    buyer_type = models.CharField(max_length=10, choices=BUYER_TYPE_CHOICES, blank=True)
    points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    profile_completed = models.BooleanField(default=False)

    # Referral fields (user-to-user)
    referral_code = models.CharField(max_length=6, unique=True, blank=True, null=True)
    referred_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals')
    referral_points_earned = models.IntegerField(default=0)

    # Partnership/Affiliate field
    partnership = models.ForeignKey(Partnership, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='referred_profiles',
                                    help_text="Partnership that referred this user")

    def save(self, *args, **kwargs):
        # Generate unique referral code if not exists
        if not self.referral_code:
            max_attempts = 10
            for _ in range(max_attempts):
                code = generate_referral_code()
                if not Profile.objects.filter(referral_code=code).exists():
                    self.referral_code = code
                    break
        super().save(*args, **kwargs)

    def set_pin(self, raw_pin):
        """Hash and store PIN"""
        self.pin = make_password(raw_pin)
        self.save(update_fields=['pin'])

    def check_pin(self, raw_pin):
        """Verify PIN"""
        if not self.pin:
            return False
        return check_password(raw_pin, self.pin)

    def has_pin(self):
        """Check if PIN is set"""
        return bool(self.pin)

    def successful_referrals_count(self):
        """Count of successfully referred users (completed profiles)"""
        return self.referrals.filter(profile_completed=True).count()

    def can_refer_more(self):
        """Check if user can still refer more friends"""
        settings = ReferralSettings.get_settings()
        if settings.max_referrals_per_user is None:
            return True
        return self.successful_referrals_count() < settings.max_referrals_per_user

    def __str__(self):
        name = f"{self.first_name} {self.second_name}".strip() or self.phone
        return f"{name} — {self.points} pts"


class ListingPartner(models.Model):
    """
    Vendors/Brands who list products for redemption with Melvins points
    Different from Partnership (referral partners)
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True,
                                help_text="User account for listing partner login")
    phone = models.CharField(max_length=24, unique=True, help_text="Listing partner's phone number")

    # PIN Authentication
    pin = models.CharField(max_length=128, blank=True, help_text="Hashed PIN for authentication")

    # Company Info
    company_name = models.CharField(max_length=200, help_text="Company/Brand name")
    code = models.CharField(max_length=8, unique=True, blank=True, help_text="Unique listing partner code")
    contact_person = models.CharField(max_length=100)
    email = models.EmailField()

    # Business Details
    business_registration = models.CharField(max_length=100, blank=True, help_text="Business registration number")
    tax_pin = models.CharField(max_length=50, blank=True, help_text="KRA PIN")

    # Bank Details for Payments
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    bank_account_name = models.CharField(max_length=200, blank=True)
    mpesa_number = models.CharField(max_length=24, blank=True, help_text="M-Pesa paybill/till number")

    # Commission Settings
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00,
                                          help_text="Melvins's commission % on redemptions")

    # Financial Tracking
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00,
                                        help_text="Total revenue from redemptions")
    Melvins_commission_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0.00,
                                                   help_text="Total commission earned by Melvins")
    partner_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00,
                                           help_text="Net earnings for partner (after commission)")
    pending_payout = models.DecimalField(max_digits=12, decimal_places=2, default=0.00,
                                         help_text="Amount pending payout to partner")
    total_paid_out = models.DecimalField(max_digits=12, decimal_places=2, default=0.00,
                                         help_text="Total amount paid to partner")

    # Status
    active = models.BooleanField(default=True)
    approved = models.BooleanField(default=False, help_text="Approved by Melvins admin")
    profile_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Listing Partner"
        verbose_name_plural = "Listing Partners"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.code:
            max_attempts = 10
            for _ in range(max_attempts):
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                if not ListingPartner.objects.filter(code=code).exists():
                    self.code = code
                    break
        super().save(*args, **kwargs)

    def set_pin(self, raw_pin):
        """Hash and store PIN"""
        self.pin = make_password(raw_pin)
        self.save(update_fields=['pin'])

    def check_pin(self, raw_pin):
        """Verify PIN"""
        if not self.pin:
            return False
        return check_password(raw_pin, self.pin)

    def has_pin(self):
        """Check if PIN is set"""
        return bool(self.pin)

    def total_products(self):
        """Count of active products"""
        return self.products.filter(active=True).count()

    def total_redemptions(self):
        """Total redemptions of this partner's products"""
        return ProductRedemption.objects.filter(product__listing_partner=self).count()

    def __str__(self):
        return f"{self.company_name} ({self.code})"


# Keep the rest of the models as they were (no changes needed)

class ReferralSettings(models.Model):
    """Singleton model for referral system settings"""
    points_for_referrer = models.IntegerField(default=50, help_text="Points awarded to referrer when friend joins")
    points_for_referee = models.IntegerField(default=20, help_text="Points awarded to new user who was referred")
    max_referrals_per_user = models.IntegerField(null=True, blank=True,
                                                 help_text="Maximum referrals per user (null = unlimited)")
    referral_enabled = models.BooleanField(default=True, help_text="Enable/disable referral system")

    class Meta:
        verbose_name = "Referral Settings"
        verbose_name_plural = "Referral Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Referral Settings"


class Referral(models.Model):
    """Track individual referral events"""
    referrer = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='referral_events')
    referred = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='referral_event')
    points_awarded_to_referrer = models.IntegerField()
    points_awarded_to_referred = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.referrer.phone} referred {self.referred.phone}"


class PartnershipEarning(models.Model):
    """Track points earned by partnerships from referred users' scans"""
    partnership = models.ForeignKey(Partnership, on_delete=models.CASCADE, related_name='earnings')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, help_text="User who made the scan")
    scan = models.ForeignKey('Scan', on_delete=models.CASCADE, help_text="The scan that generated earnings")
    points_earned = models.IntegerField(help_text="Points earned by partner from this scan")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Partnership Earning"
        verbose_name_plural = "Partnership Earnings"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.partnership.name} earned {self.points_earned} pts from {self.profile.phone}'s scan"


class OTP(models.Model):
    """Keep for future SMS integration"""
    phone = models.CharField(max_length=24)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)
    is_partner = models.BooleanField(default=False, help_text="OTP for partner registration")

    def is_valid(self):
        return not self.used and (timezone.now() - self.created_at).total_seconds() < 300


class PackCode(models.Model):
    code = models.CharField(
        max_length=128,
        unique=True,
        blank=True,  # Allow blank so custom codes can be set in management command
        help_text="Unique pack code"
    )
    sku = models.CharField(max_length=64, default="Melvins")
    points = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)
    used_by = models.ForeignKey('Profile', null=True, blank=True, on_delete=models.SET_NULL)
    used_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Only generate code if not provided (for backward compatibility)
        if not self.code:
            self.code = generate_pack_code()
        super().save(*args, **kwargs)

    def mark_used(self, profile):
        self.used = True
        self.used_by = profile
        self.used_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.sku} - {self.code[:8]}{' (used)' if self.used else ''}"

    class Meta:
        verbose_name = "Pack Code"
        verbose_name_plural = "Pack Codes"
        ordering = ['-created_at']


class Scan(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    pack = models.ForeignKey(PackCode, on_delete=models.CASCADE)
    points_awarded = models.IntegerField()
    scanned_at = models.DateTimeField(auto_now_add=True)
    partnership_points_awarded = models.BooleanField(default=False)

    def award_partnership_points(self):
        """Award points to the partnership that referred this user"""
        if self.partnership_points_awarded:
            return

        if not self.profile.partnership:
            return

        if not self.profile.partnership.active:
            return

        partnership = self.profile.partnership
        points = partnership.points_per_scan

        PartnershipEarning.objects.create(
            partnership=partnership,
            profile=self.profile,
            scan=self,
            points_earned=points
        )

        partnership.total_points_earned += points
        partnership.save(update_fields=['total_points_earned'])

        self.partnership_points_awarded = True
        self.save(update_fields=['partnership_points_awarded'])


class Reward(models.Model):
    name = models.CharField(max_length=100)
    cost_points = models.IntegerField()
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    available_at_shops = models.BooleanField(default=False,
                                             help_text="Can be redeemed at partner shops")
    partner_shops = models.ManyToManyField(Partnership, blank=True,
                                           limit_choices_to={'partner_type': 'shop'},
                                           related_name='available_rewards',
                                           help_text="Shops where this reward can be redeemed")

    def __str__(self):
        return f"{self.name} ({self.cost_points} pts)"


class Redemption(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved by Shop'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
    ]

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE)
    redeemed_at_shop = models.ForeignKey(Partnership, null=True, blank=True,
                                         on_delete=models.SET_NULL,
                                         limit_choices_to={'partner_type': 'shop'},
                                         help_text="Shop where reward was redeemed")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    fulfilled = models.BooleanField(default=False)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    redemption_code = models.CharField(max_length=8, unique=True, blank=True,
                                       help_text="Code for shop to verify redemption")
    metadata = models.JSONField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.redemption_code:
            self.redemption_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.profile.phone} - {self.reward.name} ({self.status})"


class PointTransferSettings(models.Model):
    """Singleton model for point transfer system settings"""
    transfer_enabled = models.BooleanField(default=True, help_text="Enable/disable point transfers")
    min_transfer_amount = models.IntegerField(default=10, help_text="Minimum points that can be transferred")
    max_transfer_amount = models.IntegerField(default=500, help_text="Maximum points per transfer")
    daily_transfer_limit = models.IntegerField(default=1000, help_text="Maximum points user can transfer per day")
    transfer_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00,
                                                  help_text="Fee percentage (0-100). E.g., 5.00 = 5%")

    class Meta:
        verbose_name = "Point Transfer Settings"
        verbose_name_plural = "Point Transfer Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Point Transfer Settings"


class PointTransfer(models.Model):
    """Track point transfers between users"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='points_sent')
    recipient = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='points_received')
    amount = models.IntegerField(help_text="Points transferred")
    fee = models.IntegerField(default=0, help_text="Transfer fee deducted")
    net_amount = models.IntegerField(help_text="Amount received by recipient")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    message = models.CharField(max_length=200, blank=True, help_text="Optional message to recipient")
    created_at = models.DateTimeField(auto_now_add=True)
    was_invite = models.BooleanField(default=False, help_text="Transfer was to invite unregistered user")
    invite_phone = models.CharField(max_length=24, blank=True, help_text="Phone of invited user")
    invite_accepted = models.BooleanField(default=False, help_text="Invited user registered")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Point Transfer"
        verbose_name_plural = "Point Transfers"

    def __str__(self):
        return f"{self.sender.phone} → {self.recipient.phone if self.recipient else self.invite_phone}: {self.amount} pts"


class PendingInvite(models.Model):
    """Track invites to unregistered users"""
    inviter = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='sent_invites')
    phone = models.CharField(max_length=24, help_text="Phone number of person being invited")
    points_promised = models.IntegerField(help_text="Points to transfer when they register")
    message = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['inviter', 'phone']

    def __str__(self):
        return f"{self.inviter.phone} invites {self.phone} ({self.points_promised} pts)"


class ProductListing(models.Model):
    """Products listed by listing partners for redemption with Melvins points"""
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ]

    listing_partner = models.ForeignKey(ListingPartner, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=100, blank=True, help_text="e.g., Electronics, Fashion, Food")
    image = models.ImageField(upload_to='product_listings/', blank=True, null=True)
    partner_price = models.DecimalField(max_digits=10, decimal_places=2,
                                        help_text="Price partner wants to receive (KES)")
    Melvins_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       help_text="Final price set by Melvins (KES)")
    points_required = models.IntegerField(null=True, blank=True,
                                          help_text="Points needed to redeem (set by Melvins)")
    point_value = models.DecimalField(max_digits=5, decimal_places=2, default=1.00,
                                      help_text="Value of 1 point in KES (e.g., 1 point = 1 KES)")
    stock_quantity = models.IntegerField(default=0, help_text="Available stock")
    redemption_limit = models.IntegerField(null=True, blank=True,
                                           help_text="Max redemptions per user (null = unlimited)")
    available_at_shops = models.ManyToManyField(Partnership, blank=True,
                                                limit_choices_to={'partner_type': 'shop'},
                                                related_name='available_products',
                                                help_text="Shops where product can be redeemed")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, help_text="Reason for rejection")
    active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False, help_text="Featured product")
    total_redemptions = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='approved_products')

    class Meta:
        verbose_name = "Product Listing"
        verbose_name_plural = "Product Listings"
        ordering = ['-created_at']

    def is_in_stock(self):
        return self.stock_quantity > 0

    def can_redeem(self, profile):
        if not self.active or self.status != 'approved':
            return False, "Product not available"

        if not self.is_in_stock():
            return False, "Out of stock"

        if profile.points < self.points_required:
            return False, f"Insufficient points. Need {self.points_required - profile.points} more"

        if self.redemption_limit:
            user_redemptions = ProductRedemption.objects.filter(
                product=self,
                profile=profile,
                status__in=['pending', 'approved', 'fulfilled']
            ).count()

            if user_redemptions >= self.redemption_limit:
                return False, f"Redemption limit reached ({self.redemption_limit})"

        return True, "Can redeem"

    def calculate_earnings(self):
        if not self.Melvins_price:
            return None

        commission = self.Melvins_price * (self.listing_partner.commission_rate / 100)
        partner_earning = self.Melvins_price - commission

        return {
            'total': self.Melvins_price,
            'Melvins_commission': commission,
            'partner_earning': partner_earning
        }

    def __str__(self):
        return f"{self.name} - {self.points_required} pts ({self.get_status_display()})"


class ProductRedemption(models.Model):
    """Track redemptions of product listings"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
    ]

    product = models.ForeignKey(ProductListing, on_delete=models.CASCADE, related_name='redemptions')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='product_redemptions')
    redeemed_at_shop = models.ForeignKey(Partnership, null=True, blank=True,
                                         on_delete=models.SET_NULL,
                                         limit_choices_to={'partner_type': 'shop'})
    points_deducted = models.IntegerField(help_text="Points deducted from user")
    amount_charged = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount in KES")
    Melvins_commission = models.DecimalField(max_digits=10, decimal_places=2,
                                            help_text="Commission earned by Melvins")
    partner_earning = models.DecimalField(max_digits=10, decimal_places=2,
                                          help_text="Amount earned by listing partner")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    redemption_code = models.CharField(max_length=8, unique=True, blank=True,
                                       help_text="Code for verification")
    created_at = models.DateTimeField(auto_now_add=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    paid_to_partner = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Product Redemption"
        verbose_name_plural = "Product Redemptions"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.redemption_code:
            while True:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                if not ProductRedemption.objects.filter(redemption_code=code).exists():
                    self.redemption_code = code
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.profile.phone} - {self.product.name} ({self.get_status_display()})"


class PartnerPayout(models.Model):
    """Track payouts to listing partners"""
    PAYMENT_METHOD_CHOICES = [
        ('bank', 'Bank Transfer'),
        ('mpesa', 'M-Pesa'),
        ('cheque', 'Cheque'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    listing_partner = models.ForeignKey(ListingPartner, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='processed_payouts')

    class Meta:
        verbose_name = "Partner Payout"
        verbose_name_plural = "Partner Payouts"
        ordering = ['-created_at']

    def __str__(self):
        return f"Payout to {self.listing_partner.company_name} - KES {self.amount} ({self.get_status_display()})"


class Challenge(models.Model):
    """Competitions/Challenges for users to win rewards"""
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('one_time', 'One-Time Event'),
    ]

    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('winners_selected', 'Winners Selected'),
    ]

    title = models.CharField(max_length=200, help_text="Challenge title")
    description = models.TextField(help_text="Challenge description")
    image = models.ImageField(upload_to='challenges/', blank=True, null=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    start_date = models.DateTimeField(help_text="When challenge starts")
    end_date = models.DateTimeField(help_text="When challenge ends")
    number_of_winners = models.IntegerField(default=1, help_text="How many winners to select")
    reward_type = models.CharField(max_length=50, choices=[
        ('points', 'Points'),
        ('cash', 'Cash Prize'),
        ('product', 'Product'),
        ('voucher', 'Voucher'),
        ('custom', 'Custom Reward'),
    ], default='points')
    reward_value = models.CharField(max_length=200, help_text="e.g., '1000 points' or 'KES 5,000' or 'iPhone 15'")
    reward_description = models.TextField(blank=True, help_text="Additional reward details")
    points_weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.0,
                                        help_text="Weight multiplier for points")
    referrals_weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.0,
                                           help_text="Weight multiplier for referrals")
    min_points_required = models.IntegerField(default=0, help_text="Minimum points to participate")
    min_scans_required = models.IntegerField(default=0, help_text="Minimum scans to participate")
    counties_eligible = models.CharField(max_length=500, blank=True,
                                         help_text="Comma-separated counties (leave blank for all)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False, help_text="Show on homepage")
    total_entries = models.IntegerField(default=0, help_text="Total eligible participants")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    winners_selected_at = models.DateTimeField(null=True, blank=True)
    is_public_results = models.BooleanField(default=False,
                                            help_text="If True, anyone can see results")
    live_draw_scheduled = models.DateTimeField(null=True, blank=True,
                                               help_text="When the live draw will happen")
    draw_in_progress = models.BooleanField(default=False, help_text="Set to True when live draw is happening")
    draw_completed_at = models.DateTimeField(null=True, blank=True, help_text="When the live draw was completed")
    live_draw_url = models.CharField(max_length=500, blank=True, help_text="YouTube/Facebook Live URL")

    class Meta:
        verbose_name = "Challenge"
        verbose_name_plural = "Challenges"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.title} ({self.get_frequency_display()}) - {self.get_status_display()}"

    def can_view_winners(self, user):
        if self.status != 'winners_selected':
            return False
        if self.is_public_results:
            return True
        if user.is_authenticated:
            return ChallengeEntry.objects.filter(challenge=self, profile=user.profile).exists()
        return False

    def is_active(self):
        now = timezone.now()
        return self.status == 'active' and self.start_date <= now <= self.end_date

    def get_eligible_profiles(self):
        profiles = Profile.objects.filter(profile_completed=True)
        if self.min_points_required > 0:
            profiles = profiles.filter(points__gte=self.min_points_required)
        if self.min_scans_required > 0:
            from django.db.models import Count
            profiles = profiles.annotate(scan_count=Count('scan')).filter(scan_count__gte=self.min_scans_required)
        if self.counties_eligible:
            counties_list = [c.strip() for c in self.counties_eligible.split(',')]
            profiles = profiles.filter(county__in=counties_list)
        return profiles

    def calculate_entry_weight(self, profile):
        weight = 1.0
        if profile.points > 0:
            points_contribution = float(profile.points) * float(self.points_weight)
            weight += points_contribution / 1000.0
        referral_count = profile.successful_referrals_count()
        if referral_count > 0:
            referral_contribution = referral_count * float(self.referrals_weight)
            weight += referral_contribution
        return max(weight, 1.0)

    def select_winners(self):
        eligible_profiles = self.get_eligible_profiles()
        if eligible_profiles.count() < self.number_of_winners:
            raise ValueError(
                f"Not enough eligible participants. Need {self.number_of_winners}, have {eligible_profiles.count()}")
        weighted_profiles = []
        for profile in eligible_profiles:
            weight = self.calculate_entry_weight(profile)
            weighted_profiles.append((profile, weight))
        weighted_profiles.sort(key=lambda x: x[1], reverse=True)
        profiles = [p[0] for p in weighted_profiles]
        weights = [p[1] for p in weighted_profiles]
        winners = random.choices(profiles, weights=weights, k=self.number_of_winners)
        winner_records = []
        for position, winner_profile in enumerate(winners, 1):
            winner_record = ChallengeWinner.objects.create(
                challenge=self,
                profile=winner_profile,
                position=position,
                entry_weight=self.calculate_entry_weight(winner_profile),
                total_entries=len(profiles)
            )
            winner_records.append(winner_record)
        self.status = 'winners_selected'
        self.winners_selected_at = timezone.now()
        self.total_entries = len(profiles)
        self.save()
        return winner_records


class ChallengeWinner(models.Model):
    """Record of challenge winners"""
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='winners')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='challenge_wins')
    position = models.IntegerField(help_text="Winner position (1st, 2nd, 3rd, etc.)")
    entry_weight = models.DecimalField(max_digits=10, decimal_places=2, help_text="Weight used for selection")
    total_entries = models.IntegerField(help_text="Total participants in challenge")
    prize_claimed = models.BooleanField(default=False)
    prize_claimed_at = models.DateTimeField(null=True, blank=True)
    prize_delivery_notes = models.TextField(blank=True)
    selected_at = models.DateTimeField(auto_now_add=True)
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Challenge Winner"
        verbose_name_plural = "Challenge Winners"
        ordering = ['challenge', 'position']
        unique_together = ['challenge', 'profile']

    def __str__(self):
        return f"{self.challenge.title} - Position {self.position}: {self.profile.phone}"

    def get_masked_phone(self):
        phone = self.profile.phone
        if len(phone) > 6:
            return phone[:7] + 'XXX' + phone[-3:]
        return phone[:3] + 'XXX'

    def get_display_name(self):
        first = self.profile.first_name
        second = self.profile.second_name
        if first and second:
            return f"{first} {second[0]}."
        elif first:
            if len(first) > 3:
                return f"{first[:3]}***"
            return f"{first}***"
        else:
            return "Winner"

    def to_dict(self):
        return {
            'position': self.position,
            'masked_phone': self.get_masked_phone(),
            'display_name': self.get_display_name(),
            'county': self.profile.get_county_display() if self.profile.county else 'Not specified',
            'entry_weight': float(self.entry_weight),
            'prize': self.challenge.reward_value,
            'selected_at': self.selected_at.isoformat()
        }


class ChallengeEntry(models.Model):
    """Track who entered each challenge"""
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='entries')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='challenge_entries')
    entry_weight = models.DecimalField(max_digits=10, decimal_places=2)
    points_at_entry = models.IntegerField(help_text="User's points when entered")
    referrals_at_entry = models.IntegerField(help_text="User's referrals when entered")
    entered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Challenge Entry"
        verbose_name_plural = "Challenge Entries"
        unique_together = ['challenge', 'profile']
        ordering = ['-entered_at']

    def __str__(self):
        return f"{self.profile.phone} entered {self.challenge.title}"


# ========================================
# TEA ESTATES COLLECTION GAME MODELS
# ========================================

class TeaEstate(models.Model):
    """Real Kenyan tea-growing regions for the collection game"""
    name = models.CharField(max_length=100, help_text="e.g., 'Kericho Valley Estate'")
    region = models.CharField(max_length=50, help_text="e.g., 'Kericho'")
    description = models.TextField(help_text="Story of this estate")
    elevation = models.CharField(max_length=50, blank=True, help_text="e.g., '2,000m above sea level'")
    tasting_notes = models.TextField(blank=True, help_text="Flavor profile of tea from this region")
    brewing_tips = models.TextField(blank=True, help_text="Recommended brewing method")
    harvest_season = models.CharField(max_length=100, blank=True, help_text="e.g., 'March - May'")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    image = models.ImageField(upload_to='estates/', blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tea Estate"
        verbose_name_plural = "Tea Estates"
        ordering = ['region', 'name']

    def __str__(self):
        return f"{self.name} ({self.region})"


class EstateCollection(models.Model):
    """Themed collections like 'Golden Harvest', 'Pick Your Brew', etc."""
    name = models.CharField(max_length=100, help_text="e.g., 'Golden Harvest Collection'")
    theme = models.CharField(max_length=100, help_text="e.g., 'Peak Season Yields'")
    description = models.TextField()
    start_date = models.DateTimeField(help_text="When collection becomes available")
    end_date = models.DateTimeField(help_text="Collection deadline")
    is_active = models.BooleanField(default=False)
    featured_image = models.ImageField(upload_to='collections/', blank=True, null=True)
    
    # Rewards for completing the collection
    completion_reward_points = models.IntegerField(default=500, help_text="Points awarded for completing set")
    completion_reward_description = models.TextField(blank=True, help_text="Additional reward details")
    
    # Stats
    total_cards = models.IntegerField(default=12, help_text="Total cards in this collection")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Estate Collection"
        verbose_name_plural = "Estate Collections"
        ordering = ['-start_date']

    def is_currently_active(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

    def save(self, *args, **kwargs):
        """Ensure only one campaign is active at a time"""
        if self.is_active:
            # Deactivate all other campaigns when this one becomes active
            EstateCollection.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active_campaign(cls):
        """Get the single active campaign, or None if no campaign is active"""
        return cls.objects.filter(is_active=True).first()

    def __str__(self):
        return f"{self.name} - {self.theme}"


class EstateCard(models.Model):
    """Individual collectible cards with rarity tiers"""
    RARITY_CHOICES = [
        ('common', 'Estate Pick (Common)'),
        ('uncommon', 'Estate Reserve (Uncommon)'),
        ('rare', 'Grand Reserve (Rare)'),
    ]
    
    # Base weights for card drops (common > uncommon > rare)
    RARITY_WEIGHTS = {
        'common': 60.0,    # 60% chance
        'uncommon': 30.0,  # 30% chance
        'rare': 10.0,      # 10% chance
    }

    estate = models.ForeignKey(TeaEstate, on_delete=models.CASCADE, related_name='cards')
    collection = models.ForeignKey(EstateCollection, on_delete=models.CASCADE, related_name='cards')
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default='common')
    card_number = models.IntegerField(help_text="Card # in collection (e.g., 1 of 12)")
    title = models.CharField(max_length=100, blank=True, help_text="Card title, defaults to estate name")
    flavor_text = models.TextField(blank=True, help_text="Special text for this card")
    
    # Drop configuration
    drop_weight = models.FloatField(default=1.0, help_text="Multiplier for drop probability")
    
    # Visuals
    card_image = models.ImageField(upload_to='cards/', blank=True, null=True)
    frame_color = models.CharField(max_length=7, default='#013328', help_text="Hex color for card frame")
    
    # Rewards
    reward_points = models.IntegerField(default=10, help_text="Points awarded when user obtains this card")
    
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Estate Card"
        verbose_name_plural = "Estate Cards"
        ordering = ['collection', 'card_number']
        unique_together = ['collection', 'card_number']

    def get_effective_weight(self):
        """Calculate actual drop weight based on rarity and custom weight"""
        base_weight = self.RARITY_WEIGHTS.get(self.rarity, 50.0)
        return base_weight * self.drop_weight

    def get_display_title(self):
        return self.title or self.estate.name

    def __str__(self):
        return f"#{self.card_number} {self.get_display_title()} ({self.get_rarity_display()}) - {self.collection.name}"


class UserCardCollection(models.Model):
    """Track which cards each user has collected"""
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='card_collection')
    card = models.ForeignKey(EstateCard, on_delete=models.CASCADE, related_name='collectors')
    obtained_at = models.DateTimeField(auto_now_add=True)
    from_pack = models.ForeignKey(PackCode, null=True, blank=True, on_delete=models.SET_NULL,
                                  help_text="The pack code that revealed this card")
    from_scan = models.ForeignKey('Scan', null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='revealed_cards')
    is_duplicate = models.BooleanField(default=False, help_text="User already had this card")
    is_new = models.BooleanField(default=True, help_text="Card hasn't been viewed yet")

    class Meta:
        verbose_name = "User Card Collection"
        verbose_name_plural = "User Card Collections"
        ordering = ['-obtained_at']

    def __str__(self):
        dup = " (duplicate)" if self.is_duplicate else ""
        return f"{self.profile.phone} - {self.card.get_display_title()}{dup}"


class CollectionCompletion(models.Model):
    """Track when users complete full collections and claim rewards"""
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='completed_collections')
    collection = models.ForeignKey(EstateCollection, on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateTimeField(auto_now_add=True)
    reward_claimed = models.BooleanField(default=False)
    reward_claimed_at = models.DateTimeField(null=True, blank=True)
    points_awarded = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Collection Completion"
        verbose_name_plural = "Collection Completions"
        unique_together = ['profile', 'collection']
        ordering = ['-completed_at']

    def claim_reward(self):
        """Award points for completing collection"""
        if self.reward_claimed:
            return False, "Reward already claimed"
        
        points = self.collection.completion_reward_points
        self.profile.points += points
        self.profile.save(update_fields=['points'])
        
        self.points_awarded = points
        self.reward_claimed = True
        self.reward_claimed_at = timezone.now()
        self.save()
        
        return True, f"Claimed {points} points!"

    def __str__(self):
        claimed = " (claimed)" if self.reward_claimed else " (unclaimed)"
        return f"{self.profile.phone} completed {self.collection.name}{claimed}"


class CardGift(models.Model):
    """Support sharing specific cards with friends via unique tokens"""
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='sent_gifts')
    receiver = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True, blank=True, related_name='received_gifts')
    card = models.ForeignKey(EstateCard, on_delete=models.CASCADE)
    token = models.CharField(max_length=40, unique=True, default=generate_token)
    created_at = models.DateTimeField(auto_now_add=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    is_claimed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Card Gift"
        verbose_name_plural = "Card Gifts"

    def __str__(self):
        return f"Gift from {self.sender.phone}: {self.card.get_display_title()}"

    def claim(self, profile):
        if self.is_claimed:
            return False, "Already claimed"
        
        # Add to user's collection
        ucc, created = UserCardCollection.objects.get_or_create(
            profile=profile,
            card=self.card,
            defaults={'is_duplicate': False, 'is_new': True}
        )
        if not created:
            # User already has it, mark as duplicate ucc entry
            ucc = UserCardCollection.objects.create(
                profile=profile,
                card=self.card,
                is_duplicate=True,
                is_new=True
            )

        self.receiver = profile
        self.is_claimed = True
        self.claimed_at = timezone.now()
        self.save()
        return True, "Card claimed successfully!"


# Helper function for card reveal
def reveal_card_for_scan(scan, profile):
    """
    Reveal a random card when a user scans a pack code.
    Returns the UserCardCollection instance created.
    """
    from django.db.models import Sum
    
    # Get active collection
    active_collections = EstateCollection.objects.filter(
        is_active=True,
        start_date__lte=timezone.now(),
        end_date__gte=timezone.now()
    )
    
    print(f"DEBUG REVEAL: Found {active_collections.count()} active collections")
    
    if not active_collections.exists():
        print("DEBUG REVEAL: No active collections found.")
        return None
    
    collection = active_collections.first()
    print(f"DEBUG REVEAL: Using collection '{collection.name}'")
    
    # Get all active cards from this collection
    cards = EstateCard.objects.filter(
        collection=collection,
        active=True
    )
    
    print(f"DEBUG REVEAL: Found {cards.count()} active cards in collection")
    
    if not cards.exists():
        print("DEBUG REVEAL: No cards in collection.")
        return None
    
    # Weighted random selection
    total_weight = sum(card.get_effective_weight() for card in cards)
    print(f"DEBUG REVEAL: Total weight: {total_weight}")
    
    random_point = random.uniform(0, total_weight)
    
    cumulative = 0
    selected_card = None
    for card in cards:
        cumulative += card.get_effective_weight()
        if random_point <= cumulative:
            selected_card = card
            break
    
    if not selected_card:
        selected_card = random.choice(list(cards))
        print("DEBUG REVEAL: Fallback random selection used")
        
    print(f"DEBUG REVEAL: Selected card: {selected_card} (ID: {selected_card.id})")
    
    # Check if user already has this card
    is_duplicate = UserCardCollection.objects.filter(
        profile=profile,
        card=selected_card,
        is_duplicate=False
    ).exists()
    
    # Create the collection entry
    user_card = UserCardCollection.objects.create(
        profile=profile,
        card=selected_card,
        from_pack=scan.pack,
        from_scan=scan,
        is_duplicate=is_duplicate,
        is_new=True
    )

    # Point tally to update at the end
    points_to_add = 0
    
    # Award card points (only for new cards, not duplicates)
    if not is_duplicate:
        points_to_add += selected_card.reward_points
    
    # Award bonus for duplicate
    if is_duplicate:
        points_to_add += 5
    
    # Check for milestones
    # Optimized unique card count query
    total_unique = UserCardCollection.objects.filter(
        profile=profile,
        card__collection=collection,
        is_duplicate=False
    ).values('card_id').distinct().count()
    
    # Milestone 1: 3 unique cards
    if total_unique == 3 and not is_duplicate:
        points_to_add += 100
    
    # Check if user has completed the collection (Milestone 2: 12 cards)
    if total_unique >= collection.total_cards and not is_duplicate:
        # User completed the collection!
        comp, created = CollectionCompletion.objects.get_or_create(
            profile=profile,
            collection=collection,
            defaults={'points_awarded': 0}
        )
        if created:
            # Award completion bonus (Gold Milestone)
            points_to_add += collection.completion_reward_points
            comp.reward_claimed = True
            comp.points_awarded = collection.completion_reward_points
            comp.reward_claimed_at = timezone.now()
            comp.save()
            
    if points_to_add > 0:
        profile.points += points_to_add
        profile.save(update_fields=['points'])
    
    return user_card


# ========================================
# TEAM COLLECTION MODELS (Group Mode)
# ========================================

def generate_team_invite_code():
    """Generate a unique 6-character team invite code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


class CollectionTeam(models.Model):
    """Team formed to collect cards together in Group mode"""
    name = models.CharField(max_length=100, help_text="Team name chosen by captain")
    collection = models.ForeignKey(EstateCollection, on_delete=models.CASCADE, related_name='teams')
    captain = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='led_teams')
    invite_code = models.CharField(max_length=6, unique=True, blank=True, help_text="Code for friends to join")
    max_members = models.IntegerField(default=5, help_text="Maximum team size")
    
    # Status
    is_active = models.BooleanField(default=True)
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When team completed collection")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Collection Team"
        verbose_name_plural = "Collection Teams"
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.invite_code:
            max_attempts = 10
            for _ in range(max_attempts):
                code = generate_team_invite_code()
                if not CollectionTeam.objects.filter(invite_code=code).exists():
                    self.invite_code = code
                    break
        super().save(*args, **kwargs)
    
    def member_count(self):
        return self.members.count()
    
    def can_join(self):
        """Check if team has room for more members"""
        return self.is_active and self.member_count() < self.max_members
    
    def cards_collected_count(self):
        """Count of unique cards collected by team"""
        return self.team_cards.count()
    
    def progress_percentage(self):
        """Team collection progress as percentage"""
        total = self.collection.total_cards
        if total == 0:
            return 0
        return int((self.cards_collected_count() / total) * 100)
    
    def is_complete(self):
        """Check if team has collected all cards"""
        return self.cards_collected_count() >= self.collection.total_cards
    
    def check_and_complete(self):
        """Check if collection is complete and award rewards"""
        if self.completed_at:
            return False, "Already completed"
        
        if not self.is_complete():
            return False, "Collection not complete"
        
        # Mark as completed
        self.completed_at = timezone.now()
        self.save(update_fields=['completed_at'])
        
        # Award points to all members
        reward_points = self.collection.completion_reward_points
        captain_bonus = int(reward_points * 0.1)  # 10% captain bonus
        
        for member in self.members.all():
            points = reward_points
            if member.profile == self.captain:
                points += captain_bonus
            
            member.points_earned += points
            member.save(update_fields=['points_earned'])
            
            member.profile.points += points
            member.profile.save(update_fields=['points'])
        
        return True, f"Team completed! All members earned {reward_points} pts"
    
    def __str__(self):
        return f"{self.name} ({self.member_count()}/{self.max_members}) - {self.collection.name}"


class TeamMember(models.Model):
    """Members of a collection team"""
    team = models.ForeignKey(CollectionTeam, on_delete=models.CASCADE, related_name='members')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='team_memberships')
    
    # Contribution tracking
    cards_contributed = models.IntegerField(default=0, help_text="Number of cards contributed")
    points_earned = models.IntegerField(default=0, help_text="Points earned from team completion")
    
    # Timestamps
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Team Member"
        verbose_name_plural = "Team Members"
        unique_together = ['team', 'profile']  # One membership per team
        ordering = ['-joined_at']
    
    def contribution_percentage(self):
        """Member's contribution as percentage of team's cards"""
        total = self.team.cards_collected_count()
        if total == 0:
            return 0
        return int((self.cards_contributed / total) * 100)
    
    def is_captain(self):
        return self.profile == self.team.captain
    
    def __str__(self):
        role = " (Captain)" if self.is_captain() else ""
        return f"{self.profile.phone}{role} - {self.team.name}"


class TeamCardCollection(models.Model):
    """Shared team card pool - cards collected by team members"""
    team = models.ForeignKey(CollectionTeam, on_delete=models.CASCADE, related_name='team_cards')
    card = models.ForeignKey(EstateCard, on_delete=models.CASCADE, related_name='team_collections')
    contributed_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='team_contributions')
    
    # Timestamps
    contributed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Team Card Collection"
        verbose_name_plural = "Team Card Collections"
        unique_together = ['team', 'card']  # One copy per card per team
        ordering = ['-contributed_at']
    
    def __str__(self):
        return f"{self.team.name} - {self.card.get_display_title()} (by {self.contributed_by.phone})"


def contribute_card_to_team(profile, card, team):
    """
    Contribute a card to team collection.
    Returns (success, message, team_card)
    """
    # Check if user is a member
    try:
        member = TeamMember.objects.get(team=team, profile=profile)
    except TeamMember.DoesNotExist:
        return False, "You are not a member of this team", None
    
    # Check if team already has this card
    if TeamCardCollection.objects.filter(team=team, card=card).exists():
        return False, "Team already has this card", None
    
    # Check if team is still active
    if not team.is_active or team.completed_at:
        return False, "Team collection is no longer active", None
    
    # Add card to team collection
    team_card = TeamCardCollection.objects.create(
        team=team,
        card=card,
        contributed_by=profile
    )
    
    # Update member's contribution count
    member.cards_contributed += 1
    member.save(update_fields=['cards_contributed'])
    
    # Check if team completed collection
    completed, msg = team.check_and_complete()
    
    if completed:
        return True, f"Card contributed! {msg}", team_card
    
    return True, f"Card contributed! Team progress: {team.cards_collected_count()}/{team.collection.total_cards}", team_card
