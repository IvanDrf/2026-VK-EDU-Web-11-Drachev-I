from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.templatetags.static import static

from .validators import validate_avatar_size


def avatar_upload_path(instance, filename):
    return f"avatars/{uuid4().hex}{Path(filename).suffix.lower()}"


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name="profile", verbose_name="Пользователь")
    avatar = models.ImageField(
        "Аватар", upload_to=avatar_upload_path, blank=True,
        validators=[FileExtensionValidator(["png", "jpg", "jpeg"]), validate_avatar_size],
    )

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return self.user.username

    def avatar_url(self):
        return self.avatar.url if self.avatar else static("img/user.png")
