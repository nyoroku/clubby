# admin.py - Complete admin configuration

from django.contrib import admin
from django.db.models import Sum, Count
from django.urls import path
from django.shortcuts import render
from django.utils.html import format_html
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
import csv


from .models import (
    Profile, Partnership, PartnershipEarning,
    PackCode, Scan, Reward, Redemption,
    ReferralSettings, Referral, OTP, PendingInvite, PointTransferSettings, PointTransfer,
    ListingPartner, PartnerPayout, ProductListing, ProductRedemption, Challenge, ChallengeWinner, ChallengeEntry,
    TeaEstate, EstateCollection, EstateCard, UserCardCollection, CollectionCompletion
)


# ============================================
# PARTNERSHIP ADMIN
# ============================================

@admin.register(Partnership)
class PartnershipAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'points_per_scan', 'total_points_earned',
        'referred_count', 'total_scans_count', 'active_badge', 'created_at'
    ]
    list_filter = ['active', 'created_at']
    search_fields = ['name', 'code', 'email', 'phone', 'contact_person']
    readonly_fields = [
        'code', 'total_points_earned', 'created_at', 'updated_at',
        'registration_link', 'dashboard_link', 'stats_display'
    ]

    fieldsets = (
        ('Partnership Information', {
            'fields': ('name', 'code', 'contact_person', 'email', 'phone')
        }),
        ('Quick Links', {
            'fields': ('registration_link', 'dashboard_link'),
        }),
        ('Points Configuration', {
            'fields': ('points_per_scan', 'total_points_earned')
        }),
        ('Payout Tracking', {
            'fields': ('pending_payout', 'total_payout'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('stats_display',),
        }),
        ('Status & Dates', {
            'fields': ('active', 'created_at', 'updated_at')
        }),
    )

    actions = ['export_to_csv', 'activate_partnerships', 'deactivate_partnerships']

    def get_urls(self):
        """Add custom URL for partnership reports"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:partnership_id>/report/',
                self.admin_site.admin_view(self.partnership_report_view),
                name='club_partnership_report'
            ),
        ]
        return custom_urls + urls

    def partnership_report_view(self, request, partnership_id):
        """Detailed partnership report view"""
        partnership = Partnership.objects.get(id=partnership_id)

        # Get date range from request
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)

        # Get earnings in date range
        earnings = PartnershipEarning.objects.filter(
            partnership=partnership,
            created_at__gte=start_date
        ).select_related('profile', 'scan', 'scan__pack')

        # Aggregate stats
        stats = earnings.aggregate(
            total_points=Sum('points_earned'),
            total_scans=Count('id'),
            unique_users=Count('profile', distinct=True)
        )

        # Top users
        top_users = earnings.values(
            'profile__phone', 'profile__first_name', 'profile__second_name'
        ).annotate(
            total_points=Sum('points_earned'),
            scan_count=Count('id')
        ).order_by('-total_points')[:10]

        # Daily breakdown
        from django.db.models.functions import TruncDate
        daily_stats = earnings.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            points=Sum('points_earned'),
            scans=Count('id')
        ).order_by('date')

        context = {
            **self.admin_site.each_context(request),
            'partnership': partnership,
            'days': days,
            'stats': stats,
            'top_users': top_users,
            'daily_stats': daily_stats,
            'recent_earnings': earnings.order_by('-created_at')[:50],
            'opts': self.model._meta,
        }

        return render(request, 'admin/partnership_report.html', context)

    def referred_count(self, obj):
        count = obj.referred_users_count()
        return format_html(
            '<strong style="color: #10b981; font-size: 1.1em;">{}</strong>',
            count
        )

    referred_count.short_description = 'Users'

    def total_scans_count(self, obj):
        count = obj.total_scans_by_referrals()
        return format_html(
            '<strong style="color: #6366f1; font-size: 1.1em;">{}</strong>',
            count
        )

    total_scans_count.short_description = 'Scans'

    def active_badge(self, obj):
        if obj.active:
            return format_html(
                '<span style="background: #10b981; color: white; padding: 4px 12px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">✓ ACTIVE</span>'
            )
        return format_html(
            '<span style="background: #ef4444; color: white; padding: 4px 12px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">✕ INACTIVE</span>'
        )

    active_badge.short_description = 'Status'

    def registration_link(self, obj):
        if obj.code:
            url = f'/request-otp/?partner={obj.code}'
            full_url = f'https://yoursite.com{url}'  # Update with your domain
            return format_html(
                '<div style="background: #f3f4f6; padding: 12px; border-radius: 8px;">'
                '<strong style="color: #1f2937;">Registration URL:</strong><br>'
                '<code style="background: white; padding: 8px; display: block; margin: 8px 0; '
                'border-radius: 4px; font-size: 12px;">{}</code>'
                '<button onclick="navigator.clipboard.writeText(\'{}\'); '
                'alert(\'Copied to clipboard!\');" '
                'style="background: #6366f1; color: white; border: none; padding: 6px 12px; '
                'border-radius: 4px; cursor: pointer; font-size: 12px;">'
                '<i class="fas fa-copy"></i> Copy Link</button>'
                '</div>',
                full_url, full_url
            )
        return '-'

    registration_link.short_description = 'Share Link'

    def dashboard_link(self, obj):
        if obj.code:
            url = f'/partnership/dashboard/?code={obj.code}'
            return format_html(
                '<a href="{}" target="_blank" '
                'style="background: #10b981; color: white; padding: 8px 16px; '
                'border-radius: 6px; text-decoration: none; display: inline-block; '
                'font-weight: bold; font-size: 13px;">'
                '<i class="fas fa-chart-line"></i> View Dashboard</a>',
                url
            )
        return '-'

    dashboard_link.short_description = 'Dashboard'

    def stats_display(self, obj):
        # Get last 30 days stats
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent = PartnershipEarning.objects.filter(
            partnership=obj,
            created_at__gte=thirty_days_ago
        ).aggregate(
            total_points=Sum('points_earned'),
            total_scans=Count('id'),
            unique_users=Count('profile', distinct=True)
        )

        html = f'''
        <div style="background: #f9fafb; padding: 20px; border-radius: 12px; border: 2px solid #e5e7eb;">
            <h3 style="margin-top: 0; color: #1f2937; font-size: 16px; margin-bottom: 16px;">
                📊 Last 30 Days Performance
            </h3>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
                <div style="background: white; padding: 12px; border-radius: 8px; text-align: center;">
                    <div style="color: #10b981; font-size: 24px; font-weight: bold;">
                        {recent['total_points'] or 0}
                    </div>
                    <div style="color: #6b7280; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">
                        Points Earned
                    </div>
                </div>
                <div style="background: white; padding: 12px; border-radius: 8px; text-align: center;">
                    <div style="color: #6366f1; font-size: 24px; font-weight: bold;">
                        {recent['total_scans'] or 0}
                    </div>
                    <div style="color: #6b7280; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">
                        Total Scans
                    </div>
                </div>
                <div style="background: white; padding: 12px; border-radius: 8px; text-align: center;">
                    <div style="color: #f59e0b; font-size: 24px; font-weight: bold;">
                        {recent['unique_users'] or 0}
                    </div>
                    <div style="color: #6b7280; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">
                        Active Users
                    </div>
                </div>
                <div style="background: white; padding: 12px; border-radius: 8px; text-align: center;">
                    <div style="color: #ec4899; font-size: 24px; font-weight: bold;">
                        {obj.points_per_scan}
                    </div>
                    <div style="color: #6b7280; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">
                        Points/Scan
                    </div>
                </div>
            </div>
            <div style="margin-top: 16px; text-align: center;">
                <strong>Total All-Time:</strong> {obj.total_points_earned} points from {obj.referred_users_count()} users
            </div>
            <div style="margin-top: 12px; text-align: center;">
                <a href="/admin/club/partnership/{obj.id}/report/" 
                   style="background: #6366f1; color: white; padding: 8px 16px; 
                          border-radius: 6px; text-decoration: none; display: inline-block; 
                          font-weight: bold; font-size: 13px;">
                    📊 View Detailed Report
                </a>
            </div>
        </div>
        '''
        return format_html(html)

    stats_display.short_description = 'Performance Statistics'

    def export_to_csv(self, request, queryset):
        """Export partnerships to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="partnerships.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Name', 'Code', 'Contact', 'Email', 'Phone',
            'Points Per Scan', 'Total Points', 'Users', 'Scans',
            'Active', 'Created'
        ])

        for p in queryset:
            writer.writerow([
                p.name, p.code, p.contact_person, p.email, p.phone,
                p.points_per_scan, p.total_points_earned,
                p.referred_users_count(), p.total_scans_by_referrals(),
                'Yes' if p.active else 'No',
                p.created_at.strftime('%Y-%m-%d %H:%M')
            ])

        return response

    export_to_csv.short_description = 'Export selected to CSV'

    def activate_partnerships(self, request, queryset):
        count = queryset.update(active=True)
        self.message_user(request, f'{count} partnership(s) activated.')

    activate_partnerships.short_description = 'Activate selected'

    def deactivate_partnerships(self, request, queryset):
        count = queryset.update(active=False)
        self.message_user(request, f'{count} partnership(s) deactivated.')

    deactivate_partnerships.short_description = 'Deactivate selected'


