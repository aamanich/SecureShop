from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect, HttpResponse
from django.core.paginator import Paginator
from apps.main.models import Product, Payment
import stripe
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Sum, Avg
from django.db.models.functions import TruncDay, TruncMonth
from django.contrib.admin.views.decorators import staff_member_required
import paypalrestsdk, json
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from django.db.models.functions import ExtractHour


stripe.api_key = settings.STRIPE_SECRET_KEY


def home(request):
    products = Product.objects.filter(available=True).order_by('-created')[:4]
    return render(request, 'main/home.html', {'products': products})

def test(request):
    return render(request, 'main/dashboard.html')

def products(request):
    products = Product.objects.filter(available=True)
    
    # Pagination
    paginator = Paginator(products, 8)  # Show 8 products per page
    page_number = request.GET.get('page', 1)
    products = paginator.get_page(page_number)
    
    return render(
        request,
        'main/products.html',
        {
            'products': products,
        }
    )

def product(request, slug):
    product = get_object_or_404(Product, slug=slug, available=True)
    other_products = Product.objects.filter(available=True).exclude(id=product.id)[:4]
    return render(
        request,
        'main/product.html',
        {'product': product, 'other_products': other_products}
    )

def payment_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    context = {
        'product': product,
        'stripe_key': settings.STRIPE_PUBLISHABLE_KEY
    }
    return render(request, 'main/payment.html', context)

@csrf_exempt
def create_checkout_session(request, product_id):
    """Create a Stripe checkout session for payment processing"""
    product = get_object_or_404(Product, id=product_id)
    
    # Create Stripe checkout session
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': product.name,
                        },
                        'unit_amount': int(product.price * 100),  # Stripe requires amount in cents
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=request.build_absolute_uri('/payment/success/'),
            cancel_url=request.build_absolute_uri('/payment/cancel/'),
        )
        
        # Record payment attempt for analytics
        Payment.objects.create(
            transaction_id=checkout_session.id,
            amount=product.price,
            status='pending',
            payment_method='card',
            product_id=str(product.id)
        )
        
        return JsonResponse({'id': checkout_session.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            # Update payment record
            payment = Payment.objects.get(transaction_id=session.id)
            payment.status = 'completed'
            payment.customer_email = session.customer_details.email
            payment.customer_country = session.customer_details.address.country
            payment.save()
        # Handle cancelation
        elif event['type'] == 'checkout.session.async_payment_failed':
            session = event['data']['object']
            
            # Update payment record
            payment = Payment.objects.get(transaction_id=session.id)
            payment.status = 'failed'
            payment.save()
        elif event['type'] == 'checkout.session.expired':
            session = event['data']['object']
            
            # Update payment record
            payment = Payment.objects.get(transaction_id=session.id)
            payment.status = 'expired'
            payment.save()
            
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def payment_success(request):
    """Display payment success page"""
    return render(request, 'main/payment_success.html')

def payment_cancel(request):
    return render(request, 'main/payment_cancel.html')

@csrf_exempt
def create_checkout_session(request, product_id):
    product = Product.objects.get(id=product_id)
    
    # Create Stripe checkout session
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': product.name,
                        },
                        'unit_amount': int(product.price * 100),  # Stripe requires amount in cents
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=request.build_absolute_uri('/payment/success/'),
            cancel_url=request.build_absolute_uri('/payment/cancel/'),
        )
        
        # Record payment attempt for analytics
        Payment.objects.create(
            transaction_id=checkout_session.id,
            amount=product.price,
            status='pending',
            payment_method='card',
            product_id=str(product.id)
        )
        
        return JsonResponse({'id': checkout_session.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            # Update payment record
            payment = Payment.objects.get(transaction_id=session.id)
            payment.status = 'completed'
            payment.customer_email = session.customer_details.email
            payment.customer_country = session.customer_details.address.country
            payment.save()
            
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@staff_member_required
def payment_analytics(request):
    """Display payment analytics dashboard for admin users"""
    
    # Daily revenue for the last 30 days
    daily_revenue = Payment.objects.filter(
        status='completed'
    ).annotate(
        day=TruncDay('created_at')
    ).values('day').annotate(
        revenue=Sum('amount'),
        count=Count('id')
    ).order_by('day')
    
    # Monthly revenue
    monthly_revenue = Payment.objects.filter(
        status='completed'
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        revenue=Sum('amount'),
        count=Count('id')
    ).order_by('month')
    
    # Payment method breakdown
    payment_methods = Payment.objects.values('payment_method').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-count')
    
    # Country breakdown
    countries = Payment.objects.filter(
        status='completed'
    ).values('customer_country').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total')
    
    # Success rate
    total_payments = Payment.objects.count()
    successful_payments = Payment.objects.filter(status='completed').count()
    success_rate = (successful_payments / total_payments) * 100 if total_payments > 0 else 0
    
    # Recent payments
    recent_payments = Payment.objects.all().order_by('-created_at')[:10]
    
    # Add Payment Status Distribution
    payment_status = Payment.objects.values('status').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-count')
    
    context = {
        'daily_revenue': json.dumps(list(daily_revenue), cls=DjangoJSONEncoder),
        'monthly_revenue': json.dumps(list(monthly_revenue), cls=DjangoJSONEncoder),
        'payment_methods': json.dumps(list(payment_methods), cls=DjangoJSONEncoder),
        'payment_status': json.dumps(list(payment_status), cls=DjangoJSONEncoder),  # Add this line
        'countries': json.dumps(list(countries), cls=DjangoJSONEncoder),
        'success_rate': success_rate,
        'total_revenue': Payment.objects.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0,
        'total_payments': total_payments,
        'recent_payments': recent_payments,
    }
    
    return render(request, 'main/payment_analytics.html', context)


# Configure PayPal SDK
paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,  # "live" for production
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_SECRET
})

