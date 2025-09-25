from flask import Blueprint, render_template, current_app

pages_bp = Blueprint("pages", __name__)

@pages_bp.route("/")
def index():
    return render_template("login.html")

@pages_bp.route("/game")
def game():
    mapbox_token = current_app.config.get("MAPBOX_ACCESS_TOKEN")
    return render_template("game.html", mapbox_token=mapbox_token)
