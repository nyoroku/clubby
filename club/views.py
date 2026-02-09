# views.py - Complete with Partner Registration

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Q
from datetime import date
from django.views.decorators.http import require_http_methods
from django.db.models.functions import TruncMonth
from datetime import timedelta
from django.utils.crypto import get_random_string
import random

from .models import (
    Profile, PackCode, Scan, Reward, Redemption, OTP,
    Partnership, PartnershipEarning, ReferralSettings, Referral, PointTransfer, PointTransferSettings, PendingInvite,
ListingPartner, PartnerPayout, ProductListing, ProductRedemption, Challenge, ChallengeWinner, ChallengeEntry,
EstateCollection, EstateCard, UserCardCollection, TeaEstate
)


def normalize_phone(phone):
    """Normalize Kenyan phone numbers to +254 format"""
    phone = phone.strip().replace(" ", "")
    if phone.startswith("07"):
        phone = "+254" + phone[1:]
    elif phone.startswith("254"):
        phone = "+" + phone
    return phone


def generate_otp():
    """Generate 6-digit OTP"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


def send_otp_sms(phone, code):
    """Send OTP via SMS - integrate with your SMS provider"""
    print(f"SMS to {phone}: Your OTP is {code}")
    return True


# ============ PARTNER REGISTRATION VIEWS ============


@login_required
def partner_complete_profile(request):
    """Complete partner profile after OTP verification"""
    try:
        partnership = request.user.partnership
    except Partnership.DoesNotExist:
        messages.error(request, 'Partner account not found')
        return redirect('club:partner_register_otp')

    if partnership.profile_completed:
        return redirect('club:partner_dashboard')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        partner_type = request.POST.get('partner_type', '').strip()
        contact_person = request.POST.get('contact_person', '').strip()
        email = request.POST.get('email', '').strip()
        county = request.POST.get('county', '').strip()
        location_details = request.POST.get('location_details', '').strip()

        # Validate required fields
        if not all([name, partner_type, contact_person]):
            messages.error(request, 'Name, type, and contact person are required')
        else:
            # Update partnership
            partnership.name = name
            partnership.partner_type = partner_type
            partnership.contact_person = contact_person
            partnership.email = email
            partnership.county = county
            partnership.location_details = location_details
            partnership.profile_completed = True
            partnership.save()

            type_display = partnership.get_partner_type_display()
            messages.success(request, f'Welcome, {name}! Your {type_display} profile is complete.')
            return redirect('club:partner_dashboard')

    context = {
        'partnership': partnership,
        'county_choices': Profile.COUNTY_CHOICES,
    }
    return render(request, 'club/partner_complete_profile.html', context)


# ============ PARTNER DASHBOARD ============

@login_required
def partner_dashboard(request):
    """Main dashboard for partners"""
    try:
        partnership = request.user.partnership
    except Partnership.DoesNotExist:
        messages.error(request, 'Partner account not found. Please create one.')
        return redirect('club:partner_create')

    if not partnership.profile_completed:
        return redirect('club:partner_complete_profile')

    # Get statistics
    referred_users = Profile.objects.filter(
        partnership=partnership,
        profile_completed=True
    ).select_related('user').order_by('-created_at')[:20]

    recent_earnings = PartnershipEarning.objects.filter(
        partnership=partnership
    ).select_related(
        'profile', 'scan', 'scan__pack'
    ).order_by('-created_at')[:30]

    # Monthly stats
    thirty_days_ago = timezone.now() - timedelta(days=30)
    monthly_stats = PartnershipEarning.objects.filter(
        partnership=partnership,
        created_at__gte=thirty_days_ago
    ).aggregate(
        total_points=Sum('points_earned'),
        total_scans=Count('id')
    )

    # Shop-specific: Pending redemptions
    pending_redemptions = []
    if partnership.is_shop():
        pending_redemptions = Redemption.objects.filter(
            redeemed_at_shop=partnership,
            status__in=['pending', 'approved']
        ).select_related('profile', 'reward').order_by('-created_at')[:20]

    context = {
        'partnership': partnership,
        'referred_users': referred_users,
        'referred_count': partnership.referred_users_count(),
        'total_scans': partnership.total_scans_by_referrals(),
        'recent_earnings': recent_earnings,
        'monthly_stats': monthly_stats,
        'pending_redemptions': pending_redemptions,
    }

    return render(request, 'club/partner_dashboard.html', context)


@login_required
def partner_referral_link(request):
    """Partner's referral link page"""
    try:
        partnership = request.user.partnership
    except Partnership.DoesNotExist:
        messages.error(request, 'Partner account not found')
        return redirect('club:partner_register_otp')

    context = {
        'partnership': partnership,
    }
    return render(request, 'club/partner_referral_link.html', context)


# ============ SHOP REDEMPTION VIEWS ============

@login_required
def shop_verify_redemption(request):
    """Shop view to verify and fulfill redemptions"""
    try:
        partnership = request.user.partnership
    except Partnership.DoesNotExist:
        messages.error(request, 'Partner account not found')
        return redirect('club:partner_dashboard')

    if not partnership.is_shop():
        messages.error(request, 'This feature is only for shop partners')
        return redirect('club:partner_dashboard')

    if request.method == 'POST':
        redemption_code = request.POST.get('redemption_code', '').strip().upper()

        if not redemption_code:
            messages.error(request, 'Please enter a redemption code')
        else:
            try:
                redemption = Redemption.objects.get(
                    redemption_code=redemption_code,
                    redeemed_at_shop=partnership
                )

                if redemption.status == 'fulfilled':
                    messages.warning(request, 'This redemption has already been fulfilled')
                elif redemption.status == 'cancelled':
                    messages.error(request, 'This redemption was cancelled')
                else:
                    # Mark as fulfilled
                    redemption.status = 'fulfilled'
                    redemption.fulfilled = True
                    redemption.fulfilled_at = timezone.now()
                    redemption.save()

                    messages.success(request,
                                     f'Redemption fulfilled! Customer: {redemption.profile.phone}, '
                                     f'Reward: {redemption.reward.name}'
                                     )

                return redirect('club:shop_verify_redemption')

            except Redemption.DoesNotExist:
                messages.error(request, 'Invalid redemption code or not for your shop')

    # Get pending redemptions
    pending_redemptions = Redemption.objects.filter(
        redeemed_at_shop=partnership,
        status__in=['pending', 'approved']
    ).select_related('profile', 'reward').order_by('-created_at')

    context = {
        'partnership': partnership,
        'pending_redemptions': pending_redemptions,
    }
    return render(request, 'club/shop_verify_redemption.html', context)


# ============ USER VIEWS (Original + Updates) ============

def request_otp(request):
    """Request OTP page - supports partnership codes AND referral codes"""
    partnership = None
    partnership_code = request.GET.get('partner') or request.POST.get('partnership_code', '').strip().upper()

    # NEW: Handle referral code from link
    referral_code = request.GET.get('ref', '').strip().upper()
    
    # NEW: Handle UTM parameters
    utm_source = request.GET.get('utm_source', '').strip()
    utm_medium = request.GET.get('utm_medium', '').strip()
    utm_campaign = request.GET.get('utm_campaign', '').strip()

    if partnership_code:
        try:
            partnership = Partnership.objects.get(code=partnership_code, active=True)
        except Partnership.DoesNotExist:
            messages.warning(request, f'Partnership code "{partnership_code}" is invalid.')
            partnership_code = None
            
    # Store initial params in session immediately when landing
    if referral_code:
        request.session['referral_code'] = referral_code
    
    if utm_source:
        request.session['utm_data'] = {
            'utm_source': utm_source,
            'utm_medium': utm_medium,
            'utm_campaign': utm_campaign
        }

    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        # Get referral code from form if provided, else fall back to session/GET
        form_referral_code = request.POST.get('referral_code', '').strip().upper()
        if form_referral_code:
            referral_code = form_referral_code
        elif not referral_code:
            referral_code = request.session.get('referral_code', '')

        if not phone:
            messages.error(request, 'Phone number is required')
        else:
            phone = normalize_phone(phone)

            otp_code = generate_otp()
            OTP.objects.create(phone=phone, code=otp_code, is_partner=False)
            send_otp_sms(phone, otp_code)
            print(f"DEBUG: OTP {otp_code} created for {phone}")

            request.session['otp_phone'] = phone
            if partnership_code:
                request.session['partnership_code'] = partnership_code
            
            # Re-save referral code to session to be sure
            if referral_code:
                request.session['referral_code'] = referral_code

            messages.success(request, f'OTP sent to {phone}')
            return redirect('club:verify_otp')

    context = {
        'partnership': partnership,
        'partnership_code': partnership_code,
        'referral_code': referral_code or request.session.get('referral_code', ''),  # Pass to template
    }
    return render(request, 'club/request_otp.html', context)

def verify_otp(request):
    """Verify OTP and login/register user"""
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile'):
            return redirect('club:dashboard')
        elif hasattr(request.user, 'partnership'):
            return redirect('club:partner_dashboard')

    phone = request.session.get('otp_phone')
    partnership_code = request.session.get('partnership_code')

    if not phone:
        messages.error(request, 'Session expired. Please request OTP again.')
        return redirect('club:request_otp')

    phone = normalize_phone(phone)

    partnership = None
    if partnership_code:
        try:
            partnership = Partnership.objects.get(code=partnership_code, active=True)
        except Partnership.DoesNotExist:
            partnership_code = None

    if request.method == 'POST':
        otp_code = request.POST.get('otp', '').strip()

        if not otp_code:
            messages.error(request, 'Please enter OTP code')
            return render(request, 'club/verify_otp.html', {'phone': phone, 'partnership': partnership})

        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        otp_obj = OTP.objects.filter(
            phone=phone,
            code=otp_code,
            used=False,
            is_partner=False,
            created_at__gte=five_minutes_ago
        ).first()

        if otp_obj:
            otp_obj.used = True
            otp_obj.save(update_fields=['used'])

            try:
                profile = Profile.objects.get(phone=phone)
                created = False
                if partnership and not profile.partnership:
                    profile.partnership = partnership
                    profile.save(update_fields=['partnership'])
                    messages.info(request, f'Your account is now linked to {partnership.name}!')
            except Profile.DoesNotExist:
                username = f"user_{phone.replace('+', '').replace('-', '')}"
                user = User.objects.create_user(
                    username=username,
                    password=get_random_string(10)
                )
                profile = Profile.objects.create(
                    user=user,
                    phone=phone,
                    partnership=partnership,
                    profile_completed=False
                )
                
                # Check for UTM data in session and save immediately
                if 'utm_data' in request.session:
                    utm_data = request.session['utm_data']
                    profile.utm_source = utm_data.get('utm_source')
                    profile.utm_medium = utm_data.get('utm_medium')
                    profile.utm_campaign = utm_data.get('utm_campaign')
                    profile.save(update_fields=['utm_source', 'utm_medium', 'utm_campaign'])
                    
                created = True

            login(request, profile.user, backend='django.contrib.auth.backends.ModelBackend')

            request.session.pop('otp_phone', None)
            request.session.pop('partnership_code', None)

            if profile.profile_completed:
                messages.success(request, f'Welcome back, {profile.first_name}!')
                return redirect('club:dashboard')
            else:
                if created and partnership:
                    messages.success(request, f'Welcome! You\'ve registered via {partnership.name}')
                messages.info(request, 'Please complete your profile')
                return redirect('club:complete_profile')

        else:
            messages.error(request, 'Invalid or expired OTP. Please request a new one.')

    return render(request, 'club/verify_otp.html', {
        'phone': phone,
        'partnership': partnership,
    })


# ADD ALL THESE MISSING VIEWS TO YOUR views.py FILE
# Add after your existing views

# ============ USER AUTHENTICATION & PROFILE ============

@login_required
def complete_profile(request):
    """Complete user profile after OTP verification"""
    profile = request.user.profile

    if profile.profile_completed:
        return redirect('club:dashboard')

    # Get referral code from session (if came from referral link)
    session_referral_code = request.session.get('referral_code', '').strip().upper()

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        second_name = request.POST.get('second_name', '').strip()
        county = request.POST.get('county', '').strip()
        buyer_type = request.POST.get('buyer_type', '').strip()
        referral_code = request.POST.get('referral_code', '').strip().upper()

        # Use session referral code if form field is empty
        if not referral_code and session_referral_code:
            referral_code = session_referral_code

        if not all([first_name, second_name, county, buyer_type]):
            messages.error(request, 'All fields are required')
        else:
            profile.first_name = first_name
            profile.second_name = second_name
            profile.county = county
            profile.buyer_type = buyer_type
            profile.profile_completed = True
            
            # UTM / Traffic Source Tracking
            if not profile.utm_source and 'utm_data' in request.session:
                utm_data = request.session['utm_data']
                profile.utm_source = utm_data.get('utm_source')
                profile.utm_medium = utm_data.get('utm_medium')
                profile.utm_campaign = utm_data.get('utm_campaign')

            if referral_code and not profile.referred_by:
                try:
                    referrer = Profile.objects.get(referral_code=referral_code)
                    if referrer != profile and referrer.can_refer_more():
                        profile.referred_by = referrer

                        settings = ReferralSettings.get_settings()
                        if settings.referral_enabled:
                            referrer.points += settings.points_for_referrer
                            referrer.referral_points_earned += settings.points_for_referrer
                            referrer.save(update_fields=['points', 'referral_points_earned'])

                            profile.points += settings.points_for_referee

                            Referral.objects.create(
                                referrer=referrer,
                                referred=profile,
                                points_awarded_to_referrer=settings.points_for_referrer,
                                points_awarded_to_referred=settings.points_for_referee
                            )

                            messages.success(
                                request,
                                f'Referral applied! You earned {settings.points_for_referee} points!'
                            )
                except Profile.DoesNotExist:
                    messages.warning(request, 'Invalid referral code')

            profile.save()

            # Process pending invites
            invites_processed = process_pending_invites(profile)
            if invites_processed > 0:
                messages.success(request, f'You received points from {invites_processed} pending invite(s)!')

            # Clear referral code from session
            request.session.pop('referral_code', None)

            # Welcome message
            welcome_msg = f'Welcome, {first_name}! Your profile is complete.'
            if profile.partnership:
                welcome_msg += f' Thanks for joining via {profile.partnership.name}!'

            messages.success(request, welcome_msg)
            return redirect('club:dashboard')

    context = {
        'profile': profile,
        'prefilled_referral_code': session_referral_code,  # Pre-fill form
    }
    return render(request, 'club/profile.html', context)


