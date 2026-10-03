from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from .forms import RegisterForm
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            messages.success(request, "You have sucessfully register!")
            login(request, user)
            return redirect("home")
        else:
            messages.error(request, "Something went wrong. Please try again.")

    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "You have successfully logged in!")
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


def landing_view(request):
    return render(request, "accounts/index.html")
# home page me analyser ke folder me banaunga q ki ye bas auth ka part hai na isliye     