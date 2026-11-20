from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Profile

User = get_user_model()
PASSWORD = "Violet-River-82!Cloud"


def avatar(name="photo.png", image_format="PNG"):
    stream = BytesIO()
    Image.new("RGB", (3, 3), "blue").save(stream, format=image_format)
    return SimpleUploadedFile(name, stream.getvalue(), content_type="image/png")


class AccountTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="existing", email="used@example.com", password=PASSWORD)

    def setUp(self):
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        settings_override = override_settings(MEDIA_ROOT=self.media.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def signup_data(self, **changes):
        data = {"username": "newuser", "email": "new@example.com", "first_name": "Иван",
                "password1": PASSWORD, "password2": PASSWORD}
        data.update(changes)
        return data

    def test_signup_creates_user_profile_hashed_password_and_image(self):
        response = self.client.post("/signup/", self.signup_data(avatar=avatar()))
        self.assertRedirects(response, "/")
        user = User.objects.get(username="newuser")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)
        self.assertEqual(user.first_name, "Иван")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertRegex(user.profile.avatar.name, r"^avatars/[a-f0-9]{32}\.png$")
        self.assertTrue(Path(user.profile.avatar.path).is_file())

    def test_signup_validation_preserves_text_and_creates_nothing(self):
        cases = ({"username": "bad username"}, {"username": "EXISTING"}, {"email": "bad-email"},
                 {"email": "USED@example.com"}, {"password1": "123", "password2": "123"},
                 {"password2": "different"})
        for changes in cases:
            with self.subTest(changes=changes):
                response = self.client.post("/signup/", self.signup_data(**changes))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assertEqual(response.context["form"]["first_name"].value(), "Иван")
                self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_invalid_avatar_extension_content_format_and_size(self):
        uploads = [avatar("photo.svg"), avatar("photo.png", "GIF"),
                   SimpleUploadedFile("photo.png", b"not an image", content_type="image/png"),
                   SimpleUploadedFile("photo.png", b"x" * (2 * 1024 * 1024 + 1), content_type="image/png")]
        for upload in uploads:
            with self.subTest(name=upload.name, size=upload.size):
                response = self.client.post("/signup/", self.signup_data(avatar=upload))
                self.assertIn("avatar", response.context["form"].errors)
                self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_login_next_and_rejection_of_external_redirects(self):
        response = self.client.post("/login/?next=/hot/%3Fpage%3D2", {"username": "existing", "password": PASSWORD})
        self.assertRedirects(response, "/hot/?page=2")
        for target in ("https://evil.example/", "//evil.example/", "/\\evil.example/", "javascript:alert(1)"):
            self.client.logout()
            response = self.client.post("/login/", {"username": "existing", "password": PASSWORD, "next": target})
            self.assertRedirects(response, "/")

    def test_login_error_preserves_login_and_next(self):
        response = self.client.post("/login/", {"username": "existing", "password": "wrong", "next": "/ask/"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertEqual(response.context["form"]["username"].value(), "existing")
        self.assertContains(response, 'name="next" value="/ask/"')

    def test_logout_is_post_only_and_stays_on_current_public_page(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        response = self.client.post("/logout/", {"next": "/hot/?page=2"})
        self.assertRedirects(response, "/hot/?page=2")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.client.force_login(self.user)
        self.assertRedirects(self.client.post("/logout/", {"next": "https://evil.example/"}), "/")

    def test_profile_requires_login_and_saves_only_own_data(self):
        self.assertRedirects(self.client.get("/profile/"), "/login/?next=/profile/")
        self.client.force_login(self.user)
        response = self.client.get("/profile/")
        self.assertEqual(response.context["form"]["email"].value(), "used@example.com")
        response = self.client.post("/profile/", {"username": "updated", "email": "updated@example.com",
                                                "first_name": "Новое имя", "avatar": avatar()})
        self.assertRedirects(response, "/profile/")
        self.user.refresh_from_db()
        path = self.user.profile.avatar.name
        self.assertEqual(self.user.username, "updated")
        self.assertEqual(self.user.email, "updated@example.com")
        self.assertContains(self.client.get("/"), self.user.profile.avatar.url)
        self.client.post("/profile/", {"username": "updated", "email": "updated@example.com", "first_name": "Ещё имя"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.avatar.name, path)

    def test_profile_errors_preserve_input_and_original_database_values(self):
        self.client.force_login(self.user)
        response = self.client.post("/profile/", {"username": "newnick", "email": "broken", "first_name": "Имя"})
        self.assertIn("email", response.context["form"].errors)
        self.assertEqual(response.context["form"]["username"].value(), "newnick")
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "existing")

    def test_csrf_is_required_for_login_and_logout(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/login/")
        data = {"username": "existing", "password": PASSWORD}
        self.assertEqual(client.post("/login/", data).status_code, 403)
        token = client.cookies["csrftoken"].value
        self.assertEqual(client.post("/login/", data, HTTP_X_CSRFTOKEN=token).status_code, 302)
        self.assertEqual(client.post("/logout/").status_code, 403)


class AdminProfileTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin", password=PASSWORD)
        self.client.force_login(self.admin)

    def test_admin_user_creation_does_not_create_duplicate_profile(self):
        response = self.client.post(reverse("admin:auth_user_add"), {
            "username": "admin-created", "password1": PASSWORD, "password2": PASSWORD,
            "usable_password": "true", "profile-TOTAL_FORMS": 0, "profile-INITIAL_FORMS": 0,
            "profile-MIN_NUM_FORMS": 0, "profile-MAX_NUM_FORMS": 1,
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="admin-created")
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)

    def test_all_model_admin_pages_and_profile_inline_open(self):
        from django.contrib import admin
        for model in admin.site._registry:
            prefix = f"admin:{model._meta.app_label}_{model._meta.model_name}"
            for action in ("changelist", "add"):
                with self.subTest(model=model.__name__, action=action):
                    self.assertEqual(self.client.get(reverse(f"{prefix}_{action}")).status_code, 200)
        response = self.client.get(reverse("admin:auth_user_change", args=[self.admin.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Аватар")
