from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.csrf import csrf_failure as django_csrf_failure
from django.views.decorators.http import require_http_methods

from .forms import LoginForm, ProfileForm, SignupForm


class LoginView(auth_views.LoginView):
    template_name = "core/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("index")


@require_http_methods(["GET", "POST"])
def signup(request):
    form = SignupForm(request.POST if request.method == "POST" else None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        auth_login(request, form.save())
        return redirect("index")
    return render(request, "core/signup.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    form = ProfileForm(request.POST if request.method == "POST" else None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Профиль сохранён.")
        return redirect("profile")
    return render(request, "core/profile.html", {"form": form})


def csrf_failure(request, reason=""):
    if request.path.startswith("/api/"):
        return JsonResponse({"error": "Не удалось проверить CSRF-токен. Обновите страницу и попробуйте ещё раз."}, status=403)
    return django_csrf_failure(request, reason=reason)
