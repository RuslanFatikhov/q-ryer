-- Миграция: Добавление поддержки нескольких городов
-- Дата: 2025-10-10

-- Добавить поле city_id в таблицу users (город по умолчанию для игрока)
ALTER TABLE users 
ADD COLUMN city_id VARCHAR(50) DEFAULT 'almaty';

-- Добавить индекс для быстрого поиска по городам
CREATE INDEX idx_users_city ON users(city_id);

-- Добавить поле city_id в таблицу orders
ALTER TABLE orders 
ADD COLUMN city_id VARCHAR(50) DEFAULT 'almaty';

-- Добавить индекс
CREATE INDEX idx_orders_city ON orders(city_id);

-- Добавить поле city_id в таблицу restaurants
ALTER TABLE restaurants 
ADD COLUMN city_id VARCHAR(50) DEFAULT 'almaty';

CREATE INDEX idx_restaurants_city ON restaurants(city_id);

-- Добавить поле city_id в таблицу buildings
ALTER TABLE buildings 
ADD COLUMN city_id VARCHAR(50) DEFAULT 'almaty';

CREATE INDEX idx_buildings_city ON buildings(city_id);

-- Добавить поле city_id в таблицу restricted_zones
ALTER TABLE restricted_zones 
ADD COLUMN city_id VARCHAR(50) DEFAULT 'almaty';

CREATE INDEX idx_restricted_zones_city ON restricted_zones(city_id);

-- Комментарии для ясности
COMMENT ON COLUMN users.city_id IS 'ID города игрока по умолчанию';
COMMENT ON COLUMN orders.city_id IS 'ID города для этого заказа';
COMMENT ON COLUMN restaurants.city_id IS 'ID города ресторана';
COMMENT ON COLUMN buildings.city_id IS 'ID города здания';
COMMENT ON COLUMN restricted_zones.city_id IS 'ID города запретной зоны';
