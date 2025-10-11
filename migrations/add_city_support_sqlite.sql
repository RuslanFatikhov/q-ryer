-- Миграция: Добавление поддержки нескольких городов (SQLite)
-- Дата: 2025-10-10

-- Добавить поле city_id в таблицу users
ALTER TABLE users ADD COLUMN city_id VARCHAR(50) DEFAULT 'almaty';

-- Добавить поле city_id в таблицу orders
ALTER TABLE orders ADD COLUMN city_id VARCHAR(50) DEFAULT 'almaty';

-- Создать индексы
CREATE INDEX IF NOT EXISTS idx_users_city ON users(city_id);
CREATE INDEX IF NOT EXISTS idx_orders_city ON orders(city_id);

-- Для restaurants, buildings и restricted_zones
-- Проверим существуют ли эти таблицы, если да - добавим city_id
