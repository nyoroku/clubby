# urls.py - Update your URL patterns to match the new PIN-based views

from django.urls import path
from . import views

app_name = 'club'

urlpatterns = [
    # ============ USER AUTHENTICATION (PIN-BASED) ============
    path('', views.landing_page, name='landing_page'),
    path('login/', views.user_login, name='user_login'),
    path('pin/', views.user_pin, name='user_pin'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('logout/', views.user_logout, name='logout'),

    # ============ PARTNER AUTHENTICATION (PIN-BASED) ============
    path('partner/login/', views.partner_login, name='partner_login'),
    path('partner/pin/', views.partner_pin, name='partner_pin'),
    path('partner/complete-profile/', views.partner_complete_profile, name='partner_complete_profile'),
    path('partner/dashboard/', views.partner_dashboard, name='partner_dashboard'),
    path('partner/referral-link/', views.partner_referral_link, name='partner_referral_link'),

    # ============ LISTING PARTNER AUTHENTICATION (PIN-BASED) ============
    path('vendor/login/', views.listing_partner_login, name='listing_partner_login'),
    path('vendor/pin/', views.listing_partner_pin, name='listing_partner_pin'),
    path('vendor/complete-profile/', views.listing_partner_complete_profile, name='listing_partner_complete_profile'),
    path('vendor/dashboard/', views.listing_partner_dashboard, name='listing_partner_dashboard'),
    path('vendor/redemptions/', views.listing_partner_redemptions, name='listing_partner_redemptions'),

    # ============ USER DASHBOARD & FEATURES ============
    path('dashboard/', views.dashboard, name='dashboard'),
    path('scan/', views.scan_pack, name='scan_pack'),
    path('redeem/<int:reward_id>/', views.redeem_reward_htmx, name='redeem_reward'),
    path('referral/', views.referral_page, name='referral_page'),
    path('redemptions/', views.user_redemptions, name='user_redemptions'),

    # ============ POINT TRANSFERS ============
    path('transfer/', views.transfer_points, name='transfer_points'),
    path('transfer/history/', views.transfer_history, name='transfer_history'),
    path('transfer/cancel-invite/<int:invite_id>/', views.cancel_invite, name='cancel_invite'),

    # ============ SHOP FEATURES ============
    path('shop/verify/', views.shop_verify_redemption, name='shop_verify_redemption'),
    path('shops/', views.shop_finder, name='shop_finder'),
    path('shops/<int:shop_id>/', views.shop_detail, name='shop_detail'),

    # ============ PRODUCT CATALOG ============
    path('products/', views.product_catalog, name='product_catalog'),
    path('products/redeem/<int:product_id>/', views.redeem_product, name='redeem_product'),

    # ============ LISTING PARTNER PRODUCT MANAGEMENT ============
    path('vendor/products/add/', views.add_product, name='add_product'),
    path('vendor/products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('vendor/redemptions/', views.view_redemptions, name='view_redemptions'),

    # ============ CHALLENGES ============
    path('challenges/', views.challenges_list, name='challenges_list'),
    path('challenges/<int:challenge_id>/', views.challenge_detail, name='challenge_detail'),
    path('challenges/<int:challenge_id>/enter/', views.enter_challenge, name='enter_challenge'),
    path('challenges/<int:challenge_id>/winners/', views.challenge_winners, name='challenge_winners'),
    path('challenges/<int:challenge_id>/live-draw/', views.challenge_live_draw, name='challenge_live_draw'),
    path('challenges/<int:challenge_id>/select-winners-ajax/', views.challenge_select_winners_ajax,
         name='challenge_select_winners_ajax'),
    path('challenges/<int:challenge_id>/live-stream/', views.public_challenge_live_stream,
         name='public_challenge_live_stream'),
    path('challenges/<int:challenge_id>/status-test/', views.challenge_status_test, name='challenge_status_test'),
    path('my-challenges/', views.my_challenges, name='my_challenges'),

    # ============ TEA ESTATES COLLECTION ============
    path('collection/', views.my_collection, name='my_collection'),
    path('collection/card/<int:card_id>/', views.card_detail, name='card_detail'),
    path('collection/reveal/<int:scan_id>/', views.card_reveal, name='card_reveal'),
    path('collection/complete/<int:collection_id>/', views.claim_collection_reward, name='claim_collection_reward'),
    path('gifts/create/<int:card_id>/', views.create_card_gift, name='create_card_gift'),
    path('gifts/claim/<str:token>/', views.claim_card_gift, name='claim_card_gift'),
    
    # ============ TEAM COLLECTION (Group Mode) ============
    path('teams/', views.team_collection_home, name='team_collection_home'),
    path('teams/create/', views.create_team, name='create_team'),
    path('teams/join/', views.join_team, name='join_team'),
    path('teams/<int:team_id>/', views.team_dashboard, name='team_dashboard'),
    path('teams/<int:team_id>/contribute/<int:card_id>/', views.contribute_to_team, name='contribute_to_team'),
    
    # ============ REWARDS ============
    path('rewards/', views.rewards, name='rewards'),
]