# ============================================
# PARTNERSHIP EARNING ADMIN
# ============================================

@admin.register(PartnershipEarning)
class PartnershipEarningAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'partnership_name', 'user_info', 'product',
        'points_earned', 'created_at'
    ]
    list_filter = ['partnership', 'created_at']
    search_fields = [
        'partnership__name', 'profile__phone',
        'profile__first_name', 'profile__second_name'
    ]
    readonly_fields = ['partnership', 'profile', 'scan', 'points_earned', 'created_at']
    date_hierarchy = 'created_at'

    def partnership_name(self, obj):
        return format_html(
            '<strong style="color: #6366f1;">{}</strong><br>'
            '<small style="color: #94a3b8;">{}</small>',
            obj.partnership.name,
            obj.partnership.code
        )

    partnership_name.short_description = 'Partnership'

    def user_info(self, obj):
        return format_html(
            '{} {}<br><small style="color: #64748b;">{}</small>',
            obj.profile.first_name or '',
            obj.profile.second_name or '',
            obj.profile.phone
        )

    user_info.short_description = 'User'

    def product(self, obj):
        return obj.scan.pack.sku

    product.short_description = 'Product'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ============================================
# PROFILE ADMIN (Enhanced)
# ============================================

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = [
        'phone', 'full_name', 'points', 'partnership_badge',
        'referral_code', 'profile_completed', 'created_at'
    ]
    list_filter = ['profile_completed', 'buyer_type', 'county', 'created_at', 'partnership']
    search_fields = ['phone', 'first_name', 'second_name', 'referral_code']
    readonly_fields = ['referral_code', 'created_at', 'user_stats']

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'phone', 'first_name', 'second_name')
        }),
        ('Location & Type', {
            'fields': ('county', 'buyer_type')
        }),
        ('Points & Status', {
            'fields': ('points', 'profile_completed')
        }),
        ('Referrals (User-to-User)', {
            'fields': ('referral_code', 'referred_by', 'referral_points_earned'),
            'classes': ('collapse',)
        }),
        ('Partnership (Affiliate)', {
            'fields': ('partnership',),
        }),
        ('Statistics', {
            'fields': ('user_stats',),
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def full_name(self, obj):
        name = f"{obj.first_name} {obj.second_name}".strip()
        return name if name else '-'

    full_name.short_description = 'Name'

    def partnership_badge(self, obj):
        if obj.partnership:
            return format_html(
                '<span style="background: linear-gradient(135deg, #9333ea 0%, #c026d3 100%); '
                'color: white; padding: 4px 10px; border-radius: 8px; font-size: 11px; '
                'font-weight: bold; display: inline-block;">'
                '<i class="fas fa-handshake"></i> {}</span>',
                obj.partnership.name
            )
        return format_html(
            '<span style="color: #94a3b8; font-size: 11px;">No partner</span>'
        )

    partnership_badge.short_description = 'Partnership'

    def user_stats(self, obj):
        scans = Scan.objects.filter(profile=obj).count()
        referrals = obj.referrals.filter(profile_completed=True).count()
        redemptions = Redemption.objects.filter(profile=obj).count()

        html = f'''
        <div style="background: #f9fafb; padding: 16px; border-radius: 8px;">
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                <div style="text-align: center;">
                    <div style="font-size: 20px; font-weight: bold; color: #6366f1;">{scans}</div>
                    <div style="font-size: 11px; color: #6b7280;">Total Scans</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 20px; font-weight: bold; color: #10b981;">{referrals}</div>
                    <div style="font-size: 11px; color: #6b7280;">Referrals</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 20px; font-weight: bold; color: #f59e0b;">{redemptions}</div>
                    <div style="font-size: 11px; color: #6b7280;">Redemptions</div>
                </div>
            </div>
        '''

        if obj.partnership:
            earnings = PartnershipEarning.objects.filter(profile=obj).aggregate(
                total=Sum('points_earned')
            )
            html += f'''
            <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #e5e7eb; text-align: center;">
                <div style="font-size: 11px; color: #6b7280; margin-bottom: 4px;">Partner Earned</div>
                <div style="font-size: 18px; font-weight: bold; color: #9333ea;">
                    {earnings['total'] or 0} points
                </div>
                <div style="font-size: 10px; color: #9333ea; margin-top: 2px;">
                    from {obj.partnership.name}
                </div>
            </div>
            '''

        html += '</div>'
        return format_html(html)

    user_stats.short_description = 'User Statistics'


# ============================================
# SCAN ADMIN (Enhanced)
# ============================================

@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user_info', 'pack_info', 'points_awarded',
        'partnership_status', 'scanned_at'
    ]
    list_filter = ['partnership_points_awarded', 'scanned_at']
    search_fields = ['profile__phone', 'pack__code', 'pack__sku']
    readonly_fields = [
        'profile', 'pack', 'points_awarded',
        'partnership_points_awarded', 'scanned_at'
    ]
    date_hierarchy = 'scanned_at'

    def user_info(self, obj):
        return format_html(
            '{}<br><small style="color: #64748b;">{}</small>',
            obj.profile.phone,
            f"{obj.profile.first_name} {obj.profile.second_name}".strip() or '-'
        )

    user_info.short_description = 'User'

    def pack_info(self, obj):
        return format_html(
            '<strong>{}</strong><br><small style="color: #64748b; font-family: monospace;">{}</small>',
            obj.pack.sku,
            obj.pack.code[:12] + '...'
        )

    pack_info.short_description = 'Pack'

    def partnership_status(self, obj):
        if obj.partnership_points_awarded:
            return format_html(
                '<span style="color: #10b981; font-weight: bold;">✓ Awarded</span>'
            )
        elif obj.profile.partnership:
            return format_html(
                '<span style="color: #f59e0b;">⚠ Pending</span>'
            )
        return format_html(
            '<span style="color: #94a3b8;">- N/A</span>'
        )

    partnership_status.short_description = 'Partner Points'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ============================================
# PACK CODE ADMIN
# ============================================

@admin.register(PackCode)
class PackCodeAdmin(admin.ModelAdmin):
    list_display = ['code_short', 'sku', 'points', 'used_badge', 'used_by', 'created_at']
    list_filter = ['used', 'sku', 'created_at']
    search_fields = ['code', 'sku', 'used_by__phone']
    readonly_fields = ['code', 'used_at', 'created_at']

    actions = ['mark_as_unused']

    def code_short(self, obj):
        return format_html(
            '<code style="background: #f3f4f6; padding: 4px 8px; border-radius: 4px; font-size: 11px;">{}</code>',
            obj.code[:16] + '...' if len(obj.code) > 16 else obj.code
        )

    code_short.short_description = 'Code'

    def used_badge(self, obj):
        if obj.used:
            return format_html(
                '<span style="background: #ef4444; color: white; padding: 3px 8px; '
                'border-radius: 6px; font-size: 10px; font-weight: bold;">USED</span>'
            )
        return format_html(
            '<span style="background: #10b981; color: white; padding: 3px 8px; '
            'border-radius: 6px; font-size: 10px; font-weight: bold;">AVAILABLE</span>'
        )

    used_badge.short_description = 'Status'

    def mark_as_unused(self, request, queryset):
        count = queryset.update(used=False, used_by=None, used_at=None)
        self.message_user(request, f'{count} pack code(s) marked as unused.')

    mark_as_unused.short_description = 'Mark as unused (reset)'


# ============================================
# OTHER MODELS
# ============================================

@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ['name', 'cost_points', 'active', 'description_short']
    list_filter = ['active']
    search_fields = ['name', 'description']

    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description

    description_short.short_description = 'Description'


@admin.register(Redemption)
class RedemptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'reward', 'created_at', 'fulfilled']
    list_filter = ['fulfilled', 'created_at']
    search_fields = ['profile__phone', 'reward__name']
    date_hierarchy = 'created_at'