def create_paypal_payment(request, product_id):
    """Create a PayPal payment for the product"""
    product = get_object_or_404(Product, id=product_id)
    
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"
        },
        "redirect_urls": {
            "return_url": request.build_absolute_uri('/payment/paypal/execute/'),
            "cancel_url": request.build_absolute_uri('/payment/cancel/')
        },
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": product.name,
                    "sku": f"product-{product.id}",
                    "price": str(product.price),
                    "currency": "USD",
                    "quantity": 1
                }]
            },
            "amount": {
                "total": str(product.price),
                "currency": "USD"
            },
            "description": f"Payment for {product.name}"
        }]
    })
    
    if payment.create():
        # Record payment attempt for analytics
        payment_record = Payment.objects.create(
            transaction_id=payment.id,
            amount=product.price,
            status='pending',
            payment_method='paypal',
            product_id=str(product.id)
        )
        
        # Extract approval URL
        for link in payment.links:
            if link.rel == "approval_url":
                approval_url = link.href
                return JsonResponse({'approval_url': approval_url})
    
    return JsonResponse({'error': 'Failed to create payment'}, status=400)

def execute_paypal_payment(request):
    """Execute PayPal payment after user approval"""
    payment_id = request.GET.get('paymentId')
    payer_id = request.GET.get('PayerID')
    
    payment = paypalrestsdk.Payment.find(payment_id)
    
    if payment.execute({"payer_id": payer_id}):
        # Update payment record
        payment_record = Payment.objects.get(transaction_id=payment_id)
        payment_record.status = 'completed'
        payment_record.save()
        
        return redirect('payment_success')
    else:
        return redirect('payment_cancel')

@staff_member_required
def live_payment_monitor(request):
    """Display real-time payment monitoring dashboard"""
    # Get recent payments
    recent_payments = Payment.objects.all().order_by('-created_at')[:20]
    
    context = {
        'recent_payments': recent_payments,
    }
    
    return render(request, 'main/live_monitor.html', context)

def get_payment_updates(request):
    """AJAX endpoint for getting payment updates"""
    if not request.user.is_staff:
        return HttpResponse(status=403)
        
    # Get payments since the last check
    last_check = request.GET.get('since')
    if last_check:
        payments = Payment.objects.filter(created_at__gt=last_check).order_by('-created_at')
    else:
        payments = Payment.objects.all().order_by('-created_at')[:5]
    
    payment_data = []
    for payment in payments:
        payment_data.append({
            'id': payment.id,
            'transaction_id': payment.transaction_id,
            'amount': float(payment.amount),
            'status': payment.status,
            'payment_method': payment.payment_method,
            'created_at': payment.created_at.isoformat(),
        })
    
    return JsonResponse({'payments': payment_data})

@staff_member_required
def payment_today_view(request):
    """Render the today's payment summary page"""
    return render(request, 'main/today_summary.html')


@staff_member_required
def payment_today_summary_api(request):
    """API endpoint for today's payment summary data"""
    today = timezone.now().date()
    
    # Get all payments for today
    today_payments = Payment.objects.filter(created_at__date=today)
    
    # Get basic metrics
    payment_count = today_payments.count()
    completed_payments = today_payments.filter(status='completed')
    completed_count = completed_payments.count()
    
    # Calculate metrics
    total_revenue = completed_payments.aggregate(total=Sum('amount'))['total'] or 0
    success_rate = (completed_count / payment_count * 100) if payment_count > 0 else 0
    avg_transaction = completed_payments.aggregate(avg=Avg('amount'))['avg'] or 0
    
    # Get payment methods breakdown
    methods_data = today_payments.values('payment_method').annotate(
        count=Count('id')
    ).order_by('-count')
    
    method_labels = [item['payment_method'] for item in methods_data]
    method_counts = [item['count'] for item in methods_data]
    
    # Get status breakdown
    status_counts = today_payments.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    status_data = {
        'completed': 0,
        'pending': 0,
        'failed': 0
    }
    
    for item in status_counts:
        status = item['status'].lower()
        if status in status_data:
            status_data[status] = item['count']
    
    # Get hourly transaction data
    hourly_data = [0] * 24
    
    hourly_counts = today_payments.annotate(
        hour=ExtractHour('created_at')
    ).values('hour').annotate(
        count=Count('id')
    ).order_by('hour')
    
    for entry in hourly_counts:
        hour = entry['hour']
        if 0 <= hour < 24:  # Ensure hour is valid
            hourly_data[hour] = entry['count']
    
    # Format hourly labels in a Windows-compatible way
    hourly_labels = []
    for hour in range(24):
        # Format hour as "01:00", "02:00", etc.
        hourly_labels.append(f"{hour:02d}:00")
    
    return JsonResponse({
        'count': payment_count,
        'revenue': float(total_revenue),
        'success_rate': float(success_rate),
        'average': float(avg_transaction),
        'methods': {
            'labels': method_labels,
            'data': method_counts
        },
        'status': status_data,
        'hourly': {
            'labels': hourly_labels,
            'data': hourly_data
        }
    })
