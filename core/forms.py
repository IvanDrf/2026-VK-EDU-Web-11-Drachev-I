from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.validators import FileExtensionValidator
from django.db import transaction

from .models import Profile
from .validators import validate_avatar_size

User = get_user_model()


class StyledFormMixin(forms.BaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", "form-control")
            field.widget.attrs.setdefault("aria-describedby", f"id_{name}_helptext id_{name}_errors")


class AvatarField(forms.ImageField):
    def __init__(self, **kwargs):
        super().__init__(
            label="Аватарка", required=False,
            validators=[FileExtensionValidator(["png", "jpg", "jpeg"]), validate_avatar_size],
            widget=forms.FileInput(attrs={"accept": "image/png,image/jpeg"}),
            help_text="PNG или JPEG, до 2 МБ.", **kwargs,
        )

    def to_python(self, data):
        if data:
            validate_avatar_size(data)
        image = super().to_python(data)
        if image and getattr(image, "image").format not in {"PNG", "JPEG"}:
            raise forms.ValidationError("Загрузите изображение PNG или JPEG.")
        return image


class UserFieldsMixin(forms.ModelForm):
    def clean_username(self):
        username = self.cleaned_data["username"]
        existing = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("Пользователь с таким логином уже существует.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Этот email уже используется.")
        return email


class LoginForm(StyledFormMixin, AuthenticationForm):
    username = forms.CharField(label="Логин", max_length=150,
                               widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}))


class SignupForm(UserFieldsMixin, StyledFormMixin, UserCreationForm):
    email = forms.EmailField(label="Email", max_length=254,
                             widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    first_name = forms.CharField(label="Имя", max_length=150,
                                 widget=forms.TextInput(attrs={"autocomplete": "given-name"}))
    avatar = AvatarField()

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "password1", "password2", "avatar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = "От 8 до 128 символов. Используйте буквы и цифры."
        self.fields["password2"].label = "Повторите пароль"
        self.fields["password2"].help_text = "Повторите пароль, от 8 до 128 символов."

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            if avatar := self.cleaned_data.get("avatar"):
                profile.avatar = avatar
                profile.save(update_fields=["avatar"])
        return user


class ProfileForm(UserFieldsMixin, StyledFormMixin, forms.ModelForm):
    email = forms.EmailField(label="Email", max_length=254)
    avatar = AvatarField()

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "avatar")
        labels = {"username": "Ник", "first_name": "Имя"}

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            if avatar := self.cleaned_data.get("avatar"):
                profile.avatar = avatar
                profile.save(update_fields=["avatar"])
        return user