@admin.register(ReferralSettings)
class ReferralSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'points_for_referrer', 'points_for_referee',
        'max_referrals_per_user', 'referral_enabled'
    ]

    def has_add_permission(self, request):
        return not ReferralSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'referrer', 'referred',
        'points_awarded_to_referrer', 'points_awarded_to_referred',
        'created_at'
    ]
    list_filter = ['created_at']
    search_fields = ['referrer__phone', 'referred__phone']
    date_hierarchy = 'created_at'
    readonly_fields = [
        'referrer', 'referred',
        'points_awarded_to_referrer', 'points_awarded_to_referred',
        'created_at'
    ]

    def has_add_permission(self, request):
        return False


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ['phone', 'code', 'used', 'created_at', 'is_valid_display']
    list_filter = ['used', 'created_at']
    search_fields = ['phone', 'code']
    readonly_fields = ['phone', 'code', 'created_at', 'used']
    date_hierarchy = 'created_at'

    def is_valid_display(self, obj):
        if obj.is_valid():
            return format_html(
                '<span style="color: #10b981; font-weight: bold;">✓ Valid</span>'
            )
        return format_html(
            '<span style="color: #ef4444;">✕ Expired/Used</span>'
        )

    is_valid_display.short_description = 'Status'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PointTransferSettings)
class PointTransferSettingsAdmin(admin.ModelAdmin):
    list_display = ['transfer_enabled', 'min_transfer_amount', 'max_transfer_amount',
                    'daily_transfer_limit', 'transfer_fee_percentage']

    def has_add_permission(self, request):
        return not PointTransferSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PointTransfer)
class PointTransferAdmin(admin.ModelAdmin):
    list_display = ['sender', 'recipient', 'amount', 'fee', 'net_amount',
                    'status', 'was_invite', 'created_at']
    list_filter = ['status', 'was_invite', 'created_at']
    search_fields = ['sender__phone', 'recipient__phone', 'invite_phone']
    readonly_fields = ['sender', 'recipient', 'amount', 'fee', 'net_amount',
                       'message', 'created_at', 'was_invite', 'invite_phone', 'invite_accepted']
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False


