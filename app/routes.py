# -*- coding: utf-8 -*-
"""
Маршруты страниц для симулятора курьера.
"""

from flask import Blueprint, render_template, current_app

pages_bp = Blueprint("pages", __name__)

@pages_bp.route("/")
def index():
    """Главная страница - перенаправление на вход"""
    return render_template("login.html")

@pages_bp.route("/register")
def register():
    """Страница регистрации"""
    return render_template("register.html")

@pages_bp.route("/login")
def login():
    """Страница входа"""
    return render_template("login.html")

@pages_bp.route("/game")
def game():
    """Страница игры"""
    mapbox_token = current_app.config.get("MAPBOX_ACCESS_TOKEN")
    return render_template("game.html", mapbox_token=mapbox_token)

@pages_bp.route("/terms")
def terms():
    """Страница пользовательского соглашения"""
    return render_template("terms.html")


@pages_bp.route("/privacy")
def privacy():
    """Политика обработки персональных данных"""
    return render_template("privacy.html")

@pages_bp.route("/faq")
def faq():
    """Часто задаваемые вопросы"""
    return render_template("faq.html")