# ============ USER DASHBOARD & SCANNING VIEWS ============

@login_required
def dashboard(request):
    """Main dashboard with all features"""
    profile = request.user.profile

    if not profile.profile_completed:
        return redirect('club:complete_profile')

    # Recent scans
    recent_scans = Scan.objects.filter(
        profile=profile
    ).select_related('pack').order_by('-scanned_at')[:10]

    # Total scans count
    total_scans = Scan.objects.filter(profile=profile).count()

    # Rewards
    rewards = Reward.objects.filter(active=True).order_by('cost_points')[:6]

    # Referral settings and count
    referral_settings = ReferralSettings.get_settings()
    referral_count = profile.successful_referrals_count()

    # Nearby shops for redemption
    nearby_shops = Partnership.objects.filter(
        partner_type='shop',
        active=True,
        profile_completed=True
    ).order_by('name')

    if profile.county:
        nearby_shops = nearby_shops.filter(county=profile.county)

    # Active Challenges
    now = timezone.now()
    active_challenges = Challenge.objects.filter(
        status='active',
        active=True,
        start_date__lte=now,
        end_date__gte=now
    ).order_by('-featured', '-draw_in_progress', 'end_date')[:3]

    # Check which challenges user has entered
    user_entered_challenges = []
    eligible_challenges = []

    if active_challenges:
        # Get entered challenge IDs
        entered_ids = ChallengeEntry.objects.filter(
            challenge__in=active_challenges,
            profile=profile
        ).values_list('challenge_id', flat=True)

        user_entered_challenges = [c for c in active_challenges if c.id in entered_ids]

        # Check eligibility for non-entered challenges
        for challenge in active_challenges:
            if challenge.id not in entered_ids:
                eligible_profiles = challenge.get_eligible_profiles()
                if profile in eligible_profiles:
                    eligible_challenges.append(challenge)

    # Challenges entered count
    challenges_entered = ChallengeEntry.objects.filter(profile=profile).count()

    # Collection Progress
    active_collection = EstateCollection.objects.filter(is_active=True).first()
    user_cards = UserCardCollection.objects.filter(profile=profile, is_duplicate=False).select_related('card', 'card__estate')
    user_card_ids = list(user_cards.values_list('card_id', flat=True))
    
    # Build card list with collected status
    collection_cards = []
    cards_remaining = 0
    if active_collection:
        all_cards = EstateCard.objects.filter(collection=active_collection, active=True).select_related('estate').order_by('card_number')
        for card in all_cards:
            is_collected = card.id in user_card_ids
            collection_cards.append({
                'card': card,
                'collected': is_collected,
            })
            if not is_collected:
                cards_remaining += 1
    
    collection_progress = 0
    progress_offset = 220
    if active_collection and active_collection.total_cards > 0:
        collection_progress = int((len(user_card_ids) / active_collection.total_cards) * 100)
        # Calculate stroke-dashoffset: 220 (circumference) - (220 * percentage / 100)
        progress_offset = 220 - int((220 * collection_progress) / 100)

    context = {
        'profile': profile,
        'recent_scans': recent_scans,
        'total_scans': total_scans,
        'rewards': rewards,
        'referral_settings': referral_settings,
        'referral_count': referral_count,
        'nearby_shops': nearby_shops,
        'active_challenges': active_challenges,
        'user_entered_challenges': user_entered_challenges,
        'eligible_challenges': eligible_challenges,
        'challenges_entered': challenges_entered,
        'collection_progress': collection_progress,
        'progress_offset': progress_offset,
        'user_cards': user_cards,
        'user_card_ids': user_card_ids,
        'active_collection': active_collection,
        'collection_cards': collection_cards,
        'cards_remaining': cards_remaining,
    }

    return render(request, 'club/dashboard.html', context)

@login_required
def create_card_gift(request, card_id):
    """Generate a gift link for a specific card"""
    from .models import EstateCard, CardGift
    profile = request.user.profile
    card = get_object_or_404(EstateCard, id=card_id)
    
    # Check if user has this card as a duplicate
    # (Actually we can allow gifting any card they have, but usually it's duplicates)
    # For now, just check if they have it
    has_card = UserCardCollection.objects.filter(profile=profile, card=card).exists()
    if not has_card:
        return JsonResponse({'success': False, 'message': 'You don\'t have this card!'})
    
    gift = CardGift.objects.create(
        sender=profile,
        card=card,
        token=uuid.uuid4().hex
    )
    
    # Build the full URL
    claim_url = request.build_absolute_uri(f"/gifts/claim/{gift.token}/")
    
    return JsonResponse({
        'success': True, 
        'claim_url': claim_url,
        'card_name': card.get_display_title()
    })


@login_required
def claim_card_gift(request, token):
    """Claim a gifted card"""
    from .models import CardGift
    profile = request.user.profile
    gift = get_object_or_404(CardGift, token=token)
    
    if gift.sender == profile:
        messages.warning(request, "You can't claim your own gift!")
        return redirect('club:my_collection')
        
    success, message = gift.claim(profile)
    if success:
        messages.success(request, f"🎁 {message}")
    else:
        messages.error(request, f"❌ {message}")
        
    return redirect('club:my_collection')

@login_required
def scan_pack(request):
    """
    Handle pack code scanning with partnership point awarding
    Shows scan form on GET, processes scan on POST
    """
    profile = request.user.profile
    
    # GET request - show the scan page
    if request.method != 'POST':
        recent_scans = Scan.objects.filter(profile=profile).order_by('-scanned_at')[:5]
        # Get and clear revealed card from session
        revealed_card = request.session.pop('revealed_card', None)
        
        # Get active collections for display
        from .models import EstateCollection
        from django.utils import timezone
        now = timezone.now()
        active_collections = EstateCollection.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).order_by('-start_date')
        
        return render(request, 'club/scan_pack.html', {
            'profile': profile,
            'recent_scans': recent_scans,
            'revealed_card': revealed_card,
            'active_collections': active_collections,
        })

    code = request.POST.get('code', '').strip().upper()
    if not code:
        messages.warning(request, 'Please enter a pack code.')
        return redirect('club:scan_pack')
    try:
        with transaction.atomic():
            is_ajax = request.headers.get('HX-Request') or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            
            try:
                pack = PackCode.objects.select_for_update().get(code=code)
            except PackCode.DoesNotExist:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': '❌ Invalid code. Please check and try again.'})
                messages.error(request, '❌ Invalid code. Please check and try again.')
                return redirect('club:scan_pack')

            if pack.used:
                msg = f'This code was already used on {pack.used_at.strftime("%b %d, %Y")}'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': msg})
                messages.error(request, msg)
                return redirect('club:scan_pack')

            points = pack.points
            profile.points += points
            profile.save(update_fields=['points'])

            pack.mark_used(profile)

            scan = Scan.objects.create(
                profile=profile,
                pack=pack,
                points_awarded=points
            )

            # Award partnership points if applicable
            try:
                scan.award_partnership_points()
            except:
                pass  # Ignore if method doesn't exist
            
            # Try to reveal a Tea Estates card
            revealed_card = None
            try:
                from .models import reveal_card_for_scan
                revealed_card = reveal_card_for_scan(scan, profile)
                print(f"DEBUG VIEW: Card reveal returned: {revealed_card}")
            except Exception as e:
                print(f"DEBUG VIEW: Card reveal crashed: {e}")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': f'Card reveal failed: {str(e)}'})
                messages.warning(request, f'Card reveal failed: {str(e)}')
            
            # Build success message and store reveal data for animation
            if revealed_card:
                print("DEBUG VIEW: Processing revealed card for display")
                reveal_data = {
                    'name': revealed_card.card.get_display_title(),
                    'region': revealed_card.card.estate.region,
                    'rarity': revealed_card.card.rarity,
                    'card_number': revealed_card.card.card_number,
                    'is_duplicate': revealed_card.is_duplicate,
                    'reward_points': revealed_card.card.reward_points,
                    'image': revealed_card.card.card_image.url if revealed_card.card.card_image else None,
                }
                
                # If HTMX/Ajax, return JSON directly for instant reveal
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'revealed_card': reveal_data,
                        'points_awarded': points,
                        'message': f'You unlocked {revealed_card.card.get_display_title()}!'
                    })

                # Store in session for standard redirects
                request.session['revealed_card'] = reveal_data
                
                if not revealed_card.is_duplicate:
                    messages.success(request, f'✅ Code accepted! You unlocked {revealed_card.card.get_display_title()}!', extra_tags='card-reveal')
                else:
                    messages.success(request, f'✅ Code accepted! You got a duplicate (+5 bonus points)', extra_tags='card-reveal-duplicate')
            else:
                if is_ajax:
                    return JsonResponse({'success': True, 'points_awarded': points, 'message': f'You earned {points} points!'})
                messages.success(request, f'✅ You earned {points} points! New balance: {profile.points} points')
            
            return redirect('club:scan_pack')

    except PackCode.DoesNotExist:
        if request.headers.get('HX-Request') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Invalid code. Please check and try again.'})
        messages.error(request, '❌ Invalid code. Please check and try again.')
        return redirect('club:scan_pack')
    except Exception as e:
        if request.headers.get('HX-Request') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})
        messages.error(request, f'Error: {str(e)}')
        return redirect('club:scan_pack')


@login_required
def redeem_reward_htmx(request, reward_id):
    """Redeem a reward - HTMX endpoint with shop selection"""
    if request.method != 'POST':
        return HttpResponse(
            '<div class="notification is-warning">Invalid request</div>'
        )

    profile = request.user.profile
    reward = get_object_or_404(Reward, id=reward_id, active=True)

    if profile.points < reward.cost_points:
        return HttpResponse(
            f'<div class="notification is-danger">'
            f'<strong>Insufficient points!</strong> You need '
            f'{reward.cost_points - profile.points} more points.'
            f'</div>'
        )

    # Get shop if reward is shop-redeemable
    shop_id = request.POST.get('shop_id')
    shop = None

    if reward.available_at_shops and shop_id:
        shop = get_object_or_404(Partnership, id=shop_id, partner_type='shop', active=True)

        # Check if reward is available at this shop
        if not reward.partner_shops.filter(id=shop.id).exists():
            return HttpResponse(
                '<div class="notification is-danger">'
                'This reward is not available at the selected shop.'
                '</div>'
            )

    try:
        with transaction.atomic():
            profile.points -= reward.cost_points
            profile.save(update_fields=['points'])

            redemption = Redemption.objects.create(
                profile=profile,
                reward=reward,
                redeemed_at_shop=shop,
                status='pending' if shop else 'fulfilled',
                fulfilled=not shop
            )

            if shop:
                message = (
                    f'<div class="notification is-success">'
                    f'<strong>Redeemed!</strong> You\'ve successfully redeemed '
                    f'<strong>{reward.name}</strong>.<br>'
                    f'<strong>Redemption Code:</strong> <code style="font-size: 1.2em; padding: 5px; background: #f5f5f5;">{redemption.redemption_code}</code><br>'
                    f'Visit <strong>{shop.name}</strong> and show this code.<br>'
                    f'Remaining balance: <strong>{profile.points} points</strong>'
                    f'</div>'
                )
            else:
                message = (
                    f'<div class="notification is-success">'
                    f'<strong>Redeemed!</strong> You\'ve successfully redeemed '
                    f'<strong>{reward.name}</strong>. '
                    f'Remaining balance: <strong>{profile.points} points</strong>'
                    f'</div>'
                )

            message += f'''
                <script>
                    document.getElementById('points-count').textContent = '{profile.points}';
                    setTimeout(() => location.reload(), 3000);
                </script>
            '''

            return HttpResponse(message)

    except Exception as e:
        return HttpResponse(
            f'<div class="notification is-danger">'
            f'<strong>Error:</strong> {str(e)}'
            f'</div>'
        )


@login_required
def referral_page(request):
    """Referral page for user-to-user referrals"""
    profile = request.user.profile
    referral_settings = ReferralSettings.get_settings()

    # Get referrals history
    referral_history = Referral.objects.filter(
        referrer=profile
    ).select_related('referred').order_by('-created_at')

    # Build absolute referral link
    referral_link = request.build_absolute_uri(
        f'/club/request-otp/?ref={profile.referral_code}'
    )

    context = {
        'profile': profile,
        'referral_settings': referral_settings,
        'settings': referral_settings,  # Alias for template compatibility
        'referral_history': referral_history,
        'referral_count': profile.successful_referrals_count(),
        'can_refer_more': profile.can_refer_more(),
        'referral_code': profile.referral_code,
        'referral_link': referral_link,
    }

    return render(request, 'club/referral.html', context)


# ============ PARTNER REGISTRATION VIEWS ============

