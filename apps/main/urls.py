from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.home, name='home'),
    path('test/', views.test, name='test'),
    path('products/', views.products, name='products'),
    path('products/<slug:slug>/', views.product, name='product'),
    
    # Payment URLs
    path('payment/<int:product_id>/', views.payment_view, name='payment'),
    path('create-checkout-session/<int:product_id>/', views.create_checkout_session, name='create_checkout_session'),
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),
    
    # PayPal URLs
    path('payment/paypal/<int:product_id>/', views.create_paypal_payment, name='create_paypal_payment'),
    path('payment/paypal/execute/', views.execute_paypal_payment, name='execute_paypal_payment'),
    
    # Analytics
    path('payment/analytics/', views.payment_analytics, name='payment_analytics'),
    
    # Add these to your urlpatterns
    path('payment/live-monitor/', views.live_payment_monitor, name='live_payment_monitor'),
    path('payment/updates/', views.get_payment_updates, name='payment_updates'),
    path('payment/today/', views.payment_today_view, name='payment_today'),
    path('payment/today-summary/', views.payment_today_summary_api, name='payment_today_summary_api'),
]
