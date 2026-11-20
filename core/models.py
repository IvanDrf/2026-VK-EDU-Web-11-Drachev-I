from django.conf import settings
from django.db import models
from django.templatetags.static import static


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name="profile", verbose_name="Пользователь")
    avatar = models.FileField("Аватар", upload_to="avatars/", blank=True)

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return self.user.username

    def avatar_url(self):
        return self.avatar.url if self.avatar else static("img/user.png")