def partner_register_otp(request):
    """Request OTP for partner registration"""
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        if not phone:
            messages.error(request, 'Phone number is required')
        else:
            phone = normalize_phone(phone)

            # Generate and send OTP
            otp_code = generate_otp()
            OTP.objects.create(phone=phone, code=otp_code, is_partner=True)
            send_otp_sms(phone, otp_code)
            print(f"DEBUG: Partner OTP {otp_code} created for {phone}")

            # Store phone in session
            request.session['partner_otp_phone'] = phone

            messages.success(request, f'OTP sent to {phone}')
            return redirect('club:partner_verify_otp')

    # Capture UTMs
    utm_source = request.GET.get('utm_source', '').strip()
    utm_medium = request.GET.get('utm_medium', '').strip()
    utm_campaign = request.GET.get('utm_campaign', '').strip()

    if utm_source:
        request.session['utm_data'] = {
            'utm_source': utm_source,
            'utm_medium': utm_medium,
            'utm_campaign': utm_campaign
        }

    return render(request, 'club/partner_register_otp.html')


def partner_verify_otp(request):
    """Verify OTP and create/login partner account"""
    if hasattr(request.user, 'partnership'):
        return redirect('club:partner_dashboard')

    phone = request.session.get('partner_otp_phone')

    if not phone:
        messages.error(request, 'Session expired. Please request OTP again.')
        return redirect('club:partner_register_otp')

    phone = normalize_phone(phone)

    if request.method == 'POST':
        otp_code = request.POST.get('otp', '').strip()

        if not otp_code:
            messages.error(request, 'Please enter OTP code')
            return render(request, 'club/partner_verify_otp.html', {'phone': phone})

        # Verify OTP
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        otp_obj = OTP.objects.filter(
            phone=phone,
            code=otp_code,
            used=False,
            is_partner=True,
            created_at__gte=five_minutes_ago
        ).first()

        if otp_obj:
            # Mark as used
            otp_obj.used = True
            otp_obj.save(update_fields=['used'])

            # Get or create partnership
            try:
                partnership = Partnership.objects.get(phone=phone)
                created = False
            except Partnership.DoesNotExist:
                username = f"partner_{phone.replace('+', '').replace('-', '')}"
                user = User.objects.create_user(
                    username=username,
                    password=get_random_string(10)
                )
                partnership = Partnership.objects.create(
                    user=user,
                    phone=phone,
                    profile_completed=False
                )
                created = True

            login(request, partnership.user, backend='django.contrib.auth.backends.ModelBackend')

            # Clean session
            request.session.pop('partner_otp_phone', None)

            if partnership.profile_completed:
                messages.success(request, f'Welcome back, {partnership.name}!')
                return redirect('club:partner_dashboard')
            else:
                if created:
                    messages.success(request, 'Welcome! Please complete your profile')
                else:
                    messages.info(request, 'Please complete your profile')
                return redirect('club:partner_complete_profile')
        else:
            messages.error(request, 'Invalid or expired OTP. Please request a new one.')

    return render(request, 'club/partner_verify_otp.html', {'phone': phone})


@login_required
def partner_complete_profile(request):
    """Complete partner profile after OTP verification"""
    try:
        partnership = request.user.partnership
    except Partnership.DoesNotExist:
        messages.error(request, 'Partner account not found')
        return redirect('club:partner_register_otp')

    if partnership.profile_completed:
        return redirect('club:partner_dashboard')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        partner_type = request.POST.get('partner_type', '').strip()
        contact_person = request.POST.get('contact_person', '').strip()
        email = request.POST.get('email', '').strip()
        county = request.POST.get('county', '').strip()
        location_details = request.POST.get('location_details', '').strip()

        # Validate required fields
        if not all([name, partner_type, contact_person]):
            messages.error(request, 'Name, type, and contact person are required')
        else:
            # Update partnership
            partnership.name = name
            partnership.partner_type = partner_type
            partnership.contact_person = contact_person
            partnership.email = email
            partnership.county = county
            partnership.location_details = location_details
            partnership.profile_completed = True
            partnership.save()

            type_display = partnership.get_partner_type_display()
            messages.success(request, f'Welcome, {name}! Your {type_display} profile is complete.')
            return redirect('club:partner_dashboard')

    context = {
        'partnership': partnership,
        'county_choices': Profile.COUNTY_CHOICES,
    }
    return render(request, 'club/partner_complete_profile.html', context)


@login_required
def partner_referral_link(request):
    """Partner's referral link page"""
    try:
        partnership = request.user.partnership
    except Partnership.DoesNotExist:
        messages.error(request, 'Partner account not found')
        return redirect('club:partner_register_otp')

    context = {
        'partnership': partnership,
    }
    return render(request, 'club/partner_referral_link.html', context)


# ============ USER VIEWS ============

@login_required
def user_redemptions(request):
    """View user's redemption history - both rewards and products"""
    profile = request.user.profile

    # Regular reward redemptions
    redemptions = Redemption.objects.filter(
        profile=profile
    ).select_related('reward', 'redeemed_at_shop').order_by('-created_at')

    # Product redemptions
    product_redemptions = ProductRedemption.objects.filter(
        profile=profile
    ).select_related(
        'product',
        'product__listing_partner',
        'redeemed_at_shop'
    ).order_by('-created_at')

    context = {
        'profile': profile,
        'redemptions': redemptions,  # Reward redemptions
        'product_redemptions': product_redemptions,  # Product redemptions
    }

    return render(request, 'club/user_redemptions.html', context)


def challenges_list(request):
    """Browse all active and upcoming challenges"""
    now = timezone.now()

    # Active challenges
    active_challenges = Challenge.objects.filter(
        status='active',
        active=True,
        start_date__lte=now,
        end_date__gte=now
    ).order_by('-featured', 'end_date')

    # Upcoming challenges
    upcoming_challenges = Challenge.objects.filter(
        status='upcoming',
        active=True,
        start_date__gt=now
    ).order_by('start_date')

    # Recently ended with winners
    ended_challenges = Challenge.objects.filter(
        status='winners_selected',
        active=True
    ).order_by('-winners_selected_at')[:5]

    context = {
        'active_challenges': active_challenges,
        'upcoming_challenges': upcoming_challenges,
        'ended_challenges': ended_challenges,
    }

    return render(request, 'club/challenges_list.html', context)



@login_required
def enter_challenge(request, challenge_id):
    """Enter a challenge"""
    challenge = get_object_or_404(Challenge, id=challenge_id, active=True, status='active')
    profile = request.user.profile

    # Check if already entered
    if ChallengeEntry.objects.filter(challenge=challenge, profile=profile).exists():
        messages.warning(request, 'You have already entered this challenge!')
        return redirect('club:challenge_detail', challenge_id=challenge.id)

    # Check eligibility
    eligible_profiles = challenge.get_eligible_profiles()
    if profile not in eligible_profiles:
        messages.error(request, 'You are not eligible for this challenge')
        return redirect('club:challenge_detail', challenge_id=challenge.id)

    # Create entry
    entry_weight = challenge.calculate_entry_weight(profile)
    ChallengeEntry.objects.create(
        challenge=challenge,
        profile=profile,
        entry_weight=entry_weight,
        points_at_entry=profile.points,
        referrals_at_entry=profile.successful_referrals_count()
    )

    messages.success(
        request,
        f'Successfully entered {challenge.title}! '
        f'Your entry weight: {entry_weight:.2f}. '
        f'Winners will be announced on {challenge.end_date.strftime("%B %d, %Y")}'
    )

    return redirect('club:challenge_detail', challenge_id=challenge.id)



@login_required
def my_challenges(request):
    """View user's challenge history"""
    profile = request.user.profile

    # Challenges entered
    entries = ChallengeEntry.objects.filter(
        profile=profile
    ).select_related('challenge').order_by('-entered_at')

    # Challenges won
    wins = ChallengeWinner.objects.filter(
        profile=profile
    ).select_related('challenge').order_by('-selected_at')

    context = {
        'profile': profile,
        'entries': entries,
        'wins': wins,
    }

    return render(request, 'club/my_challenges.html', context)


# ADMIN HELPER VIEW (can be called via management command or admin action)
def select_challenge_winners_view(request, challenge_id):
    """
    Admin view to select winners for a challenge
    This should be restricted to admin users
    """
    if not request.user.is_staff:
        messages.error(request, 'Unauthorized')
        return redirect('club:dashboard')

    challenge = get_object_or_404(Challenge, id=challenge_id)

    if challenge.status == 'winners_selected':
        messages.warning(request, 'Winners already selected for this challenge')
        return redirect('club:challenge_winners', challenge_id=challenge.id)

    if challenge.status != 'ended' and challenge.end_date > timezone.now():
        messages.error(request, 'Challenge has not ended yet')
        return redirect('club:challenge_detail', challenge_id=challenge.id)

    try:
        winners = challenge.select_winners()
        messages.success(
            request,
            f'Successfully selected {len(winners)} winners for {challenge.title}!'
        )

        # TODO: Send notifications to winners via SMS/email

        return redirect('club:challenge_winners', challenge_id=challenge.id)

    except ValueError as e:
        messages.error(request, str(e))
        return redirect('club:challenge_detail', challenge_id=challenge.id)
    except Exception as e:
        messages.error(request, f'Error selecting winners: {str(e)}')
        return redirect('club:challenge_detail', challenge_id=challenge.id)


