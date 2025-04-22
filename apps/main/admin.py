from django.contrib import admin
from .models import Product, Payment


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'rating', 'available', 'created']
    list_filter = ['available', 'created', 'updated']
    list_editable = ['price', 'available']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'amount', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['transaction_id', 'customer_email']
    readonly_fields = ['transaction_id', 'created_at', 'updated_at']
    fieldsets = [
        ('Payment Information', {
            'fields': ('transaction_id', 'amount', 'currency', 'status', 'payment_method')
        }),
        ('Customer Information', {
            'fields': ('customer_email', 'customer_country', 'product_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    ]
    
    def has_add_permission(self, request):
        # Prevent manual creation of payment records
        return False