@admin.register(PendingInvite)
class PendingInviteAdmin(admin.ModelAdmin):
    list_display = ['inviter', 'phone', 'points_promised', 'accepted', 'created_at']
    list_filter = ['accepted', 'created_at']
    search_fields = ['inviter__phone', 'phone']
    readonly_fields = ['inviter', 'phone', 'points_promised', 'message',
                       'created_at', 'accepted', 'accepted_at']
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False


@admin.register(ListingPartner)
class ListingPartnerAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'code', 'phone', 'approved', 'active',
                    'total_products_count', 'pending_payout', 'total_paid_out', 'created_at']
    list_filter = ['approved', 'active', 'profile_completed', 'created_at']
    search_fields = ['company_name', 'code', 'phone', 'email', 'contact_person']
    readonly_fields = ['code', 'total_revenue', 'Melvins_commission_earned',
                       'partner_earnings', 'pending_payout', 'total_paid_out',
                       'created_at', 'updated_at']

    fieldsets = (
        ('Company Information', {
            'fields': ('user', 'phone', 'company_name', 'code', 'contact_person', 'email')
        }),
        ('Business Details', {
            'fields': ('business_registration', 'tax_pin')
        }),
        ('Payment Information', {
            'fields': ('bank_name', 'bank_account_number', 'bank_account_name', 'mpesa_number')
        }),
        ('Commission & Financials', {
            'fields': ('commission_rate', 'total_revenue', 'Melvins_commission_earned',
                       'partner_earnings', 'pending_payout', 'total_paid_out')
        }),
        ('Status', {
            'fields': ('approved', 'active', 'profile_completed', 'created_at', 'updated_at')
        }),
    )

    actions = ['approve_partners', 'reject_partners', 'process_payout']

    def total_products_count(self, obj):
        return obj.total_products()

    total_products_count.short_description = 'Total Products'

    def approve_partners(self, request, queryset):
        updated = queryset.update(approved=True)
        self.message_user(request, f'{updated} listing partners approved.')

    approve_partners.short_description = 'Approve selected partners'

    def reject_partners(self, request, queryset):
        updated = queryset.update(approved=False)
        self.message_user(request, f'{updated} listing partners rejected.')

    reject_partners.short_description = 'Reject selected partners'

    def process_payout(self, request, queryset):
        # This would open a form to process payout
        # For now, just show the partners with pending payouts
        total_payout = sum([p.pending_payout for p in queryset])
        self.message_user(
            request,
            f'Total pending payout for selected partners: KES {total_payout}'
        )

    process_payout.short_description = 'View payout summary'


@admin.register(ProductListing)
class ProductListingAdmin(admin.ModelAdmin):
    list_display = ['name', 'listing_partner', 'partner_price', 'Melvins_price',
                    'points_required', 'stock_quantity', 'status', 'total_redemptions',
                    'featured', 'created_at']
    list_filter = ['status', 'featured', 'active', 'category', 'created_at']
    search_fields = ['name', 'listing_partner__company_name', 'category']
    readonly_fields = ['listing_partner', 'partner_price', 'total_redemptions',
                       'created_at', 'updated_at', 'approved_at', 'approved_by']
    filter_horizontal = ['available_at_shops']

    fieldsets = (
        ('Product Information', {
            'fields': ('listing_partner', 'name', 'description', 'category', 'image')
        }),
        ('Pricing (Partner Sets)', {
            'fields': ('partner_price',)
        }),
        ('Pricing (Melvins Sets)', {
            'fields': ('Melvins_price', 'points_required', 'point_value'),
            'description': 'Set the final price and points required'
        }),
        ('Availability', {
            'fields': ('stock_quantity', 'redemption_limit', 'available_at_shops')
        }),
        ('Status', {
            'fields': ('status', 'rejection_reason', 'active', 'featured')
        }),
        ('Tracking', {
            'fields': ('total_redemptions', 'created_at', 'updated_at',
                       'approved_at', 'approved_by'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_products', 'reject_products', 'feature_products']

    def approve_products(self, request, queryset):
        # Check if prices and points are set
        for product in queryset:
            if not product.Melvins_price or not product.points_required:
                self.message_user(
                    request,
                    f'Cannot approve "{product.name}" - set Melvins_price and points_required first',
                    level='error'
                )
                continue

            product.status = 'approved'
            product.approved_at = timezone.now()
            product.approved_by = request.user
            product.save()

        self.message_user(request, 'Selected products approved.')

    approve_products.short_description = 'Approve selected products'

    def reject_products(self, request, queryset):
        # This would ideally open a form to enter rejection reason
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} products rejected.')

    reject_products.short_description = 'Reject selected products'

    def feature_products(self, request, queryset):
        updated = queryset.update(featured=True)
        self.message_user(request, f'{updated} products featured.')

    feature_products.short_description = 'Feature selected products'


@admin.register(ProductRedemption)
class ProductRedemptionAdmin(admin.ModelAdmin):
    list_display = ['redemption_code', 'product', 'profile', 'points_deducted',
                    'partner_earning', 'Melvins_commission', 'status', 'paid_to_partner',
                    'created_at']
    list_filter = ['status', 'paid_to_partner', 'created_at', 'product__listing_partner']
    search_fields = ['redemption_code', 'profile__phone', 'product__name']
    readonly_fields = ['product', 'profile', 'points_deducted', 'amount_charged',
                       'Melvins_commission', 'partner_earning', 'redemption_code',
                       'created_at', 'fulfilled_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Redemption Details', {
            'fields': ('product', 'profile', 'redeemed_at_shop', 'redemption_code')
        }),
        ('Financial', {
            'fields': ('points_deducted', 'amount_charged', 'Melvins_commission', 'partner_earning')
        }),
        ('Status & Tracking', {
            'fields': ('status', 'created_at', 'fulfilled_at')
        }),
        ('Payout', {
            'fields': ('paid_to_partner', 'paid_at')
        }),
    )

    actions = ['mark_fulfilled', 'mark_paid']

    def mark_fulfilled(self, request, queryset):
        updated = queryset.update(status='fulfilled', fulfilled_at=timezone.now())
        self.message_user(request, f'{updated} redemptions marked as fulfilled.')

    mark_fulfilled.short_description = 'Mark as fulfilled'

    def mark_paid(self, request, queryset):
        # Update redemptions
        updated = queryset.filter(status='fulfilled').update(
            paid_to_partner=True,
            paid_at=timezone.now()
        )

        # Update listing partners' pending payout
        for redemption in queryset.filter(status='fulfilled'):
            partner = redemption.product.listing_partner
            partner.pending_payout -= redemption.partner_earning
            partner.total_paid_out += redemption.partner_earning
            partner.save(update_fields=['pending_payout', 'total_paid_out'])

        self.message_user(request, f'{updated} redemptions marked as paid.')

    mark_paid.short_description = 'Mark as paid to partner'


@admin.register(PartnerPayout)
class PartnerPayoutAdmin(admin.ModelAdmin):
    list_display = ['listing_partner', 'amount', 'payment_method', 'status',
                    'created_at', 'completed_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['listing_partner__company_name', 'reference_number']
    readonly_fields = ['created_at', 'processed_at', 'completed_at', 'processed_by']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Payout Information', {
            'fields': ('listing_partner', 'amount', 'payment_method')
        }),
        ('Payment Details', {
            'fields': ('reference_number', 'notes')
        }),
        ('Status & Tracking', {
            'fields': ('status', 'created_at', 'processed_at', 'completed_at', 'processed_by')
        }),
    )

    actions = ['mark_completed']

    def mark_completed(self, request, queryset):
        updated = queryset.update(
            status='completed',
            completed_at=timezone.now(),
            processed_by=request.user
        )
        self.message_user(request, f'{updated} payouts marked as completed.')


