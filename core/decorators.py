from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse


def login_required_for_post(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        handler = login_required(view) if request.method == "POST" else view
        return handler(request, *args, **kwargs)
    return wrapped


def json_endpoint(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.method != "POST":
            response = JsonResponse({"error": "Используйте метод POST."}, status=405)
            response["Allow"] = "POST"
            return response
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Войдите, чтобы выполнить действие.", "login_url": reverse("login")}, status=401)
        return view(request, *args, **kwargs)
    return wrapped
