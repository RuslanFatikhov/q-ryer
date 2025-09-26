from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_cors import CORS
import os

# Инициализация расширений
db = SQLAlchemy()
socketio = SocketIO()

def create_app(config_name=None):
    """
    Factory функция для создания Flask приложения
    """
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"), static_folder=os.path.join(os.path.dirname(__file__), "..", "static"))

    # Загружаем конфигурацию
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    from app.config import DevelopmentConfig, ProductionConfig, TestingConfig

    config_map = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }

    app.config.from_object(config_map.get(config_name, DevelopmentConfig))

    # Инициализируем расширения
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")
    CORS(app)

    # Регистрируем blueprints
    from app.api.auth import auth_bp
    from app.api.player import player_bp
    from app.api.admin import admin_bp
    from app.routes import pages_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(player_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(pages_bp)

    # Регистрируем SocketIO обработчики
    from app.socketio_handlers import game_events
    # Обработчики регистрируются через декораторы при импорте
    # (game_events регистрируются через декораторы)

    # Создаем таблицы в базе данных
    with app.app_context():
        db.create_all()
        from app.utils.data_loader import load_initial_data
        load_initial_data()

    # Добавляем базовые маршруты
    @app.route("/api/health")
    def health_check():
        try:
            db.session.execute(db.text("SELECT 1"))
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}, 500

    return app
