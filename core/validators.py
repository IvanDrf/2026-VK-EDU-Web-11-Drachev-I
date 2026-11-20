from django.core.exceptions import ValidationError

MAX_AVATAR_SIZE = 2 * 1024 * 1024


def validate_avatar_size(value):
    if value.size > MAX_AVATAR_SIZE:
        raise ValidationError("Размер аватарки не должен превышать 2 МБ.")