@admin.register(ChallengeWinner)
class ChallengeWinnerAdmin(admin.ModelAdmin):
    list_display = [
        'challenge_title', 'position_badge', 'profile_display',
        'masked_phone', 'entry_weight', 'prize_status', 'selected_at'
    ]
    list_filter = [
        'prize_claimed', 'challenge__frequency',
        'challenge__is_public_results', 'selected_at'
    ]
    search_fields = [
        'challenge__title', 'profile__phone',
        'profile__first_name', 'profile__second_name'
    ]
    readonly_fields = [
        'challenge', 'profile', 'position', 'entry_weight',
        'total_entries', 'selected_at', 'winner_details_display'
    ]
    date_hierarchy = 'selected_at'

    fieldsets = (
        ('Winner Information', {
            'fields': ('challenge', 'profile', 'position', 'entry_weight', 'total_entries')
        }),
        ('Display Details', {
            'fields': ('winner_details_display',),
            'description': 'How this winner appears to the public'
        }),
        ('Prize Management', {
            'fields': ('prize_claimed', 'prize_claimed_at', 'prize_delivery_notes')
        }),
        ('Notifications', {
            'fields': ('notified_at',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('selected_at',),
            'classes': ('collapse',)
        }),
    )

    actions = [
        'mark_prizes_claimed',
        'mark_as_notified',
        'send_winner_notification',
        'export_winners_csv'
    ]

    def challenge_title(self, obj):
        """Display challenge with status"""
        return format_html(
            '<strong>{}</strong><br>'
            '<small style="color: #6b7280;">{}</small>',
            obj.challenge.title,
            obj.challenge.get_frequency_display()
        )

    challenge_title.short_description = 'Challenge'

    def position_badge(self, obj):
        """Display position with medal emoji"""
        colors = {
            1: '#fbbf24',  # Gold
            2: '#d1d5db',  # Silver
            3: '#fb923c',  # Bronze
        }

        emoji = {
            1: '🥇',
            2: '🥈',
            3: '🥉'
        }

        color = colors.get(obj.position, '#6b7280')
        medal = emoji.get(obj.position, '🏆')

        suffix = 'st' if obj.position == 1 else 'nd' if obj.position == 2 else 'rd' if obj.position == 3 else 'th'

        return format_html(
            '<span style="background: {}; color: white; padding: 6px 12px; '
            'border-radius: 8px; font-size: 14px; font-weight: bold; '
            'display: inline-block;">{} {}{}</span>',
            color, medal, obj.position, suffix
        )

    position_badge.short_description = 'Position'

    def profile_display(self, obj):
        """Display full profile info for admin"""
        return format_html(
            '<strong>{} {}</strong><br>'
            '<small style="color: #6b7280;">{}</small>',
            obj.profile.first_name,
            obj.profile.second_name,
            obj.profile.phone
        )

    profile_display.short_description = 'Winner'

    def masked_phone(self, obj):
        """Show how phone appears to public"""
        return format_html(
            '<code style="background: #f3f4f6; padding: 4px 8px; '
            'border-radius: 4px; font-size: 12px;">{}</code>',
            obj.get_masked_phone()
        )

    masked_phone.short_description = 'Public Display'

    def prize_status(self, obj):
        """Display prize claim status"""
        if obj.prize_claimed:
            return format_html(
                '<span style="background: #10b981; color: white; padding: 4px 10px; '
                'border-radius: 8px; font-size: 11px; font-weight: bold;">'
                '✅ CLAIMED</span><br>'
                '<small style="color: #6b7280; font-size: 10px;">{}</small>',
                obj.prize_claimed_at.strftime('%b %d, %Y') if obj.prize_claimed_at else '-'
            )

        return format_html(
            '<span style="background: #f59e0b; color: white; padding: 4px 10px; '
            'border-radius: 8px; font-size: 11px; font-weight: bold;">'
            '⏳ PENDING</span>'
        )

    prize_status.short_description = 'Prize Status'

    def winner_details_display(self, obj):
        """Show how winner appears publicly vs privately"""
        html = f'''
        <div style="background: #f9fafb; padding: 16px; border-radius: 8px;">
            <div style="margin-bottom: 16px;">
                <h4 style="margin: 0 0 8px 0; color: #1f2937;">Public Display</h4>
                <div style="background: white; padding: 12px; border-radius: 6px; border: 2px solid #e5e7eb;">
                    <div style="font-size: 18px; font-weight: bold; color: #6366f1; margin-bottom: 4px;">
                        {obj.get_masked_phone()}
                    </div>
                    <div style="font-size: 14px; color: #6b7280;">
                        {obj.get_display_name()}
                    </div>
                    <div style="font-size: 12px; color: #9ca3af; margin-top: 4px;">
                        Entry Weight: {obj.entry_weight:.2f}
                    </div>
                </div>
                <p style="margin: 8px 0 0 0; font-size: 11px; color: #6b7280;">
                    <em>This is how the winner appears to public viewers</em>
                </p>
            </div>

            <div>
                <h4 style="margin: 0 0 8px 0; color: #1f2937;">Admin View (Full Details)</h4>
                <div style="background: white; padding: 12px; border-radius: 6px; border: 2px solid #6366f1;">
                    <div style="font-size: 18px; font-weight: bold; color: #1f2937; margin-bottom: 4px;">
                        {obj.profile.phone}
                    </div>
                    <div style="font-size: 14px; color: #6b7280;">
                        {obj.profile.first_name} {obj.profile.second_name}
                    </div>
                    <div style="font-size: 12px; color: #9ca3af; margin-top: 8px;">
                        <strong>Points at Entry:</strong> {obj.profile.points}<br>
                        <strong>Referrals:</strong> {obj.profile.successful_referrals_count()}<br>
                        <strong>County:</strong> {obj.profile.get_county_display() if obj.profile.county else 'N/A'}
                    </div>
                </div>
            </div>
        </div>
        '''
        return format_html(html)

    winner_details_display.short_description = 'Winner Display Preview'

    # ============================================
    # ACTIONS
    # ============================================

    def mark_prizes_claimed(self, request, queryset):
        """Mark selected prizes as claimed"""
        updated = queryset.update(prize_claimed=True, prize_claimed_at=timezone.now())
        self.message_user(
            request,
            f'{updated} prize(s) marked as claimed.',
            level='success'
        )

    mark_prizes_claimed.short_description = '✅ Mark prizes as claimed'

    def mark_as_notified(self, request, queryset):
        """Mark winners as notified"""
        updated = queryset.update(notified_at=timezone.now())
        self.message_user(
            request,
            f'{updated} winner(s) marked as notified.',
            level='success'
        )

    mark_as_notified.short_description = '📧 Mark as notified'

    def send_winner_notification(self, request, queryset):
        """Send SMS/Email notifications to winners"""
        count = 0
        for winner in queryset:
            # TODO: Integrate with your SMS provider
            # send_sms(
            #     winner.profile.phone,
            #     f"Congratulations! You won {winner.challenge.title}! "
            #     f"Position: {winner.position}. Prize: {winner.challenge.reward_value}. "
            #     f"Contact us to claim your prize."
            # )

            winner.notified_at = timezone.now()
            winner.save(update_fields=['notified_at'])
            count += 1

        self.message_user(
            request,
            f'{count} winner(s) notified. (SMS integration pending)',
            level='success'
        )

    send_winner_notification.short_description = '📱 Send notifications'

    def export_winners_csv(self, request, queryset):
        """Export winners to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="challenge_winners.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Challenge', 'Position', 'Phone', 'Name',
            'Entry Weight', 'Points', 'Referrals',
            'Prize Claimed', 'Notified', 'Selected Date'
        ])

        for winner in queryset:
            writer.writerow([
                winner.challenge.title,
                winner.position,
                winner.profile.phone,
                f"{winner.profile.first_name} {winner.profile.second_name}",
                winner.entry_weight,
                winner.profile.points,
                winner.profile.successful_referrals_count(),
                'Yes' if winner.prize_claimed else 'No',
                'Yes' if winner.notified_at else 'No',
                winner.selected_at.strftime('%Y-%m-%d %H:%M')
            ])

        return response

    export_winners_csv.short_description = '📥 Export to CSV'

    def has_add_permission(self, request):
        """Prevent manual addition"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of winners"""
        return False


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'frequency', 'status_badge', 'number_of_winners',
        'total_entries', 'visibility_badge', 'start_date', 'end_date',
        'featured', 'live_draw_actions'
    ]
    list_filter = [
        'status', 'frequency', 'featured', 'active',
        'is_public_results', 'draw_in_progress', 'start_date'
    ]
    search_fields = ['title', 'description']
    readonly_fields = [
        'total_entries', 'winners_selected_at', 'draw_completed_at',
        'created_at', 'updated_at', 'live_draw_links'
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'image', 'frequency')
        }),
        ('Timing', {
            'fields': ('start_date', 'end_date', 'live_draw_scheduled')
        }),
        ('Winners & Rewards', {
            'fields': ('number_of_winners', 'reward_type', 'reward_value', 'reward_description')
        }),
        ('Weighting Configuration', {
            'fields': ('points_weight', 'referrals_weight'),
            'description': 'Higher weights give more advantage to users with points/referrals'
        }),
        ('Eligibility Criteria', {
            'fields': ('min_points_required', 'min_scans_required', 'counties_eligible'),
            'classes': ('collapse',)
        }),
        ('Visibility & Access', {
            'fields': ('is_public_results',),
            'description': 'Public = Anyone can see winners. Private = Only participants can see winners'
        }),
        ('Live Draw Settings', {
            'fields': ('draw_in_progress', 'live_draw_url', 'live_draw_links'),
            'description': 'Manage live draw broadcast'
        }),
        ('Status & Tracking', {
            'fields': (
                'status', 'active', 'featured',
                'total_entries', 'winners_selected_at', 'draw_completed_at'
            )
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = [
        'activate_challenges',
        'end_challenges',
        'start_live_draw_action',
        'open_live_draw_page',
        'make_public_results',
        'make_private_results',
        'reset_draw_status'
    ]

    # ===================================================
    # DISPLAY HELPERS
    # ===================================================

    def status_badge(self, obj):
        colors = {
            'upcoming': '#f59e0b',
            'active': '#10b981',
            'ended': '#6b7280',
            'winners_selected': '#6366f1'
        }

        if obj.draw_in_progress:
            return format_html(
                '<span style="background: #ef4444; color: white; padding: 4px 10px; '
                'border-radius: 8px; font-size: 11px; font-weight: bold; '
                'animation: pulse 2s ease-in-out infinite;">🔴 LIVE DRAW</span>'
            )

        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; '
            'border-radius: 8px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display().upper()
        )

    status_badge.short_description = 'Status'

    def visibility_badge(self, obj):
        if obj.is_public_results:
            return format_html(
                '<span style="background: #10b981; color: white; padding: 4px 10px; '
                'border-radius: 8px; font-size: 11px; font-weight: bold;">🌍 PUBLIC</span>'
            )
        return format_html(
            '<span style="background: #f59e0b; color: white; padding: 4px 10px; '
            'border-radius: 8px; font-size: 11px; font-weight: bold;">🔒 PRIVATE</span>'
        )

    visibility_badge.short_description = 'Results'

    def live_draw_actions(self, obj):
        if obj.status == 'winners_selected':
            return format_html(
                '<a href="/club/challenge/{}/winners/" target="_blank" '
                'style="background: #6366f1; color: white; padding: 6px 12px; '
                'border-radius: 6px; text-decoration: none; font-size: 11px; '
                'display: inline-block; font-weight: bold;">🏆 View Winners</a>',
                obj.id
            )

        if obj.draw_in_progress:
            return format_html(
                '<a href="/club/challenge/{}/live-draw/" target="_blank" '
                'style="background: #ef4444; color: white; padding: 6px 12px; '
                'border-radius: 6px; text-decoration: none; font-size: 11px; '
                'display: inline-block; font-weight: bold; animation: pulse 2s ease-in-out infinite;">'
                '🔴 Open Live Draw</a>',
                obj.id
            )

        now = timezone.now()
        if obj.end_date < now and obj.status != 'winners_selected':
            return format_html(
                '<a href="/club/challenge/{}/live-draw/" target="_blank" '
                'style="background: #10b981; color: white; padding: 6px 12px; '
                'border-radius: 6px; text-decoration: none; font-size: 11px; '
                'display: inline-block; font-weight: bold;">🎲 Start Draw</a>',
                obj.id
            )

        return format_html('<span style="color: #6b7280; font-size: 11px;">Not Ready</span>')

    live_draw_actions.short_description = 'Actions'

    # ===================================================
    # FIXED VERSION OF live_draw_links
    # ===================================================

    def live_draw_links(self, obj):
        """Display all relevant links for live draw"""
        request = getattr(self, 'request', None)
        if request:
            public_url = request.build_absolute_uri(f'/club/challenge/{obj.id}/watch-live/')
        else:
            public_url = f'/club/challenge/{obj.id}/watch-live/'

        html = '<div style="background: #f9fafb; padding: 16px; border-radius: 8px;">'

        # Diagnostic/Status Link
        html += f'''
        <div style="margin-bottom: 12px;">
            <strong>🔍 Status Check & Diagnostics:</strong><br>
            <a href="/club/challenge/{obj.id}/status-test/" target="_blank"
               style="background: #8b5cf6; color: white; padding: 8px 16px; 
                      border-radius: 6px; text-decoration: none; display: inline-block; 
                      margin-top: 4px; font-weight: bold;">
                🧪 Open Diagnostic Page
            </a>
            <p style="margin: 4px 0 0 0; font-size: 11px; color: #6b7280;">
                Check system status, API endpoints, and debug issues
            </p>
        </div>
        '''

        # Admin Live Draw Control
        html += f'''
        <div style="margin-bottom: 12px;">
            <strong>🎬 Admin Control Panel:</strong><br>
            <a href="/club/challenge/{obj.id}/live-draw/" target="_blank"
               style="background: #6366f1; color: white; padding: 8px 16px; 
                      border-radius: 6px; text-decoration: none; display: inline-block; 
                      margin-top: 4px; font-weight: bold;">
                Open Live Draw Page
            </a>
            <p style="margin: 4px 0 0 0; font-size: 11px; color: #6b7280;">
                Use this to start and control the live draw
            </p>
        </div>
        '''

        # Public Watch Link
        if obj.draw_in_progress or obj.status == 'winners_selected':
            html += f'''
            <div style="margin-bottom: 12px;">
                <strong>📺 Public Watch Link:</strong><br>
                <code style="background: white; padding: 8px; display: block; 
                             border-radius: 4px; font-size: 11px; margin: 4px 0;">
                    {public_url}
                </code>
                <button onclick="navigator.clipboard.writeText('{public_url}'); alert('Copied!');"
                        style="background: #10b981; color: white; border: none; 
                               padding: 6px 12px; border-radius: 4px; cursor: pointer; 
                               font-size: 11px; margin-top: 4px;">
                    📋 Copy Link
                </button>
                <p style="margin: 4px 0 0 0; font-size: 11px; color: #6b7280;">
                    Share this link for public viewing
                </p>
            </div>
            '''

        # Winners Link
        if obj.status == 'winners_selected':
            html += f'''
            <div style="margin-bottom: 12px;">
                <strong>🏆 Winners Page:</strong><br>
                <a href="/club/challenge/{obj.id}/winners/" target="_blank"
                   style="background: #f59e0b; color: white; padding: 8px 16px; 
                          border-radius: 6px; text-decoration: none; display: inline-block; 
                          margin-top: 4px; font-weight: bold;">
                    View Winners
                </a>
            </div>
            '''

        if obj.draw_in_progress:
            html += '''
            <div style="background: #fef3c7; padding: 8px; border-radius: 4px; 
                        border-left: 4px solid #f59e0b;">
                <strong style="color: #92400e;">⚠️ Live Draw In Progress</strong><br>
                <span style="font-size: 11px; color: #78350f;">
                    Winners are being selected right now!
                </span>
            </div>
            '''

        html += '</div>'
        return format_html(html)

    live_draw_links.short_description = 'Live Draw Links'

    # ===================================================
    # ADMIN ACTIONS
    # ===================================================

    def activate_challenges(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} challenge(s) activated.')
    activate_challenges.short_description = '✅ Activate selected challenges'

    def end_challenges(self, request, queryset):
        updated = queryset.update(status='ended')
        self.message_user(request, f'{updated} challenge(s) ended.')
    end_challenges.short_description = '⏹️ End selected challenges'

    def start_live_draw_action(self, request, queryset):
        count = 0
        for challenge in queryset:
            if challenge.status == 'winners_selected':
                self.message_user(request, f'Winners already selected for "{challenge.title}"', level='warning')
                continue
            if challenge.end_date > timezone.now():
                self.message_user(request, f'Challenge "{challenge.title}" has not ended yet', level='error')
                continue
            challenge.draw_in_progress = True
            challenge.save(update_fields=['draw_in_progress'])
            count += 1

        if count > 0:
            self.message_user(request, f'{count} challenge(s) marked as ready. Open the Live Draw page to select winners.', level='success')
    start_live_draw_action.short_description = '🎬 Prepare for Live Draw'

    def open_live_draw_page(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, 'Please select exactly one challenge', level='error')
            return
        challenge = queryset.first()
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(f'/club/challenge/{challenge.id}/live-draw/')
    open_live_draw_page.short_description = '🎲 Open Live Draw Page'

    def make_public_results(self, request, queryset):
        updated = queryset.update(is_public_results=True)
        self.message_user(request, f'{updated} challenge(s) set to PUBLIC results (anyone can view winners)', level='success')
    make_public_results.short_description = '🌍 Make Results PUBLIC'

    def make_private_results(self, request, queryset):
        updated = queryset.update(is_public_results=False)
        self.message_user(request, f'{updated} challenge(s) set to PRIVATE results (only participants can view)', level='success')
    make_private_results.short_description = '🔒 Make Results PRIVATE'

    def reset_draw_status(self, request, queryset):
        updated = queryset.update(draw_in_progress=False)
        self.message_user(request, f'{updated} challenge(s) draw status reset. You can now start the draw again.', level='success')
    reset_draw_status.short_description = '🔄 Reset Draw Status (if stuck)'

    # ===================================================
    # CUSTOM METHODS
    # ===================================================

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Capture request for use in readonly fields like live_draw_links"""
        self.request = request
        return super().change_view(request, object_id, form_url, extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:challenge_id>/live-preview/',
                self.admin_site.admin_view(self.live_preview_view),
                name='club_challenge_live_preview'
            ),
        ]
        return custom_urls + urls

    def live_preview_view(self, request, challenge_id):
        from django.shortcuts import redirect
        return redirect('club:challenge_live_draw', challenge_id=challenge_id)

# Add CSS for pulse animation to admin
from django.contrib import admin as django_admin


# Add this to inject custom CSS
class CustomAdminSite(django_admin.AdminSite):
    def each_context(self, request):
        context = super().each_context(request)
        # Inject custom CSS for animations
        return context


# Register custom CSS in your admin template or use this approach:
def admin_custom_css():
    return '''
    <style>
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    </style> '''


@admin.register(ChallengeEntry)
class ChallengeEntryAdmin(admin.ModelAdmin):
    list_display = ['challenge', 'profile', 'entry_weight', 'points_at_entry',
                    'referrals_at_entry', 'entered_at']
    list_filter = ['challenge', 'entered_at']
    search_fields = ['challenge__title', 'profile__phone']
    readonly_fields = ['challenge', 'profile', 'entry_weight', 'points_at_entry',
                       'referrals_at_entry', 'entered_at']

    def has_add_permission(self, request):
        return False


# ============================================
# TEA ESTATES COLLECTION ADMIN
# ============================================

class EstateCardInline(admin.TabularInline):
    model = EstateCard
    extra = 0
    fields = ['card_number', 'title', 'rarity', 'drop_weight', 'active']
    readonly_fields = ['card_number', 'title']
    can_delete = False


@admin.register(TeaEstate)
class TeaEstateAdmin(admin.ModelAdmin):
    list_display = ['name', 'region', 'elevation', 'active', 'created_at']
    list_filter = ['region', 'active', 'created_at']
    search_fields = ['name', 'region', 'description']
    readonly_fields = ['created_at']
    fieldsets = (
        ('Estate Information', {
            'fields': ('name', 'region', 'description', 'image')
        }),
        ('Details', {
            'fields': ('elevation', 'tasting_notes', 'brewing_tips', 'harvest_season')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('active', 'created_at')
        }),
    )


@admin.register(EstateCollection)
class EstateCollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'theme', 'total_cards', 'completion_reward_points', 
                    'is_active', 'start_date', 'end_date', 'collection_status']
    list_filter = ['is_active', 'start_date', 'end_date']
    search_fields = ['name', 'theme', 'description']
    readonly_fields = ['created_at']
    inlines = [EstateCardInline]
    
    fieldsets = (
        ('Collection Information', {
            'fields': ('name', 'theme', 'description', 'featured_image')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'is_active')
        }),
        ('Rewards', {
            'fields': ('total_cards', 'completion_reward_points', 'completion_reward_description')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def collection_status(self, obj):
        if obj.is_currently_active():
            return format_html(
                '<span style="background: #10b981; color: white; padding: 4px 12px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">🟢 ACTIVE</span>'
            )
        elif obj.start_date > timezone.now():
            return format_html(
                '<span style="background: #f59e0b; color: white; padding: 4px 12px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">⏳ UPCOMING</span>'
            )
        else:
            return format_html(
                '<span style="background: #94a3b8; color: white; padding: 4px 12px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">⏹ ENDED</span>'
            )
    collection_status.short_description = 'Status'


@admin.register(EstateCard)
class EstateCardAdmin(admin.ModelAdmin):
    list_display = ['card_number', 'get_display_title', 'estate', 'collection', 
                    'rarity_badge', 'drop_weight', 'active']
    list_filter = ['rarity', 'collection', 'active']
    search_fields = ['title', 'estate__name', 'collection__name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Card Information', {
            'fields': ('collection', 'estate', 'card_number', 'title', 'flavor_text')
        }),
        ('Drop Configuration', {
            'fields': ('rarity', 'drop_weight')
        }),
        ('Visuals', {
            'fields': ('card_image', 'frame_color')
        }),
        ('Status', {
            'fields': ('active', 'created_at')
        }),
    )
    
    def rarity_badge(self, obj):
        colors = {
            'common': '#94a3b8',
            'uncommon': '#01453a',
            'rare': '#CC8B65'
        }
        color = colors.get(obj.rarity, '#94a3b8')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_rarity_display()
        )
    rarity_badge.short_description = 'Rarity'


@admin.register(UserCardCollection)
class UserCardCollectionAdmin(admin.ModelAdmin):
    list_display = ['profile', 'card', 'is_duplicate', 'is_new', 'obtained_at']
    list_filter = ['is_duplicate', 'is_new', 'card__collection', 'obtained_at']
    search_fields = ['profile__phone', 'card__title', 'card__estate__name']
    readonly_fields = ['profile', 'card', 'from_pack', 'from_scan', 'is_duplicate', 'obtained_at']
    date_hierarchy = 'obtained_at'
    
    def has_add_permission(self, request):
        return False


@admin.register(CollectionCompletion)
class CollectionCompletionAdmin(admin.ModelAdmin):
    list_display = ['profile', 'collection', 'completed_at', 'points_awarded', 
                    'reward_claimed', 'reward_claimed_at']
    list_filter = ['reward_claimed', 'collection', 'completed_at']
    search_fields = ['profile__phone', 'collection__name']
    readonly_fields = ['profile', 'collection', 'completed_at', 'points_awarded', 
                       'reward_claimed', 'reward_claimed_at']
    date_hierarchy = 'completed_at'
    
    def has_add_permission(self, request):
        return False


# ============================================
# CUSTOMIZE ADMIN SITE - MELVINS CLUB
# ============================================

admin.site.site_header = 'Melvins Club Administration'
admin.site.site_title = 'Melvins Club Admin'
admin.site.index_title = 'Welcome to Melvins Club Admin Portal'