@login_required
def logout_view(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('club:request_otp')


# ============ SHOP FINDER VIEWS (Public/User) ============

def shop_finder(request):
    """Find shops where users can redeem rewards"""
    county = request.GET.get('county', '')

    shops = Partnership.objects.filter(
        partner_type='shop',
        active=True,
        profile_completed=True
    ).order_by('name')

    if county:
        shops = shops.filter(county=county)

    context = {
        'shops': shops,
        'county_choices': Profile.COUNTY_CHOICES,
        'selected_county': county,
    }

    return render(request, 'club/shop_finder.html', context)


def shop_detail(request, shop_id):
    """View shop details and available rewards"""
    shop = get_object_or_404(
        Partnership,
        id=shop_id,
        partner_type='shop',
        active=True,
        profile_completed=True
    )

    available_rewards = shop.available_rewards.filter(active=True).order_by('cost_points')

    context = {
        'shop': shop,
        'available_rewards': available_rewards,
    }

    return render(request, 'club/shop_detail.html', context)


@login_required
def transfer_points(request):
    """Transfer points to another user or invite new user"""
    profile = request.user.profile
    settings = PointTransferSettings.get_settings()

    if not settings.transfer_enabled:
        messages.error(request, 'Point transfers are currently disabled.')
        return redirect('club:dashboard')

    # Calculate today's transfer total
    today_transfers = PointTransfer.objects.filter(
        sender=profile,
        created_at__date=date.today(),
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0

    remaining_limit = settings.daily_transfer_limit - today_transfers

    if request.method == 'POST':
        recipient_phone = request.POST.get('recipient_phone', '').strip()
        amount = request.POST.get('amount', '').strip()
        message_text = request.POST.get('message', '').strip()

        # Validate inputs
        if not recipient_phone or not amount:
            messages.error(request, 'Phone number and amount are required')
            return redirect('club:transfer_points')

        try:
            amount = int(amount)
        except ValueError:
            messages.error(request, 'Invalid amount')
            return redirect('club:transfer_points')

        # Normalize phone
        recipient_phone = normalize_phone(recipient_phone)

        # Check if trying to send to self
        if recipient_phone == profile.phone:
            messages.error(request, 'You cannot transfer points to yourself')
            return redirect('club:transfer_points')

        # Validate amount limits
        if amount < settings.min_transfer_amount:
            messages.error(request, f'Minimum transfer is {settings.min_transfer_amount} points')
            return redirect('club:transfer_points')

        if amount > settings.max_transfer_amount:
            messages.error(request, f'Maximum transfer is {settings.max_transfer_amount} points')
            return redirect('club:transfer_points')

        if amount > remaining_limit:
            messages.error(request, f'Daily limit exceeded. You can only transfer {remaining_limit} more points today.')
            return redirect('club:transfer_points')

        # Calculate fee
        fee = int(amount * (settings.transfer_fee_percentage / 100))
        total_deduction = amount + fee
        net_amount = amount

        # Check sender has enough points
        if profile.points < total_deduction:
            messages.error(request, f'Insufficient points. You need {total_deduction} points (including {fee} fee)')
            return redirect('club:transfer_points')

        # Check if recipient is registered
        try:
            recipient = Profile.objects.get(phone=recipient_phone)

            # Registered user - process transfer immediately
            with transaction.atomic():
                # Deduct from sender
                profile.points -= total_deduction
                profile.save(update_fields=['points'])

                # Add to recipient
                recipient.points += net_amount
                recipient.save(update_fields=['points'])

                # Create transfer record
                PointTransfer.objects.create(
                    sender=profile,
                    recipient=recipient,
                    amount=amount,
                    fee=fee,
                    net_amount=net_amount,
                    message=message_text,
                    status='completed'
                )

                messages.success(
                    request,
                    f'Successfully sent {amount} points to {recipient.first_name} {recipient.second_name}!'
                )

                # TODO: Send SMS notification to recipient
                # send_sms(recipient_phone, f"You received {amount} points from {profile.first_name}!")

        except Profile.DoesNotExist:
            # User not registered - create pending invite

            # Check if already invited this phone
            existing_invite = PendingInvite.objects.filter(
                inviter=profile,
                phone=recipient_phone,
                accepted=False
            ).first()

            if existing_invite:
                messages.warning(request, f'You already have a pending invite to {recipient_phone}')
                return redirect('club:transfer_points')

            # Deduct points from sender and hold them
            with transaction.atomic():
                profile.points -= total_deduction
                profile.save(update_fields=['points'])

                # Create pending invite
                PendingInvite.objects.create(
                    inviter=profile,
                    phone=recipient_phone,
                    points_promised=net_amount,
                    message=message_text
                )

                messages.success(
                    request,
                    f'Invite sent to {recipient_phone}! They will receive {net_amount} points when they register. '
                    f'If they use your referral code, you\'ll also earn referral points!'
                )

                # TODO: Send SMS invite
                # send_sms(recipient_phone,
                #          f"{profile.first_name} wants to send you {net_amount} points! "
                #          f"Register at {request.scheme}://{request.get_host()}/club/ "
                #          f"with code {profile.referral_code}")

        return redirect('club:transfer_history')

    # GET request - show form
    context = {
        'profile': profile,
        'settings': settings,
        'today_transfers': today_transfers,
        'remaining_limit': remaining_limit,
    }
    return render(request, 'club/transfer_points.html', context)


@login_required
def transfer_history(request):
    """View transfer history"""
    profile = request.user.profile

    # Transfers sent
    sent_transfers = PointTransfer.objects.filter(
        sender=profile
    ).select_related('recipient').order_by('-created_at')[:20]

    # Transfers received
    received_transfers = PointTransfer.objects.filter(
        recipient=profile
    ).select_related('sender').order_by('-created_at')[:20]

    # Pending invites
    pending_invites = PendingInvite.objects.filter(
        inviter=profile,
        accepted=False
    ).order_by('-created_at')

    # Stats
    total_sent = PointTransfer.objects.filter(
        sender=profile,
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_received = PointTransfer.objects.filter(
        recipient=profile,
        status='completed'
    ).aggregate(total=Sum('net_amount'))['total'] or 0

    context = {
        'profile': profile,
        'sent_transfers': sent_transfers,
        'received_transfers': received_transfers,
        'pending_invites': pending_invites,
        'total_sent': total_sent,
        'total_received': total_received,
    }
    return render(request, 'club/transfer_history.html', context)


@login_required
def cancel_invite(request, invite_id):
    """Cancel a pending invite and refund points"""
    profile = request.user.profile

    invite = get_object_or_404(PendingInvite, id=invite_id, inviter=profile, accepted=False)

    if request.method == 'POST':
        with transaction.atomic():
            # Refund points to inviter
            settings = PointTransferSettings.get_settings()
            fee = int(invite.points_promised * (settings.transfer_fee_percentage / 100))
            refund_amount = invite.points_promised + fee

            profile.points += refund_amount
            profile.save(update_fields=['points'])

            # Delete invite
            invite.delete()

            messages.success(request, f'Invite cancelled. {refund_amount} points refunded to your account.')

    return redirect('club:transfer_history')


# ADD THIS HELPER FUNCTION TO PROCESS INVITES WHEN USER REGISTERS
def process_pending_invites(new_profile):
    """
    Process any pending invites for this user when they register
    Call this in complete_profile view after profile is saved
    """
    pending_invites = PendingInvite.objects.filter(
        phone=new_profile.phone,
        accepted=False
    )

    referral_settings = ReferralSettings.get_settings()

    for invite in pending_invites:
        with transaction.atomic():
            # Give promised points to new user
            new_profile.points += invite.points_promised
            new_profile.save(update_fields=['points'])

            # Create transfer record
            PointTransfer.objects.create(
                sender=invite.inviter,
                recipient=new_profile,
                amount=invite.points_promised,
                fee=0,  # Fee already deducted when invite was created
                net_amount=invite.points_promised,
                message=invite.message,
                status='completed',
                was_invite=True,
                invite_phone=invite.phone,
                invite_accepted=True
            )

            # If new user uses inviter's referral code, give referral bonus
            if new_profile.referred_by == invite.inviter:
                # Already got referral points, just mark the connection
                messages.info(
                    None,
                    f'You received {invite.points_promised} points from {invite.inviter.first_name} '
                    f'plus {referral_settings.points_for_referee} referral bonus!'
                )
            else:
                # Give referral bonus to inviter since they brought this user
                invite.inviter.points += referral_settings.points_for_referrer
                invite.inviter.referral_points_earned += referral_settings.points_for_referrer
                invite.inviter.save(update_fields=['points', 'referral_points_earned'])

                # Set referral relationship
                new_profile.referred_by = invite.inviter
                new_profile.points += referral_settings.points_for_referee
                new_profile.save(update_fields=['referred_by', 'points'])

                # Create referral record
                Referral.objects.create(
                    referrer=invite.inviter,
                    referred=new_profile,
                    points_awarded_to_referrer=referral_settings.points_for_referrer,
                    points_awarded_to_referred=referral_settings.points_for_referee
                )

            # Mark invite as accepted
            invite.accepted = True
            invite.accepted_at = timezone.now()
            invite.save()

    return pending_invites.count()


def listing_partner_register_otp(request):
    """Request OTP for listing partner registration"""
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        if not phone:
            messages.error(request, 'Phone number is required')
        else:
            phone = normalize_phone(phone)

            # Generate and send OTP
            otp_code = generate_otp()
            OTP.objects.create(phone=phone, code=otp_code, is_partner=True)
            send_otp_sms(phone, otp_code)
            print(f"DEBUG: Listing Partner OTP {otp_code} created for {phone}")

            request.session['listing_partner_otp_phone'] = phone

            messages.success(request, f'OTP sent to {phone}')
            return redirect('club:listing_partner_verify_otp')

    return render(request, 'club/listing_partner_register_otp.html')


def listing_partner_verify_otp(request):
    """Verify OTP and create/login listing partner account"""
    if hasattr(request.user, 'listingpartner'):
        return redirect('club:listing_partner_dashboard')

    phone = request.session.get('listing_partner_otp_phone')

    if not phone:
        messages.error(request, 'Session expired. Please request OTP again.')
        return redirect('club:listing_partner_register_otp')

    phone = normalize_phone(phone)

    if request.method == 'POST':
        otp_code = request.POST.get('otp', '').strip()

        if not otp_code:
            messages.error(request, 'Please enter OTP code')
            return render(request, 'club/listing_partner_verify_otp.html', {'phone': phone})

        # Verify OTP
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        otp_obj = OTP.objects.filter(
            phone=phone,
            code=otp_code,
            used=False,
            is_partner=True,
            created_at__gte=five_minutes_ago
        ).first()

        if otp_obj:
            otp_obj.used = True
            otp_obj.save(update_fields=['used'])

            # Get or create listing partner
            try:
                listing_partner = ListingPartner.objects.get(phone=phone)
                created = False
            except ListingPartner.DoesNotExist:
                username = f"listing_{phone.replace('+', '').replace('-', '')}"
                user = User.objects.create_user(
                    username=username,
                    password=get_random_string(10)
                )
                listing_partner = ListingPartner.objects.create(
                    user=user,
                    phone=phone,
                    profile_completed=False,
                    approved=False
                )
                created = True

            login(request, listing_partner.user, backend='django.contrib.auth.backends.ModelBackend')

            request.session.pop('listing_partner_otp_phone', None)

            if listing_partner.profile_completed:
                messages.success(request, f'Welcome back, {listing_partner.company_name}!')
                return redirect('club:listing_partner_dashboard')
            else:
                if created:
                    messages.success(request, 'Welcome! Please complete your company profile')
                else:
                    messages.info(request, 'Please complete your profile')
                return redirect('club:listing_partner_complete_profile')
        else:
            messages.error(request, 'Invalid or expired OTP. Please request a new one.')

    return render(request, 'club/listing_partner_verify_otp.html', {'phone': phone})


@login_required
def listing_partner_complete_profile(request):
    """Complete listing partner profile"""
    try:
        listing_partner = request.user.listingpartner
    except ListingPartner.DoesNotExist:
        messages.error(request, 'Listing partner account not found')
        return redirect('club:listing_partner_register_otp')

    if listing_partner.profile_completed:
        return redirect('club:listing_partner_dashboard')

    if request.method == 'POST':
        company_name = request.POST.get('company_name', '').strip()
        contact_person = request.POST.get('contact_person', '').strip()
        email = request.POST.get('email', '').strip()
        business_registration = request.POST.get('business_registration', '').strip()
        tax_pin = request.POST.get('tax_pin', '').strip()
        bank_name = request.POST.get('bank_name', '').strip()
        bank_account_number = request.POST.get('bank_account_number', '').strip()
        bank_account_name = request.POST.get('bank_account_name', '').strip()
        mpesa_number = request.POST.get('mpesa_number', '').strip()

        if not all([company_name, contact_person, email]):
            messages.error(request, 'Company name, contact person, and email are required')
        else:
            listing_partner.company_name = company_name
            listing_partner.contact_person = contact_person
            listing_partner.email = email
            listing_partner.business_registration = business_registration
            listing_partner.tax_pin = tax_pin
            listing_partner.bank_name = bank_name
            listing_partner.bank_account_number = bank_account_number
            listing_partner.bank_account_name = bank_account_name
            listing_partner.mpesa_number = mpesa_number
            listing_partner.profile_completed = True
            listing_partner.save()

            messages.success(
                request,
                f'Profile completed! Your account is pending approval by Melvins admin. '
                f'You will be notified once approved.'
            )
            return redirect('club:listing_partner_dashboard')

    context = {
        'listing_partner': listing_partner,
    }
    return render(request, 'club/listing_partner_complete_profile.html', context)


# ============ LISTING PARTNER DASHBOARD ============

@login_required
def listing_partner_dashboard(request):
    """Main dashboard for listing partners"""
    try:
        listing_partner = request.user.listingpartner
    except ListingPartner.DoesNotExist:
        messages.error(request, 'Listing partner account not found. Please create one.')
        return redirect('club:listing_partner_create')

    if not listing_partner.profile_completed:
        return redirect('club:listing_partner_complete_profile')

    # Get statistics
    products = listing_partner.products.all().order_by('-created_at')

    pending_products = products.filter(status='pending').count()
    approved_products = products.filter(status='approved', active=True).count()
    rejected_products = products.filter(status='rejected').count()

    # Recent redemptions
    recent_redemptions = ProductRedemption.objects.filter(
        product__listing_partner=listing_partner
    ).select_related('product', 'profile', 'redeemed_at_shop').order_by('-created_at')[:20]

    # Financial stats
    unpaid_redemptions = ProductRedemption.objects.filter(
        product__listing_partner=listing_partner,
        status='fulfilled',
        paid_to_partner=False
    ).aggregate(total=Sum('partner_earning'))['total'] or 0

    # Update pending payout
    listing_partner.pending_payout = unpaid_redemptions
    listing_partner.save(update_fields=['pending_payout'])

    # Monthly stats
    thirty_days_ago = timezone.now() - timedelta(days=30)
    monthly_redemptions = ProductRedemption.objects.filter(
        product__listing_partner=listing_partner,
        created_at__gte=thirty_days_ago,
        status='fulfilled'
    ).aggregate(
        total_redemptions=Count('id'),
        total_revenue=Sum('partner_earning')
    )

    context = {
        'listing_partner': listing_partner,
        'products': products[:10],
        'total_products': listing_partner.total_products(),
        'pending_products': pending_products,
        'approved_products': approved_products,
        'rejected_products': rejected_products,
        'recent_redemptions': recent_redemptions,
        'monthly_redemptions': monthly_redemptions['total_redemptions'] or 0,
        'monthly_revenue': monthly_redemptions['total_revenue'] or 0,
    }

    return render(request, 'club/listing_partner_dashboard.html', context)


# ============ PRODUCT MANAGEMENT ============

@login_required
def add_product(request):
    """Add new product listing"""
    try:
        listing_partner = request.user.listingpartner
    except ListingPartner.DoesNotExist:
        messages.error(request, 'Listing partner account not found')
        return redirect('club:listing_partner_dashboard')

    if not listing_partner.approved:
        messages.error(request, 'Your account must be approved before listing products')
        return redirect('club:listing_partner_dashboard')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', '').strip()
        partner_price = request.POST.get('partner_price', '').strip()
        stock_quantity = request.POST.get('stock_quantity', '').strip()
        image = request.FILES.get('image')

        if not all([name, description, partner_price, stock_quantity]):
            messages.error(request, 'All fields are required')
        else:
            try:
                product = ProductListing.objects.create(
                    listing_partner=listing_partner,
                    name=name,
                    description=description,
                    category=category,
                    partner_price=partner_price,
                    stock_quantity=stock_quantity,
                    image=image,
                    status='pending'
                )

                messages.success(
                    request,
                    f'Product "{name}" submitted for approval. '
                    f'Melvins admin will review and set the points value.'
                )
                return redirect('club:listing_partner_dashboard')

            except Exception as e:
                messages.error(request, f'Error creating product: {str(e)}')

    context = {
        'listing_partner': listing_partner,
    }
    return render(request, 'club/add_product.html', context)


@login_required
def edit_product(request, product_id):
    """Edit existing product"""
    try:
        listing_partner = request.user.listingpartner
    except ListingPartner.DoesNotExist:
        messages.error(request, 'Listing partner account not found')
        return redirect('club:listing_partner_dashboard')

    product = get_object_or_404(ProductListing, id=product_id, listing_partner=listing_partner)

    if request.method == 'POST':
        product.name = request.POST.get('name', '').strip()
        product.description = request.POST.get('description', '').strip()
        product.category = request.POST.get('category', '').strip()
        product.partner_price = request.POST.get('partner_price')
        product.stock_quantity = request.POST.get('stock_quantity')

        if request.FILES.get('image'):
            product.image = request.FILES.get('image')

        # If product was rejected, reset to pending when edited
        if product.status == 'rejected':
            product.status = 'pending'
            product.rejection_reason = ''

        product.save()

        messages.success(request, f'Product "{product.name}" updated successfully')
        return redirect('club:listing_partner_dashboard')

    context = {
        'listing_partner': listing_partner,
        'product': product,
    }
    return render(request, 'club/edit_product.html', context)


@login_required
def view_redemptions(request):
    """View all redemptions for listing partner"""
    try:
        listing_partner = request.user.listingpartner
    except ListingPartner.DoesNotExist:
        messages.error(request, 'Listing partner account not found')
        return redirect('club:listing_partner_dashboard')

    redemptions = ProductRedemption.objects.filter(
        product__listing_partner=listing_partner
    ).select_related('product', 'profile', 'redeemed_at_shop').order_by('-created_at')

    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        redemptions = redemptions.filter(status=status_filter)

    context = {
        'listing_partner': listing_partner,
        'redemptions': redemptions,
        'status_filter': status_filter,
    }
    return render(request, 'club/listing_partner_redemptions.html', context)


# ============ USER-FACING PRODUCT CATALOG ============

def product_catalog(request):
    """Browse available products for redemption"""
    products = ProductListing.objects.filter(
        status='approved',
        active=True,
        stock_quantity__gt=0
    ).select_related('listing_partner').order_by('-featured', '-created_at')

    # Filter by category if provided
    category = request.GET.get('category')
    if category:
        products = products.filter(category=category)

    # Get all categories
    categories = ProductListing.objects.filter(
        status='approved',
        active=True
    ).values_list('category', flat=True).distinct()

    context = {
        'products': products,
        'categories': categories,
        'selected_category': category,
    }
    return render(request, 'club/product_catalog.html', context)


@login_required
def redeem_product(request, product_id):
    """Redeem a product listing"""
    profile = request.user.profile
    product = get_object_or_404(ProductListing, id=product_id, status='approved', active=True)

    can_redeem, message = product.can_redeem(profile)

    if not can_redeem:
        messages.error(request, message)
        return redirect('club:product_catalog')

    if request.method == 'POST':
        shop_id = request.POST.get('shop_id')
        shop = None

        if shop_id:
            shop = get_object_or_404(Partnership, id=shop_id, partner_type='shop', active=True)

            # Check if product is available at this shop
            if not product.available_at_shops.filter(id=shop.id).exists():
                messages.error(request, 'Product not available at this shop')
                return redirect('club:product_catalog')

        try:
            with transaction.atomic():
                # Calculate earnings
                earnings = product.calculate_earnings()

                # Deduct points from user
                profile.points -= product.points_required
                profile.save(update_fields=['points'])

                # Create redemption
                redemption = ProductRedemption.objects.create(
                    product=product,
                    profile=profile,
                    redeemed_at_shop=shop,
                    points_deducted=product.points_required,
                    amount_charged=earnings['total'],
                    Melvins_commission=earnings['Melvins_commission'],
                    partner_earning=earnings['partner_earning'],
                    status='pending'
                )

                # Update product stock and tracking
                product.stock_quantity -= 1
                product.total_redemptions += 1
                product.save(update_fields=['stock_quantity', 'total_redemptions'])

                # Update listing partner financials
                listing_partner = product.listing_partner
                listing_partner.total_revenue += earnings['total']
                listing_partner.melvins_commission_earned += earnings['Melvins_commission']
                listing_partner.partner_earnings += earnings['partner_earning']
                listing_partner.pending_payout += earnings['partner_earning']
                listing_partner.save(update_fields=[
                    'total_revenue', 'melvins_commission_earned',
                    'partner_earnings', 'pending_payout'
                ])

                if shop:
                    messages.success(
                        request,
                        f'Successfully redeemed {product.name}! '
                        f'Your redemption code is: {redemption.redemption_code}. '
                        f'Show this code at {shop.name} to collect your item.'
                    )
                else:
                    messages.success(
                        request,
                        f'Successfully redeemed {product.name}! '
                        f'Your redemption code is: {redemption.redemption_code}'
                    )

                return redirect('club:user_redemptions')

        except Exception as e:
            messages.error(request, f'Error processing redemption: {str(e)}')
            return redirect('club:product_catalog')

    # Show shops if product is available at shops
    available_shops = product.available_at_shops.filter(active=True)

    context = {
        'product': product,
        'profile': profile,
        'available_shops': available_shops,
        'earnings': product.calculate_earnings(),
    }
    return render(request, 'club/redeem_product.html', context)


@login_required
def challenge_live_draw(request, challenge_id):
    """
    Live draw page - dramatized winner selection
    Only admin/staff can access this to start the draw
    """
    if not request.user.is_staff:
        messages.error(request, 'Only administrators can access the live draw.')
        return redirect('club:challenge_detail', challenge_id=challenge_id)

    challenge = get_object_or_404(Challenge, id=challenge_id)

    # Check if challenge has ended
    if challenge.end_date > timezone.now():
        messages.error(request, 'Challenge has not ended yet.')
        return redirect('club:challenge_detail', challenge_id=challenge_id)

    # Check if winners already selected - redirect to winners page
    existing_winners = ChallengeWinner.objects.filter(challenge=challenge)
    if existing_winners.exists():
        messages.warning(
            request,
            'Winners already selected for this challenge. '
            'Use "Reset Draw Status" action in admin if you need to redo the draw.'
        )
        return redirect('club:challenge_winners', challenge_id=challenge_id)

    # Get eligible entries
    total_entries = challenge.get_eligible_profiles().count()

    if total_entries == 0:
        messages.error(request, 'No eligible participants for this challenge.')
        return redirect('club:challenge_detail', challenge_id=challenge_id)

    if total_entries < challenge.number_of_winners:
        messages.error(
            request,
            f'Not enough participants. Need {challenge.number_of_winners}, '
            f'but only {total_entries} eligible.'
        )
        return redirect('club:challenge_detail', challenge_id=challenge_id)

    # Mark draw as in progress
    challenge.draw_in_progress = True
    challenge.save(update_fields=['draw_in_progress'])

    context = {
        'challenge': challenge,
        'total_entries': total_entries,
        'draw_started': False,
    }

    return render(request, 'club/challenge_live_draw.html', context)


@login_required
@require_http_methods(["POST"])
def challenge_select_winners_ajax(request, challenge_id):
    """
    AJAX endpoint to actually select winners during live draw
    """
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    challenge = get_object_or_404(Challenge, id=challenge_id)

    # Check if winners already exist
    existing_winners = ChallengeWinner.objects.filter(challenge=challenge)

    if existing_winners.exists():
        # Winners already selected, just return them
        winners_data = [winner.to_dict() for winner in existing_winners.order_by('position')]

        # Make sure challenge status is correct
        if challenge.status != 'winners_selected':
            challenge.status = 'winners_selected'
            challenge.winners_selected_at = timezone.now()
            challenge.save(update_fields=['status', 'winners_selected_at'])

        challenge.draw_in_progress = False
        challenge.draw_completed_at = timezone.now()
        challenge.save(update_fields=['draw_in_progress', 'draw_completed_at'])

        return JsonResponse({
            'success': True,
            'winners': winners_data,
            'challenge_id': challenge.id,
            'total_entries': challenge.total_entries,
            'already_selected': True
        })

    # Verify challenge is ready for winner selection
    if challenge.status == 'winners_selected':
        return JsonResponse({
            'success': False,
            'error': 'Winners already selected but not found in database. Please check Challenge Winners in admin.'
        })

    try:
        # Select winners using the existing method
        winners = challenge.select_winners()

        # Mark draw as completed
        challenge.draw_in_progress = False
        challenge.draw_completed_at = timezone.now()
        challenge.save(update_fields=['draw_in_progress', 'draw_completed_at'])

        # Serialize winners for JSON response
        winners_data = [winner.to_dict() for winner in winners]

        return JsonResponse({
            'success': True,
            'winners': winners_data,
            'challenge_id': challenge.id,
            'total_entries': challenge.total_entries,
            'already_selected': False
        })

    except ValueError as e:
        # Reset draw status on error
        challenge.draw_in_progress = False
        challenge.save(update_fields=['draw_in_progress'])

        return JsonResponse({
            'success': False,
            'error': str(e)
        })
    except Exception as e:
        # Reset draw status on error
        challenge.draw_in_progress = False
        challenge.save(update_fields=['draw_in_progress'])

        import traceback
        error_detail = traceback.format_exc()
        print(f"Error selecting winners: {error_detail}")

        return JsonResponse({
            'success': False,
            'error': f'Error selecting winners: {str(e)}'
        })


def challenge_winners(request, challenge_id):
    """
    View winners - with access control based on is_public_results
    """
    challenge = get_object_or_404(Challenge, id=challenge_id)

    # Check if user can view winners
    can_view = challenge.can_view_winners(request.user)

    if not can_view:
        if not challenge.is_public_results:
            messages.error(
                request,
                'Only participants can view winners for this challenge. '
                'You must have entered the challenge to see the results.'
            )
        else:
            messages.error(request, 'Winners have not been selected yet.')
        return redirect('club:challenge_detail', challenge_id=challenge.id)

    winners = challenge.winners.all().select_related('profile').order_by('position')

    # Check if user is a winner
    is_winner = False
    user_winner = None
    if request.user.is_authenticated:
        user_winner = winners.filter(profile=request.user.profile).first()
        is_winner = user_winner is not None

    context = {
        'challenge': challenge,
        'winners': winners,
        'is_winner': is_winner,
        'user_winner': user_winner,
    }

    return render(request, 'club/challenge_winners.html', context)


def public_challenge_live_stream(request, challenge_id):
    """
    Public viewing page for live draw (read-only)
    Shows the draw in progress without control buttons
    """
    challenge = get_object_or_404(Challenge, id=challenge_id, active=True)

    # If winners already selected, redirect to winners page
    if challenge.status == 'winners_selected':
        return redirect('club:challenge_winners', challenge_id=challenge.id)

    # If draw not started yet
    if not challenge.draw_in_progress:
        # Check if it should have started based on end date
        if challenge.end_date > timezone.now():
            messages.info(request, 'This challenge has not ended yet.')
            return redirect('club:challenge_detail', challenge_id=challenge_id)
        else:
            messages.info(request, 'Live draw has not started yet. Check back soon!')
            return redirect('club:challenge_detail', challenge_id=challenge_id)

    # Get any winners already selected (for progressive reveal)
    winners = challenge.winners.all().select_related('profile').order_by('position')

    # Simulate viewer count (you can make this real with websockets/redis)
    viewer_count = ChallengeEntry.objects.filter(challenge=challenge).count() + 10

    context = {
        'challenge': challenge,
        'total_entries': challenge.total_entries or challenge.get_eligible_profiles().count(),
        'is_viewer': True,
        'winners': winners,
        'viewer_count': viewer_count,
        'now': timezone.now(),
    }

    return render(request, 'club/challenge_live_stream_public.html', context)


@login_required
def challenge_status_test(request, challenge_id):
    """
    Diagnostic page to check challenge status
    Helpful for debugging and verifying everything works
    """
    if not request.user.is_staff:
        messages.error(request, 'Only administrators can access the diagnostic page.')
        return redirect('club:challenge_detail', challenge_id=challenge_id)

    challenge = get_object_or_404(Challenge, id=challenge_id)

    # Get winners
    winners = ChallengeWinner.objects.filter(
        challenge=challenge
    ).select_related('profile').order_by('position')

    winners_count = winners.count()

    # Get eligible profiles
    eligible_profiles = challenge.get_eligible_profiles()
    eligible_count = eligible_profiles.count()

    context = {
        'challenge': challenge,
        'winners': winners,
        'winners_count': winners_count,
        'eligible_count': eligible_count,
    }

    return render(request, 'club/challenge_status_test.html', context)


# Update the existing challenge_detail view to show live draw info
def challenge_detail(request, challenge_id):
    """View challenge details and enter if eligible"""
    challenge = get_object_or_404(Challenge, id=challenge_id, active=True)

    # Check if user is authenticated
    is_eligible = False
    already_entered = False
    user_weight = 0
    eligibility_message = ""

    if request.user.is_authenticated:
        profile = request.user.profile

        # Check eligibility
        eligible_profiles = challenge.get_eligible_profiles()
        is_eligible = profile in eligible_profiles

        if is_eligible:
            user_weight = challenge.calculate_entry_weight(profile)

            # Check if already entered
            already_entered = ChallengeEntry.objects.filter(
                challenge=challenge,
                profile=profile
            ).exists()
        else:
            # Determine why not eligible
            reasons = []
            if challenge.min_points_required > 0 and profile.points < challenge.min_points_required:
                reasons.append(f"Need {challenge.min_points_required} points (you have {profile.points})")

            if challenge.min_scans_required > 0:
                scan_count = Scan.objects.filter(profile=profile).count()
                if scan_count < challenge.min_scans_required:
                    reasons.append(f"Need {challenge.min_scans_required} scans (you have {scan_count})")

            if challenge.counties_eligible:
                counties = [c.strip() for c in challenge.counties_eligible.split(',')]
                if profile.county not in counties:
                    reasons.append("Your county is not eligible")

            eligibility_message = " | ".join(reasons) if reasons else "Not eligible"

    # Get winners if already selected (and user can view them)
    winners = []
    can_view_winners = False
    if challenge.status == 'winners_selected':
        can_view_winners = challenge.can_view_winners(request.user)
        if can_view_winners:
            winners = challenge.winners.all().select_related('profile')

    context = {
        'challenge': challenge,
        'is_eligible': is_eligible,
        'already_entered': already_entered,
        'user_weight': user_weight,
        'eligibility_message': eligibility_message,
        'winners': winners,
        'can_view_winners': can_view_winners,
        'profile': request.user.profile if request.user.is_authenticated else None,
    }

    return render(request, 'club/challenge_detail.html', context)


@require_http_methods(["GET"])
def challenge_winners_status(request, challenge_id):
    """
    AJAX endpoint to check if winners have been selected
    Used by public live stream page
    """
    challenge = get_object_or_404(Challenge, id=challenge_id)

    return JsonResponse({
        'challenge_id': challenge.id,
        'winners_selected': challenge.status == 'winners_selected',
        'draw_in_progress': challenge.draw_in_progress,
        'total_entries': challenge.total_entries,
    })




# ============ USER AUTHENTICATION VIEWS (PIN-BASED) ============

def user_login(request):
    """User login - phone entry with partnership/referral code support"""
    partnership = None
    partnership_code = request.GET.get('partner') or request.POST.get('partnership_code', '').strip().upper()
    
    # Capture Referrals & UTMs
    referral_code = request.GET.get('ref', '').strip().upper()
    if not referral_code:
        referral_code = request.session.get('referral_code', '')
        
    utm_source = request.GET.get('utm_source', '').strip()
    if utm_source:
        request.session['utm_data'] = {
            'utm_source': utm_source,
            'utm_medium': request.GET.get('utm_medium', '').strip(),
            'utm_campaign': request.GET.get('utm_campaign', '').strip()
        }

    if partnership_code:
        try:
            partnership = Partnership.objects.get(code=partnership_code, active=True)
        except Partnership.DoesNotExist:
            messages.warning(request, f'Partnership code "{partnership_code}" is invalid.')
            partnership_code = None

    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        if not referral_code:
            referral_code = request.POST.get('referral_code', '').strip().upper()

        if not phone:
            messages.error(request, 'Phone number is required')
        else:
            phone = normalize_phone(phone)

            # Store in session for next step
            request.session['user_phone'] = phone
            if partnership_code:
                request.session['partnership_code'] = partnership_code
            if referral_code:
                request.session['referral_code'] = referral_code

            return redirect('club:user_pin')

    context = {
        'partnership': partnership,
        'partnership_code': partnership_code,
        'referral_code': referral_code,
    }
    return render(request, 'club/user_login.html', context)


def user_pin(request):
    """User PIN entry/setup"""
    phone = request.session.get('user_phone')
    partnership_code = request.session.get('partnership_code')
    referral_code = request.session.get('referral_code')

    if not phone:
        messages.error(request, 'Session expired. Please start again.')
        return redirect('club:user_login')

    phone = normalize_phone(phone)

    # Get partnership if code exists
    partnership = None
    if partnership_code:
        try:
            partnership = Partnership.objects.get(code=partnership_code, active=True)
        except Partnership.DoesNotExist:
            partnership_code = None

    # Check if user exists
    try:
        profile = Profile.objects.get(phone=phone)
        is_new_user = False
        has_pin = profile.has_pin()
    except Profile.DoesNotExist:
        profile = None
        is_new_user = True
        has_pin = False

    if request.method == 'POST':
        pin = request.POST.get('pin', '').strip()

        if not pin or len(pin) != 6 or not pin.isdigit():
            messages.error(request, 'PIN must be exactly 6 digits')
            return render(request, 'club/user_pin.html', {
                'phone': phone,
                'is_new_user': is_new_user,
                'has_pin': has_pin,
                'partnership': partnership,
            })

        if is_new_user:
            # Create new user account
            username = f"user_{phone.replace('+', '').replace('-', '')}"
            user = User.objects.create_user(
                username=username,
                password=get_random_string(10)
            )
            profile = Profile.objects.create(
                user=user,
                phone=phone,
                partnership=partnership,
                profile_completed=False
            )
            
            # Check for UTM data in session and save immediately
            if 'utm_data' in request.session:
                utm_data = request.session['utm_data']
                profile.utm_source = utm_data.get('utm_source')
                profile.utm_medium = utm_data.get('utm_medium')
                profile.utm_campaign = utm_data.get('utm_campaign')
                profile.save(update_fields=['utm_source', 'utm_medium', 'utm_campaign'])

            profile.set_pin(pin)

            login(request, profile.user, backend='django.contrib.auth.backends.ModelBackend')

            # Clean session
            request.session.pop('user_phone', None)
            request.session.pop('partnership_code', None)
            # Keep referral_code for complete_profile

            if partnership:
                messages.success(request, f'Welcome! You\'ve registered via {partnership.name}')
            else:
                messages.success(request, 'Account created! Please complete your profile.')

            return redirect('club:complete_profile')

        else:
            # Existing user
            if not has_pin:
                # Set PIN for existing user (migration scenario)
                profile.set_pin(pin)
                login(request, profile.user, backend='django.contrib.auth.backends.ModelBackend')

                request.session.pop('user_phone', None)
                request.session.pop('partnership_code', None)
                request.session.pop('referral_code', None)

                if profile.profile_completed:
                    messages.success(request, f'PIN set! Welcome back, {profile.first_name}!')
                    return redirect('club:dashboard')
                else:
                    messages.info(request, 'PIN set! Please complete your profile.')
                    return redirect('club:complete_profile')
            else:
                # Verify PIN
                if profile.check_pin(pin):
                    # Update partnership if provided and not already set
                    if partnership and not profile.partnership:
                        profile.partnership = partnership
                        profile.save(update_fields=['partnership'])
                        messages.info(request, f'Your account is now linked to {partnership.name}!')

                    login(request, profile.user, backend='django.contrib.auth.backends.ModelBackend')

                    # Clean session
                    request.session.pop('user_phone', None)
                    request.session.pop('partnership_code', None)
                    request.session.pop('referral_code', None)

                    if profile.profile_completed:
                        messages.success(request, f'Welcome back, {profile.first_name}!')
                        return redirect('club:dashboard')
                    else:
                        messages.info(request, 'Please complete your profile')
                        return redirect('club:complete_profile')
                else:
                    messages.error(request, 'Invalid PIN. Please try again.')

    context = {
        'phone': phone,
        'is_new_user': is_new_user,
        'has_pin': has_pin,
        'partnership': partnership,
    }
    return render(request, 'club/user_pin.html', context)


# ============ PARTNER AUTHENTICATION VIEWS (PIN-BASED) ============

@login_required
def partner_create(request):
    """Create partner account for authenticated user"""
    if hasattr(request.user, 'partnership'):
        return redirect('club:partner_dashboard')

    if request.method == 'POST':
        # Create new partnership
        phone = request.user.profile.phone if hasattr(request.user, 'profile') and request.user.profile.phone else ''
        
        partnership = Partnership.objects.create(
            user=request.user,
            phone=phone, # Might be empty, prompt user later if needed
            profile_completed=False
        )
        messages.success(request, 'Partner account created! Please complete your profile.')
        return redirect('club:partner_complete_profile')

    return render(request, 'club/partner_create.html')

@login_required
def listing_partner_create(request):
    """Create listing partner (vendor) account for authenticated user"""
    if hasattr(request.user, 'listingpartner'):
        return redirect('club:listing_partner_dashboard')

    if request.method == 'POST':
        # Create new listing partner
        phone = request.user.profile.phone if hasattr(request.user, 'profile') and request.user.profile.phone else ''
        
        listing_partner = ListingPartner.objects.create(
            user=request.user,
            phone=phone,
            profile_completed=False
        )
        messages.success(request, 'Vendor account created! Please complete your profile.')
        return redirect('club:listing_partner_complete_profile')

    return render(request, 'club/listing_partner_create.html')

def partner_login(request):
    """Partner login - phone entry"""
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()

        if not phone:
            messages.error(request, 'Phone number is required')
        else:
            phone = normalize_phone(phone)
            request.session['partner_phone'] = phone
            return redirect('club:partner_pin')

    return render(request, 'club/partner_login.html')


def partner_pin(request):
    """Partner PIN entry/setup"""
    phone = request.session.get('partner_phone')

    if not phone:
        messages.error(request, 'Session expired. Please start again.')
        return redirect('club:partner_login')

    phone = normalize_phone(phone)

    # Check if partner exists
    try:
        partnership = Partnership.objects.get(phone=phone)
        is_new_partner = False
        has_pin = partnership.has_pin()
    except Partnership.DoesNotExist:
        partnership = None
        is_new_partner = True
        has_pin = False

    if request.method == 'POST':
        pin = request.POST.get('pin', '').strip()

        if not pin or len(pin) != 6 or not pin.isdigit():
            messages.error(request, 'PIN must be exactly 6 digits')
            return render(request, 'club/partner_pin.html', {
                'phone': phone,
                'is_new_partner': is_new_partner,
                'has_pin': has_pin,
            })

        if is_new_partner:
            # Create new partner account
            username = f"partner_{phone.replace('+', '').replace('-', '')}"
            user = User.objects.create_user(
                username=username,
                password=get_random_string(10)
            )
            partnership = Partnership.objects.create(
                user=user,
                phone=phone,
                profile_completed=False
            )
            partnership.set_pin(pin)

            login(request, partnership.user, backend='django.contrib.auth.backends.ModelBackend')

            request.session.pop('partner_phone', None)

            messages.success(request, 'Partner account created! Please complete your profile.')
            return redirect('club:partner_complete_profile')

        else:
            # Existing partner
            if not has_pin:
                # Set PIN for existing partner
                partnership.set_pin(pin)
                login(request, partnership.user, backend='django.contrib.auth.backends.ModelBackend')

                request.session.pop('partner_phone', None)

                if partnership.profile_completed:
                    messages.success(request, f'PIN set! Welcome back, {partnership.name}!')
                    return redirect('club:partner_dashboard')
                else:
                    messages.info(request, 'PIN set! Please complete your profile.')
                    return redirect('club:partner_complete_profile')
            else:
                # Verify PIN
                if partnership.check_pin(pin):
                    login(request, partnership.user, backend='django.contrib.auth.backends.ModelBackend')

                    request.session.pop('partner_phone', None)

                    if partnership.profile_completed:
                        messages.success(request, f'Welcome back, {partnership.name}!')
                        return redirect('club:partner_dashboard')
                    else:
                        messages.info(request, 'Please complete your profile')
                        return redirect('club:partner_complete_profile')
                else:
                    messages.error(request, 'Invalid PIN. Please try again.')

    context = {
        'phone': phone,
        'is_new_partner': is_new_partner,
        'has_pin': has_pin,
    }
    return render(request, 'club/partner_pin.html', context)


# ============ LISTING PARTNER AUTHENTICATION VIEWS (PIN-BASED) ============

def listing_partner_login(request):
    """Listing partner login - phone entry"""
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()

        if not phone:
            messages.error(request, 'Phone number is required')
        else:
            phone = normalize_phone(phone)
            request.session['listing_partner_phone'] = phone
            return redirect('club:listing_partner_pin')

    return render(request, 'club/listing_partner_login.html')


def listing_partner_pin(request):
    """Listing partner PIN entry/setup"""
    phone = request.session.get('listing_partner_phone')

    if not phone:
        messages.error(request, 'Session expired. Please start again.')
        return redirect('club:listing_partner_login')

    phone = normalize_phone(phone)

    # Check if listing partner exists
    try:
        listing_partner = ListingPartner.objects.get(phone=phone)
        is_new_partner = False
        has_pin = listing_partner.has_pin()
    except ListingPartner.DoesNotExist:
        listing_partner = None
        is_new_partner = True
        has_pin = False

    if request.method == 'POST':
        pin = request.POST.get('pin', '').strip()

        if not pin or len(pin) != 6 or not pin.isdigit():
            messages.error(request, 'PIN must be exactly 6 digits')
            return render(request, 'club/listing_partner_pin.html', {
                'phone': phone,
                'is_new_partner': is_new_partner,
                'has_pin': has_pin,
            })

        if is_new_partner:
            # Create new listing partner account
            username = f"listing_{phone.replace('+', '').replace('-', '')}"
            user = User.objects.create_user(
                username=username,
                password=get_random_string(10)
            )
            listing_partner = ListingPartner.objects.create(
                user=user,
                phone=phone,
                profile_completed=False,
                approved=False
            )
            listing_partner.set_pin(pin)

            login(request, listing_partner.user, backend='django.contrib.auth.backends.ModelBackend')

            request.session.pop('listing_partner_phone', None)

            messages.success(request, 'Listing partner account created! Please complete your profile.')
            return redirect('club:listing_partner_complete_profile')

        else:
            # Existing listing partner
            if not has_pin:
                # Set PIN for existing listing partner
                listing_partner.set_pin(pin)
                login(request, listing_partner.user, backend='django.contrib.auth.backends.ModelBackend')

                request.session.pop('listing_partner_phone', None)

                if listing_partner.profile_completed:
                    messages.success(request, f'PIN set! Welcome back, {listing_partner.company_name}!')
                    return redirect('club:listing_partner_dashboard')
                else:
                    messages.info(request, 'PIN set! Please complete your profile.')
                    return redirect('club:listing_partner_complete_profile')
            else:
                # Verify PIN
                if listing_partner.check_pin(pin):
                    login(request, listing_partner.user, backend='django.contrib.auth.backends.ModelBackend')

                    request.session.pop('listing_partner_phone', None)

                    if listing_partner.profile_completed:
                        messages.success(request, f'Welcome back, {listing_partner.company_name}!')
                        return redirect('club:listing_partner_dashboard')
                    else:
                        messages.info(request, 'Please complete your profile')
                        return redirect('club:listing_partner_complete_profile')
                else:
                    messages.error(request, 'Invalid PIN. Please try again.')

    context = {
        'phone': phone,
        'is_new_partner': is_new_partner,
        'has_pin': has_pin,
    }
    return render(request, 'club/listing_partner_pin.html', context)


# ============ PROFILE COMPLETION VIEWS (Keep existing logic) ============

@login_required
def complete_profile(request):
    """Complete user profile after PIN authentication"""
    profile = request.user.profile

    if profile.profile_completed:
        return redirect('club:dashboard')

    # Get referral code from session (if came from referral link)
    session_referral_code = request.session.get('referral_code', '').strip().upper()

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        second_name = request.POST.get('second_name', '').strip()
        county = request.POST.get('county', '').strip()
        buyer_type = request.POST.get('buyer_type', '').strip()
        referral_code = request.POST.get('referral_code', '').strip().upper()

        # Use session referral code if form field is empty
        if not referral_code and session_referral_code:
            referral_code = session_referral_code

        if not all([first_name, second_name, county, buyer_type]):
            messages.error(request, 'All fields are required')
        else:
            profile.first_name = first_name
            profile.second_name = second_name
            profile.county = county
            profile.buyer_type = buyer_type
            profile.profile_completed = True

            if referral_code and not profile.referred_by:
                try:
                    referrer = Profile.objects.get(referral_code=referral_code)
                    if referrer != profile and referrer.can_refer_more():
                        profile.referred_by = referrer

                        settings = ReferralSettings.get_settings()
                        if settings.referral_enabled:
                            referrer.points += settings.points_for_referrer
                            referrer.referral_points_earned += settings.points_for_referrer
                            referrer.save(update_fields=['points', 'referral_points_earned'])

                            profile.points += settings.points_for_referee

                            Referral.objects.create(
                                referrer=referrer,
                                referred=profile,
                                points_awarded_to_referrer=settings.points_for_referrer,
                                points_awarded_to_referred=settings.points_for_referee
                            )

                            messages.success(
                                request,
                                f'Referral applied! You earned {settings.points_for_referee} points!'
                            )
                except Profile.DoesNotExist:
                    messages.warning(request, 'Invalid referral code')

            profile.save()

            # Process pending invites
            invites_processed = process_pending_invites(profile)
            if invites_processed > 0:
                messages.success(request, f'You received points from {invites_processed} pending invite(s)!')

            # Clear referral code from session
            request.session.pop('referral_code', None)

            # Welcome message
            welcome_msg = f'Welcome, {first_name}! Your profile is complete.'
            if profile.partnership:
                welcome_msg += f' Thanks for joining via {profile.partnership.name}!'

            messages.success(request, welcome_msg)
            return redirect('club:dashboard')

    context = {
        'profile': profile,
        'prefilled_referral_code': session_referral_code,
    }
    return render(request, 'club/complete_profile.html', context)


@login_required
def partner_complete_profile(request):
    """Complete partner profile after PIN authentication"""
    try:
        partnership = request.user.partnership
    except Partnership.DoesNotExist:
        messages.error(request, 'Partner account not found')
        return redirect('club:partner_login')

    if partnership.profile_completed:
        return redirect('club:partner_dashboard')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        partner_type = request.POST.get('partner_type', '').strip()
        contact_person = request.POST.get('contact_person', '').strip()
        email = request.POST.get('email', '').strip()
        county = request.POST.get('county', '').strip()
        location_details = request.POST.get('location_details', '').strip()

        if not all([name, partner_type, contact_person]):
            messages.error(request, 'Name, type, and contact person are required')
        else:
            partnership.name = name
            partnership.partner_type = partner_type
            partnership.contact_person = contact_person
            partnership.email = email
            partnership.county = county
            partnership.location_details = location_details
            partnership.profile_completed = True
            partnership.save()

            type_display = partnership.get_partner_type_display()
            messages.success(request, f'Welcome, {name}! Your {type_display} profile is complete.')
            return redirect('club:partner_dashboard')

    context = {
        'partnership': partnership,
        'county_choices': Profile.COUNTY_CHOICES,
    }
    return render(request, 'club/partner_complete_profile.html', context)


@login_required
def listing_partner_complete_profile(request):
    """Complete listing partner profile"""
    try:
        listing_partner = request.user.listingpartner
    except ListingPartner.DoesNotExist:
        messages.error(request, 'Listing partner account not found')
        return redirect('club:listing_partner_login')

    if listing_partner.profile_completed:
        return redirect('club:listing_partner_dashboard')

    if request.method == 'POST':
        company_name = request.POST.get('company_name', '').strip()
        contact_person = request.POST.get('contact_person', '').strip()
        email = request.POST.get('email', '').strip()
        business_registration = request.POST.get('business_registration', '').strip()
        tax_pin = request.POST.get('tax_pin', '').strip()
        bank_name = request.POST.get('bank_name', '').strip()
        bank_account_number = request.POST.get('bank_account_number', '').strip()
        bank_account_name = request.POST.get('bank_account_name', '').strip()
        mpesa_number = request.POST.get('mpesa_number', '').strip()

        if not all([company_name, contact_person, email]):
            messages.error(request, 'Company name, contact person, and email are required')
        else:
            listing_partner.company_name = company_name
            listing_partner.contact_person = contact_person
            listing_partner.email = email
            listing_partner.business_registration = business_registration
            listing_partner.tax_pin = tax_pin
            listing_partner.bank_name = bank_name
            listing_partner.bank_account_number = bank_account_number
            listing_partner.bank_account_name = bank_account_name
            listing_partner.mpesa_number = mpesa_number
            listing_partner.profile_completed = True
            listing_partner.save()

            messages.success(
                request,
                f'Profile completed! Your account is pending approval by Melvins admin. '
                f'You will be notified once approved.'
            )
            return redirect('club:listing_partner_dashboard')

    context = {
        'listing_partner': listing_partner,
    }
    return render(request, 'club/listing_partner_complete_profile.html', context)

@login_required
def user_logout(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('club:user_login')


def landing_page(request):
    """Public landing page - main entry point"""
    # Capture Referrals & UTMs
    referral_code = request.GET.get('ref', '').strip().upper()
    utm_source = request.GET.get('utm_source', '').strip()
    utm_medium = request.GET.get('utm_medium', '').strip()
    utm_campaign = request.GET.get('utm_campaign', '').strip()

    if referral_code:
        request.session['referral_code'] = referral_code
        
    if utm_source:
        request.session['utm_data'] = {
            'utm_source': utm_source,
            'utm_medium': utm_medium,
            'utm_campaign': utm_campaign
        }

    if request.user.is_authenticated:
        if hasattr(request.user, 'profile'):
            return redirect('club:dashboard')
        elif hasattr(request.user, 'partnership'):
            return redirect('club:partner_dashboard')
        elif hasattr(request.user, 'listingpartner'):
            return redirect('club:listing_partner_dashboard')
    return render(request, 'club/landing_page.html')


@login_required
def listing_partner_redemptions(request):
    """View all redemptions for listing partner"""
    try:
        listing_partner = request.user.listingpartner
    except ListingPartner.DoesNotExist:
        messages.error(request, 'Listing partner account not found')
        return redirect('club:listing_partner_login')

    if not listing_partner.profile_completed:
        return redirect('club:listing_partner_complete_profile')

    # Get all redemptions for this partner's products
    redemptions = ProductRedemption.objects.filter(
        product__listing_partner=listing_partner
    ).select_related('product', 'profile', 'redeemed_at_shop').order_by('-created_at')

    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        redemptions = redemptions.filter(status=status_filter)

    context = {
        'listing_partner': listing_partner,
        'redemptions': redemptions,
        'status_filter': status_filter,
    }
    return render(request, 'club/listing_partner_redemptions.html', context)


# ============ TEA ESTATES COLLECTION VIEWS ============

@login_required
def my_collection(request):
    """View user's Tea Estates card collection"""
    from .models import (
        EstateCollection, EstateCard, UserCardCollection, CollectionCompletion
    )
    
    profile = request.user.profile
    
    # Get active collection (prioritize currently running ones)
    from django.utils import timezone
    active_collection = EstateCollection.objects.filter(
        is_active=True,
        start_date__lte=timezone.now(),
        end_date__gte=timezone.now()
    ).first()
    
    # Fallback to any active collection if no date-match
    if not active_collection:
        active_collection = EstateCollection.objects.filter(is_active=True).first()
    
    if not active_collection:
        context = {
            'profile': profile,
            'collection': None,
            'user_cards': [],
            'progress': 0,
        }
        return render(request, 'club/my_collection.html', context)
    
    # Get all cards in the collection
    all_cards = EstateCard.objects.filter(
        collection=active_collection,
        active=True
    ).select_related('estate').order_by('card_number')
    
    # Get user's collected cards (unique, not duplicates)
    user_collected_ids = UserCardCollection.objects.filter(
        profile=profile,
        card__collection=active_collection,
        is_duplicate=False
    ).values_list('card_id', flat=True).distinct()
    
    user_collected_set = set(user_collected_ids)
    
    # Calculate progress
    collected_count = len(user_collected_set)
    total_count = all_cards.count()
    progress_percent = (collected_count / total_count * 100) if total_count > 0 else 0
    
    # Mark new cards as viewed
    UserCardCollection.objects.filter(
        profile=profile,
        card__collection=active_collection,
        is_new=True
    ).update(is_new=False)
    
    # Check for completed collection
    completion = CollectionCompletion.objects.filter(
        profile=profile,
        collection=active_collection
    ).first()
    
    # Get recent cards (with duplicates for display)
    recent_cards = UserCardCollection.objects.filter(
        profile=profile,
        card__collection=active_collection
    ).select_related('card', 'card__estate').order_by('-obtained_at')[:12]
    
    # Build card grid with collected status
    cards_with_status = []
    for card in all_cards:
        cards_with_status.append({
            'card': card,
            'collected': card.id in user_collected_set
        })
    
    context = {
        'profile': profile,
        'collection': active_collection,
        'cards_with_status': cards_with_status,
        'collected_count': collected_count,
        'total_count': total_count,
        'progress_percent': progress_percent,
        'completion': completion,
        'recent_cards': recent_cards,
    }
    
    return render(request, 'club/my_collection.html', context)


@login_required
def card_detail(request, card_id):
    """View details of a specific estate card"""
    from .models import EstateCard, UserCardCollection
    
    profile = request.user.profile
    card = get_object_or_404(EstateCard, id=card_id, active=True)
    
    # Check if user has this card
    user_card = UserCardCollection.objects.filter(
        profile=profile,
        card=card,
        is_duplicate=False
    ).first()
    
    # Count duplicates
    duplicate_count = UserCardCollection.objects.filter(
        profile=profile,
        card=card,
        is_duplicate=True
    ).count()
    
    context = {
        'card': card,
        'estate': card.estate,
        'user_card': user_card,
        'has_card': user_card is not None,
        'duplicate_count': duplicate_count,
    }
    
    return render(request, 'club/card_detail.html', context)


@login_required
def card_reveal(request, scan_id):
    """Show card reveal animation after scan"""
    from .models import Scan, UserCardCollection
    
    profile = request.user.profile
    scan = get_object_or_404(Scan, id=scan_id, profile=profile)
    
    # Get the card that was revealed from this scan
    revealed_card = UserCardCollection.objects.filter(
        from_scan=scan,
        profile=profile
    ).select_related('card', 'card__estate', 'card__collection').first()
    
    if not revealed_card:
        messages.info(request, 'No card was revealed with this scan.')
        return redirect('club:my_collection')
    
    context = {
        'revealed_card': revealed_card,
        'card': revealed_card.card,
        'estate': revealed_card.card.estate,
        'is_duplicate': revealed_card.is_duplicate,
        'scan': scan,
    }
    
    return render(request, 'club/card_reveal.html', context)


@login_required
def claim_collection_reward(request, collection_id):
    """Claim reward for completing a collection"""
    from .models import EstateCollection, CollectionCompletion
    
    profile = request.user.profile
    collection = get_object_or_404(EstateCollection, id=collection_id)
    
    # Check if user has completed this collection
    completion = CollectionCompletion.objects.filter(
        profile=profile,
        collection=collection
    ).first()
    
    if not completion:
        messages.error(request, 'You have not completed this collection yet.')
        return redirect('club:my_collection')
    
    if completion.reward_claimed:
        messages.info(request, 'You have already claimed this reward.')
        return redirect('club:my_collection')
    
    # Claim the reward
    success, message = completion.claim_reward()
    
    if success:
        messages.success(request, f'🎉 {message}')
    else:
        messages.error(request, message)
    
    return redirect('club:my_collection')


@login_required
def rewards(request):
    """View available rewards for redemption"""
    from .models import Reward
    
    profile = request.user.profile
    
    # Get all active rewards
    all_rewards = Reward.objects.filter(active=True).order_by('cost_points')
    
    # Split into affordable and coming soon
    affordable_rewards = []
    coming_soon_rewards = []
    
    for reward in all_rewards:
        if profile.points >= reward.cost_points:
            affordable_rewards.append(reward)
        else:
            coming_soon_rewards.append(reward)
    
    context = {
        'profile': profile,
        'affordable_rewards': affordable_rewards,
        'coming_soon_rewards': coming_soon_rewards,
        'all_rewards': all_rewards,
    }
    
    return render(request, 'club/rewards.html', context)


@login_required
def create_card_gift(request, card_id):
    """Generate a shareable link to gift a card"""
    from .models import EstateCard, UserCardCollection, CardGift
    from django.urls import reverse
    
    profile = request.user.profile
    card = get_object_or_404(EstateCard, id=card_id)
    
    # Verify ownership
    if not UserCardCollection.objects.filter(profile=profile, card=card).exists():
        return JsonResponse({'success': False, 'message': "You don't own this card!"}, status=403)
        
    try:
        # Create gift
        gift = CardGift.objects.create(
            sender=profile,
            card=card
        )
        
        # Build URL
        claim_url = request.build_absolute_uri(
            reverse('club:claim_card_gift', args=[gift.token])
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Gift link created!',
            'share_url': claim_url
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


def claim_card_gift(request, token):
    """Handle claiming of a gifted card"""
    from .models import CardGift
    from django.urls import reverse
    
    gift = get_object_or_404(CardGift, token=token)
    
    if not request.user.is_authenticated:
        return redirect(f"{reverse('club:user_login')}?next={request.path}")
        
    try:
        success, message = gift.claim(request.user.profile)
        if success:
            messages.success(request, f"You've accepted the gift: {gift.card.get_display_title()}!")
            return redirect('club:my_collection')
        else:
            messages.error(request, message)
            return redirect('club:dashboard')
    except Exception as e:
        messages.error(request, f"Error claiming gift: {str(e)}")
        return redirect('club:dashboard')


# ============ TEAM COLLECTION VIEWS (Group Mode) ============

@login_required
def team_collection_home(request):
    """Team collection hub - view your teams and option to create/join"""
    from .models import (
        EstateCollection, CollectionTeam, TeamMember
    )
    from django.utils import timezone
    
    profile = request.user.profile
    
    # Get active collection
    active_collection = EstateCollection.objects.filter(
        is_active=True,
        start_date__lte=timezone.now(),
        end_date__gte=timezone.now()
    ).first()
    
    if not active_collection:
        active_collection = EstateCollection.objects.filter(is_active=True).first()
    
    # Get user's team memberships for this collection
    team_memberships = []
    led_teams = []
    
    if active_collection:
        team_memberships = TeamMember.objects.filter(
            profile=profile,
            team__collection=active_collection
        ).select_related('team', 'team__captain')
        
        led_teams = CollectionTeam.objects.filter(
            captain=profile,
            collection=active_collection
        )
    
    # Leaderboard - Top 10 fastest teams
    top_teams = []
    if active_collection:
        top_teams = CollectionTeam.objects.filter(
            collection=active_collection,
            completed_at__isnull=False
        ).order_by('completed_at')[:10]
    
    context = {
        'profile': profile,
        'collection': active_collection,
        'team_memberships': team_memberships,
        'led_teams': led_teams,
        'top_teams': top_teams,
    }
    
    return render(request, 'club/team_collection_home.html', context)


@login_required
def create_team(request):
    """Create a new team for the active collection"""
    from .models import (
        EstateCollection, CollectionTeam, TeamMember
    )
    from django.utils import timezone
    
    profile = request.user.profile
    
    # Get active collection
    active_collection = EstateCollection.objects.filter(
        is_active=True,
        start_date__lte=timezone.now(),
        end_date__gte=timezone.now()
    ).first()
    
    if not active_collection:
        messages.error(request, 'No active collection campaign right now.')
        return redirect('club:team_collection_home')
    
    # Check if user already has a team for this collection
    existing_membership = TeamMember.objects.filter(
        profile=profile,
        team__collection=active_collection
    ).first()
    
    if existing_membership:
        messages.info(request, f'You are already in team "{existing_membership.team.name}"')
        return redirect('club:team_dashboard', team_id=existing_membership.team.id)
    
    if request.method == 'POST':
        team_name = request.POST.get('team_name', '').strip()
        
        if not team_name:
            messages.error(request, 'Team name is required')
        elif len(team_name) > 100:
            messages.error(request, 'Team name too long (max 100 characters)')
        else:
            # Create team
            team = CollectionTeam.objects.create(
                name=team_name,
                collection=active_collection,
                captain=profile
            )
            
            # Add captain as first member
            TeamMember.objects.create(
                team=team,
                profile=profile
            )
            
            messages.success(request, f'Team "{team_name}" created! Share code: {team.invite_code}')
            return redirect('club:team_dashboard', team_id=team.id)
    
    context = {
        'profile': profile,
        'collection': active_collection,
    }
    
    return render(request, 'club/create_team.html', context)


@login_required
def join_team(request):
    """Join a team using invite code"""
    from .models import (
        CollectionTeam, TeamMember
    )
    
    profile = request.user.profile
    
    if request.method == 'POST':
        invite_code = request.POST.get('invite_code', '').strip().upper()
        
        if not invite_code:
            messages.error(request, 'Invite code is required')
        else:
            try:
                team = CollectionTeam.objects.get(invite_code=invite_code)
                
                # Check if already a member
                if TeamMember.objects.filter(team=team, profile=profile).exists():
                    messages.info(request, 'You are already a member of this team!')
                    return redirect('club:team_dashboard', team_id=team.id)
                
                # Check if user is in another team for same collection
                existing = TeamMember.objects.filter(
                    profile=profile,
                    team__collection=team.collection
                ).first()
                if existing:
                    messages.error(request, f'You are already in team "{existing.team.name}" for this campaign.')
                    return redirect('club:team_dashboard', team_id=existing.team.id)
                
                # Check if team can accept more members
                if not team.can_join():
                    messages.error(request, 'This team is full or no longer active.')
                else:
                    # Join the team
                    TeamMember.objects.create(
                        team=team,
                        profile=profile
                    )
                    messages.success(request, f'You joined team "{team.name}"!')
                    return redirect('club:team_dashboard', team_id=team.id)
                    
            except CollectionTeam.DoesNotExist:
                messages.error(request, 'Invalid invite code')
    
    context = {
        'profile': profile,
    }
    
    return render(request, 'club/join_team.html', context)


@login_required
def team_dashboard(request, team_id):
    """View team progress and members"""
    from .models import (
        CollectionTeam, TeamMember, TeamCardCollection, EstateCard
    )
    
    profile = request.user.profile
    team = get_object_or_404(CollectionTeam, id=team_id)
    
    # Check if user is a member
    try:
        membership = TeamMember.objects.get(team=team, profile=profile)
    except TeamMember.DoesNotExist:
        messages.error(request, 'You are not a member of this team')
        return redirect('club:team_collection_home')
    
    # Get all members with contribution stats
    members = TeamMember.objects.filter(team=team).select_related('profile').order_by('-cards_contributed')
    
    # Get all cards in collection
    all_cards = EstateCard.objects.filter(
        collection=team.collection,
        active=True
    ).select_related('estate').order_by('card_number')
    
    # Get team's collected cards
    team_collected_ids = TeamCardCollection.objects.filter(
        team=team
    ).values_list('card_id', flat=True)
    team_collected_set = set(team_collected_ids)
    
    # Build card grid with status
    cards_with_status = []
    for card in all_cards:
        cards_with_status.append({
            'card': card,
            'collected': card.id in team_collected_set
        })
    
    # Recent contributions
    recent_contributions = TeamCardCollection.objects.filter(
        team=team
    ).select_related('card', 'card__estate', 'contributed_by').order_by('-contributed_at')[:10]
    
    context = {
        'profile': profile,
        'team': team,
        'membership': membership,
        'members': members,
        'cards_with_status': cards_with_status,
        'collected_count': len(team_collected_set),
        'total_count': all_cards.count(),
        'progress_percent': team.progress_percentage(),
        'recent_contributions': recent_contributions,
        'is_captain': profile == team.captain,
    }
    
    return render(request, 'club/team_dashboard.html', context)


@login_required
def contribute_to_team(request, team_id, card_id):
    """Contribute a card from personal collection to team"""
    from .models import (
        CollectionTeam, EstateCard, UserCardCollection, contribute_card_to_team
    )
    
    profile = request.user.profile
    team = get_object_or_404(CollectionTeam, id=team_id)
    card = get_object_or_404(EstateCard, id=card_id)
    
    # Check ownership - user must have this card
    user_has_card = UserCardCollection.objects.filter(
        profile=profile,
        card=card
    ).exists()
    
    if not user_has_card:
        messages.error(request, "You don't have this card in your collection")
        return redirect('club:team_dashboard', team_id=team_id)
    
    # Contribute to team
    success, message, team_card = contribute_card_to_team(profile, card, team)
    
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    
    return redirect('club:team_dashboard', team_id=team_id)


# ============ MANAGEMENT DASHBOARD ============

@login_required
def management_dashboard(request):
    """
    Enhanced Datafa.st style management dashboard
    High density, actionable metrics for staff/admins
    """
    if not request.user.is_staff:
        messages.error(request, "Access denied. Staff only.")
        return redirect('club:dashboard')
    
    # Time ranges
    now = timezone.now()
    t24h = now - timedelta(days=1)
    prev_t24h = now - timedelta(days=2)
    
    # 1. KPI Pulse & Trends
    total_users = Profile.objects.count()
    users_24h = Profile.objects.filter(created_at__gte=t24h).count()
    prev_users_24h = Profile.objects.filter(created_at__range=(prev_t24h, t24h)).count()
    
    total_scans = Scan.objects.count()
    scans_24h = Scan.objects.filter(scanned_at__gte=t24h).count()
    prev_scans_24h = Scan.objects.filter(scanned_at__range=(prev_t24h, t24h)).count()
    
    total_redemptions = ProductRedemption.objects.count()
    redemptions_24h = ProductRedemption.objects.filter(created_at__gte=t24h).count()
    prev_redemptions_24h = ProductRedemption.objects.filter(created_at__range=(prev_t24h, t24h)).count()
    
    # Helper for trend
    def get_trend(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)

    trends = {
        'users': get_trend(users_24h, prev_users_24h),
        'scans': get_trend(scans_24h, prev_scans_24h),
        'redemptions': get_trend(redemptions_24h, prev_redemptions_24h),
    }

    # Revenue (Commission)
    total_revenue = ListingPartner.objects.aggregate(total=Sum('melvins_commission_earned'))['total'] or 0
    
    # 2. User List (Enriched with Search & Filters)
    from django.core.paginator import Paginator
    
    # Base queryset with annotations for performance
    users_qs = Profile.objects.select_related('user').annotate(
        scan_count=Count('scan', distinct=True),
        redemption_count=Count('product_redemptions', distinct=True)
    ).order_by('-created_at')

    # Filtering
    search_query = request.GET.get('q', '').strip()
    county_filter = request.GET.get('county', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if search_query:
        users_qs = users_qs.filter(
            Q(first_name__icontains=search_query) | 
            Q(second_name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    if county_filter:
        users_qs = users_qs.filter(county=county_filter)

    if status_filter == 'active':
        users_qs = users_qs.filter(user__is_active=True)
    elif status_filter == 'inactive':
        users_qs = users_qs.filter(user__is_active=False)

    # Pagination
    paginator = Paginator(users_qs, 50)
    page_number = request.GET.get('page')
    recent_users = paginator.get_page(page_number)
    
    # 3. Geographic Breakdown
    county_data = Profile.objects.values('county').annotate(
        user_count=Count('id')
    ).order_by('-user_count')
    
    if total_users > 0:
        for c in county_data:
            c['user_percent'] = (c['user_count'] / total_users) * 100
            
    # Distinct counties for filter dropdown
    all_counties = [c['county'] for c in county_data if c['county']]
    
    # 4. Channel Tracking
    total_referred = Profile.objects.filter(referred_by__isnull=False).count()
    organic_users = total_users - total_referred
    
    traffic_sources = Profile.objects.values('utm_source').annotate(
        count=Count('id')
    ).order_by('-count')
    
    top_shops = Partnership.objects.filter(partner_type='shop').annotate(
        redemption_count=Count('productredemption')
    ).order_by('-redemption_count')[:10]
    
    # 5. Activity Feed
    recent_scans = Scan.objects.select_related('profile', 'pack').order_by('-scanned_at')[:20]
    recent_redemptions = ProductRedemption.objects.select_related('profile', 'product').order_by('-created_at')[:20]
    
    activity_feed = []
    for s in recent_scans:
        activity_feed.append({
            'type': 'scan',
            'user': s.profile,
            'desc': f"Scanned Pack",
            'value': f"+{s.points_awarded} pts",
            'time': s.scanned_at,
            'icon': '📷'
        })
        
    for r in recent_redemptions:
        activity_feed.append({
            'type': 'redeem',
            'user': r.profile,
            'desc': f"Redeemed {r.product.name}",
            'value': f"-{r.points_deducted} pts",
            'time': r.created_at,
            'icon': '🎁'
        })
    activity_feed.sort(key=lambda x: x['time'], reverse=True)
    activity_feed = activity_feed[:30]
    
    # 6. Chart Logic
    from django.db.models.functions import TruncDate
    start_date = now - timedelta(days=30)
    
    daily_scans = Scan.objects.filter(scanned_at__gte=start_date)\
        .annotate(date=TruncDate('scanned_at'))\
        .values('date')\
        .annotate(count=Count('id'))\
        .order_by('date')
        
    daily_redemptions = ProductRedemption.objects.filter(created_at__gte=start_date)\
        .annotate(date=TruncDate('created_at'))\
        .values('date')\
        .annotate(count=Count('id'))\
        .order_by('date')
        
    scan_dict = {item['date']: item['count'] for item in daily_scans}
    redemption_dict = {item['date']: item['count'] for item in daily_redemptions}
    
    chart_labels = []
    scan_data = []
    redemption_data = []
    
    for i in range(30):
        d = (now - timedelta(days=29-i)).date()
        chart_labels.append(d.strftime('%d %b'))
        scan_data.append(scan_dict.get(d, 0))
        redemption_data.append(redemption_dict.get(d, 0))
    
    context = {
        'total_users': total_users,
        'users_24h': users_24h,
        'trends': trends,
        'total_scans': total_scans,
        'scans_24h': scans_24h,
        'total_redemptions': total_redemptions,
        'redemptions_24h': redemptions_24h,
        'total_revenue': total_revenue,
        'county_data': county_data,
        'organic_users': organic_users,
        'total_referred': total_referred,
        'traffic_sources': traffic_sources,
        'top_shops': top_shops,
        'recent_users': recent_users,
        'activity_feed': activity_feed,
        'chart_labels': chart_labels,
        'scan_data': scan_data,
        'redemption_data': redemption_data,
        'all_counties': all_counties, # For dropdown
        'search_query': search_query,
        'county_filter': county_filter,
        'status_filter': status_filter,
    }
    
    return render(request, 'club/management_dashboard.html', context)
