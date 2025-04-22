from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import Account, AccountPassword, Query

class AccountPasswordInline(admin.TabularInline):
    model = Account.passwords.through
    extra = 0
    verbose_name = "Password History"
    verbose_name_plural = "Password History"
    
class QueryInline(admin.TabularInline):
    model = Account.queries.through
    extra = 0
    verbose_name = "Query"
    verbose_name_plural = "Queries"

@admin.register(AccountPassword)
class AccountPasswordAdmin(admin.ModelAdmin):
    list_display = ('masked_value', 'created_at')
    search_fields = ('value',)
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def masked_value(self, obj):
        if obj.value:
            # Show only the first and last character, mask the rest
            return f"{obj.value[:1]}{'*' * (len(obj.value) - 2)}{obj.value[-1:]}" if len(obj.value) > 2 else "****"
        return "None"
    masked_value.short_description = "Password"

@admin.register(Query)
class QueryAdmin(admin.ModelAdmin):
    list_display = ('value', 'created_at')
    search_fields = ('value',)
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

@admin.register(Account)
class AccountAdmin(UserAdmin):
    list_display = ('email', 'username', 'get_full_name_display', 'phone', 'display_avatar', 
                    'is_active', 'is_staff', 'is_admin', 'is_subscribed', 'created_at')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone')
    readonly_fields = ('created_at', 'updated_at', 'display_avatar')
    ordering = ('-created_at',)
    
    filter_horizontal = ()
    list_filter = ('is_admin', 'is_active', 'is_staff', 'is_subscribed', 'gender', 'created_at')
    
    fieldsets = (
        ('Account Credentials', {'fields': ('email', 'username', 'password')}),
        ('Personal Information', {'fields': ('first_name', 'last_name', 'other_names', 'gender', 'phone', 'details')}),
        ('Avatar', {'fields': ('display_avatar',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_admin', 'is_superuser')}),
        ('Subscription', {'fields': ('is_subscribed', 'subscribed_on')}),
        ('Important Dates', {'fields': ('created_at', 'updated_at', 'last_login')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_admin'),
        }),
    )
    
    inlines = [AccountPasswordInline, QueryInline]
    
    def get_full_name_display(self, obj):
        return obj.get_full_name
    get_full_name_display.short_description = 'Full Name'
    
    def display_avatar(self, obj):
        return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', obj.get_avatar)
    display_avatar.short_description = 'Avatar'
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)
    
    def save_model(self, request, obj, form, change):
        # If this is a new user or password has changed, save the password to history
        if not change or 'password' in form.changed_data:
            super().save_model(request, obj, form, change)
            # Create password history entry after saving
            if obj.password:  # Only if password is set
                new_password = AccountPassword.objects.create(value=obj.password)
                obj.passwords.add(new_password)
        else:
            super().save_model(request, obj, form, change)