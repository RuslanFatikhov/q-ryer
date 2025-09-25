# -*- coding: utf-8 -*-
"""
API endpoints для админки симулятора курьера.
Управление пользователями, заказами, жалобами и настройками.
"""

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import func, desc
from app import db
from app.models import User, Order, Report
from app.utils.restaurant_helper import get_restaurants_stats
from app.utils.building_helper import get_buildings_stats
import logging
from datetime import datetime, timedelta

# Создаем blueprint
admin_bp = Blueprint('admin', __name__)

# Настройка логирования
logger = logging.getLogger(__name__)

@admin_bp.route('/users', methods=['GET'])
def get_users():
    """
    Получение списка пользователей с фильтрацией и пагинацией.
    """
    try:
        # Параметры запроса
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        status = request.args.get('status')  # online, offline, all
        search = request.args.get('search', '').strip()
        
        # Базовый запрос
        query = User.query.filter_by(is_active=True)
        
        # Фильтр по статусу
        if status == 'online':
            query = query.filter_by(is_online=True)
        elif status == 'offline':
            query = query.filter_by(is_online=False)
        
        # Поиск по имени пользователя или email
        if search:
            query = query.filter(
                db.or_(
                    User.username.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%')
                )
            )
        
        # Сортировка по активности
        query = query.order_by(desc(User.last_activity))
        
        # Пагинация
        paginated = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        users_data = []
        for user in paginated.items:
            user_dict = user.to_dict()
            user_dict['active_order'] = user.get_active_order().to_dict() if user.get_active_order() else None
            users_data.append(user_dict)
        
        return jsonify({
            'users': users_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return jsonify({'error': 'Failed to get users'}), 500

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user_details(user_id):
    """
    Получение подробной информации о пользователе.
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Основная информация
        user_data = user.to_dict()
        
        # Активный заказ
        active_order = user.get_active_order()
        user_data['active_order'] = active_order.to_dict() if active_order else None
        
        # Статистика
        user_data['statistics'] = user.get_statistics()
        
        # Последние заказы (10 штук)
        recent_orders = Order.query.filter_by(user_id=user_id).order_by(
            desc(Order.created_at)
        ).limit(10).all()
        
        user_data['recent_orders'] = [order.to_dict() for order in recent_orders]
        
        # Жалобы пользователя
        user_reports = Report.query.filter_by(user_id=user_id).order_by(
            desc(Report.created_at)
        ).limit(5).all()
        
        user_data['recent_reports'] = [report.to_dict() for report in user_reports]
        
        return jsonify(user_data)
        
    except Exception as e:
        logger.error(f"Error getting user details: {str(e)}")
        return jsonify({'error': 'Failed to get user details'}), 500

@admin_bp.route('/orders', methods=['GET'])
def get_orders():
    """
    Получение списка заказов с фильтрацией.
    """
    try:
        # Параметры запроса
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        status = request.args.get('status')  # pending, active, completed, cancelled
        user_id = request.args.get('user_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Базовый запрос
        query = Order.query
        
        # Фильтр по статусу
        if status:
            query = query.filter_by(status=status)
        
        # Фильтр по пользователю
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        # Фильтр по дате
        if date_from:
            date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(Order.created_at >= date_from_obj)
        
        if date_to:
            date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(Order.created_at <= date_to_obj)
        
        # Сортировка по дате создания
        query = query.order_by(desc(Order.created_at))
        
        # Пагинация
        paginated = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        orders_data = []
        for order in paginated.items:
            order_dict = order.to_dict()
            # Добавляем информацию о пользователе
            if order.user:
                order_dict['user_name'] = order.user.username
            orders_data.append(order_dict)
        
        return jsonify({
            'orders': orders_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting orders: {str(e)}")
        return jsonify({'error': 'Failed to get orders'}), 500

@admin_bp.route('/reports', methods=['GET'])
def get_reports():
    """
    Получение списка жалоб от пользователей.
    """
    try:
        # Параметры запроса
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        status = request.args.get('status')  # pending, in_review, resolved, dismissed
        priority = request.args.get('priority')  # low, medium, high, critical
        report_type = request.args.get('type')
        
        # Базовый запрос
        query = Report.query
        
        # Фильтры
        if status:
            query = query.filter_by(status=status)
        
        if priority:
            query = query.filter_by(priority=priority)
        
        if report_type:
            query = query.filter_by(report_type=report_type)
        
        # Сортировка: сначала по приоритету, затем по дате
        query = query.order_by(
            desc(Report.priority),
            desc(Report.created_at)
        )
        
        # Пагинация
        paginated = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        reports_data = [report.to_dict() for report in paginated.items]
        
        return jsonify({
            'reports': reports_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting reports: {str(e)}")
        return jsonify({'error': 'Failed to get reports'}), 500

@admin_bp.route('/reports/<int:report_id>/status', methods=['POST'])
def update_report_status(report_id):
    """
    Обновление статуса жалобы.
    """
    try:
        data = request.get_json()
        new_status = data.get('status')
        admin_response = data.get('admin_response')
        
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        report = Report.query.get(report_id)
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        # Обновляем статус
        success = report.update_status(new_status, admin_response)
        if not success:
            return jsonify({'error': 'Invalid status'}), 400
        
        logger.info(f"Report {report_id} status updated to {new_status}")
        
        return jsonify({
            'success': True,
            'message': 'Report status updated',
            'report': report.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error updating report status: {str(e)}")
        return jsonify({'error': 'Failed to update report status'}), 500

@admin_bp.route('/analytics/overview', methods=['GET'])
def get_analytics_overview():
    """
    Получение общей аналитики системы.
    """
    try:
        # Параметры периода
        days = int(request.args.get('days', 7))
        date_from = datetime.utcnow() - timedelta(days=days)
        
        # Статистика пользователей
        total_users = User.query.filter_by(is_active=True).count()
        online_users = User.query.filter_by(is_online=True, is_active=True).count()
        new_users_period = User.query.filter(
            User.created_at >= date_from,
            User.is_active == True
        ).count()
        
        # Статистика заказов
        total_orders = Order.query.count()
        completed_orders = Order.query.filter_by(status='completed').count()
        orders_period = Order.query.filter(Order.created_at >= date_from).count()
        
        # Статистика по периоду
        period_completed = Order.query.filter(
            Order.created_at >= date_from,
            Order.status == 'completed'
        ).count()
        
        # Средние показатели
        avg_delivery_amount = db.session.query(func.avg(Order.amount)).filter(
            Order.status == 'completed'
        ).scalar() or 0
        
        total_revenue = db.session.query(func.sum(Order.amount)).filter(
            Order.status == 'completed'
        ).scalar() or 0
        
        # Статистика жалоб
        total_reports = Report.query.count()
        pending_reports = Report.query.filter_by(status='pending').count()
        reports_period = Report.query.filter(Report.created_at >= date_from).count()
        
        # Статистика данных
        restaurants_stats = get_restaurants_stats()
        buildings_stats = get_buildings_stats()
        
        return jsonify({
            'period_days': days,
            'users': {
                'total': total_users,
                'online': online_users,
                'new_in_period': new_users_period,
                'online_percentage': round((online_users / max(total_users, 1)) * 100, 1)
            },
            'orders': {
                'total': total_orders,
                'completed': completed_orders,
                'in_period': orders_period,
                'completed_in_period': period_completed,
                'completion_rate': round((completed_orders / max(total_orders, 1)) * 100, 1)
            },
            'revenue': {
                'total': round(total_revenue, 2),
                'average_order': round(avg_delivery_amount, 2)
            },
            'reports': {
                'total': total_reports,
                'pending': pending_reports,
                'in_period': reports_period
            },
            'data': {
                'restaurants': restaurants_stats,
                'buildings': buildings_stats
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        return jsonify({'error': 'Failed to get analytics'}), 500

@admin_bp.route('/analytics/orders_by_day', methods=['GET'])
def get_orders_by_day():
    """
    Получение статистики заказов по дням.
    """
    try:
        days = int(request.args.get('days', 14))
        date_from = datetime.utcnow() - timedelta(days=days)
        
        # Запрос заказов по дням
        orders_by_day = db.session.query(
            func.date(Order.created_at).label('date'),
            func.count(Order.id).label('total'),
            func.sum(func.case([(Order.status == 'completed', 1)], else_=0)).label('completed'),
            func.sum(func.case([(Order.status == 'cancelled', 1)], else_=0)).label('cancelled')
        ).filter(
            Order.created_at >= date_from
        ).group_by(
            func.date(Order.created_at)
        ).order_by('date').all()
        
        # Форматируем данные
        chart_data = []
        for row in orders_by_day:
            chart_data.append({
                'date': row.date.isoformat(),
                'total': int(row.total),
                'completed': int(row.completed or 0),
                'cancelled': int(row.cancelled or 0)
            })
        
        return jsonify(chart_data)
        
    except Exception as e:
        logger.error(f"Error getting orders by day: {str(e)}")
        return jsonify({'error': 'Failed to get orders statistics'}), 500

@admin_bp.route('/config', methods=['GET'])
def get_system_config():
    """
    Получение текущей конфигурации системы.
    """
    try:
        config = current_app.config['GAME_CONFIG']
        
        return jsonify({
            'game_config': config,
            'app_config': {
                'debug': current_app.debug,
                'testing': current_app.testing
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting config: {str(e)}")
        return jsonify({'error': 'Failed to get config'}), 500

@admin_bp.route('/config', methods=['POST'])
def update_system_config():
    """
    Обновление конфигурации системы.
    """
    try:
        data = request.get_json()
        
        # Получаем текущую конфигурацию
        config = current_app.config['GAME_CONFIG'].copy()
        
        # Обновляемые параметры
        updatable_params = [
            'base_payment', 'pickup_fee', 'dropoff_fee', 'distance_rate',
            'on_time_bonus', 'pickup_radius', 'dropoff_radius',
            'delivery_speed_kmh', 'delivery_base_time', 'max_gps_accuracy'
        ]
        
        updated_params = []
        for param in updatable_params:
            if param in data:
                old_value = config.get(param)
                new_value = data[param]
                
                if old_value != new_value:
                    config[param] = new_value
                    updated_params.append({
                        'param': param,
                        'old_value': old_value,
                        'new_value': new_value
                    })
        
        # Применяем обновленную конфигурацию
        current_app.config['GAME_CONFIG'] = config
        
        logger.info(f"System config updated: {updated_params}")
        
        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully',
            'updated_params': updated_params,
            'new_config': config
        })
        
    except Exception as e:
        logger.error(f"Error updating config: {str(e)}")
        return jsonify({'error': 'Failed to update config'}), 500

@admin_bp.route('/system/status', methods=['GET'])
def get_system_status():
    """
    Получение статуса системы для мониторинга.
    """
    try:
        # Статус базы данных
        try:
            db.session.execute('SELECT 1')
            db_status = 'connected'
        except Exception:
            db_status = 'error'
        
        # Статус файлов данных
        import os
        data_files_status = {
            'restaurants': os.path.exists('data/restaurants.geojson'),
            'buildings': os.path.exists('data/buildings.geojson')
        }
        
        # Счетчики
        online_users = User.query.filter_by(is_online=True).count()
        active_orders = Order.query.filter_by(status='active').count()
        pending_reports = Report.query.filter_by(status='pending').count()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': db_status,
            'data_files': data_files_status,
            'counters': {
                'online_users': online_users,
                'active_orders': active_orders,
                'pending_reports': pending_reports
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500