from django.shortcuts import render

# Create your views here.


def login(request):
    return render(
        request=request,
        template_name="core/login.html",
        context={"user_authenticated": False},
    )


def signup(request):
    return render(
        request=request,
        template_name="core/signup.html",
        context={"user_authenticated": False},
    )


def profile(request):
    return render(
        request=request,
        template_name="core/profile.html",
        context={
            "user_authenticated": True,
            "user": {"username": "IvanDrf", "email": "ivan@example.com"},
        },
    )
