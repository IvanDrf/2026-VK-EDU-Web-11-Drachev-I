from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    extra = 0
    max_num = 1
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return obj is not None and super().has_add_permission(request, obj)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "avatar")
    search_fields = ("user__username", "user__email")
    list_filter = ("user__is_active", "user__is_staff")
    list_select_related = ("user",)
    raw_id_fields = ("user",)


User = get_user_model()
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)


admin.site.site_header = "Администрирование AskHub"
admin.site.site_title = "AskHub"
