/* Курсовая работа по дисциплине "Базы данных"
 Тема: Разработка базы данных для автоматизации вокзала (Вариант 4)
 Студент: Никишев Наиль
*/

-- Очистка старых данных (чтобы скрипт можно было запускать без ошибок)
DROP VIEW IF EXISTS v_station_train_stats;
DROP VIEW IF EXISTS v_moscow_stations;
DROP TABLE IF EXISTS route_data CASCADE;
DROP TABLE IF EXISTS routes CASCADE;
DROP TABLE IF EXISTS staff CASCADE;
DROP TABLE IF EXISTS trains CASCADE;
DROP TABLE IF EXISTS crews CASCADE;
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS train_types CASCADE;
DROP TABLE IF EXISTS stations CASCADE;

-- =========================================================================
-- 1. НЕЗАВИСИМЫЕ ТАБЛИЦЫ (СПРАВОЧНИКИ)
-- =========================================================================

CREATE TABLE stations (
    station_id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    inn VARCHAR(12) UNIQUE CHECK (length(inn) IN (10, 12)),
    address TEXT DEFAULT 'Адрес не указан',
    staff_count INT DEFAULT 0 
);

CREATE TABLE train_types (
    train_type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE positions (
    position_id SERIAL PRIMARY KEY,
    position_name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE crews (
    crew_id SERIAL PRIMARY KEY,
    crew_name VARCHAR(100) NOT NULL UNIQUE
);

-- 2. ЗАВИСИМЫЕ ТАБЛИЦЫ


CREATE TABLE trains (
    train_id SERIAL PRIMARY KEY,
    station_id INT NOT NULL REFERENCES stations(station_id),
    train_type_id INT NOT NULL REFERENCES train_types(train_type_id),
    name VARCHAR(100) NOT NULL
);

CREATE TABLE staff (
    inn VARCHAR(12) PRIMARY KEY CHECK (length(inn) = 12),
    station_id INT NOT NULL REFERENCES stations(station_id),
    full_name VARCHAR(200) NOT NULL,
    position_id INT NOT NULL REFERENCES positions(position_id),
    crew_id INT REFERENCES crews(crew_id)
);

CREATE TABLE routes (
    route_id SERIAL PRIMARY KEY,
    owner_station_id INT NOT NULL REFERENCES stations(station_id),
    train_id INT NOT NULL REFERENCES trains(train_id),
    departure_station_id INT NOT NULL REFERENCES stations(station_id),
    arrival_station_id INT NOT NULL REFERENCES stations(station_id),
    departure_time TIMESTAMP NOT NULL,
    arrival_time TIMESTAMP NOT NULL,
    crew_id INT REFERENCES crews(crew_id),
    CHECK (arrival_time > departure_time)
);

CREATE TABLE route_data (
    route_id INT NOT NULL REFERENCES routes(route_id) ON DELETE CASCADE,
    stop_number INT NOT NULL,
    station_id INT NOT NULL REFERENCES stations(station_id),
    arrival_time TIMESTAMP,
    departure_time TIMESTAMP,
    PRIMARY KEY (route_id, stop_number),
    CHECK (departure_time > arrival_time)
);

-- 3. ИНДЕКСЫ
CREATE INDEX idx_trains_station ON trains(station_id);
CREATE INDEX idx_staff_station ON staff(station_id);
CREATE INDEX idx_routes_departure_time ON routes(departure_time);

-- 4. ТРИГГЕРЫ 
CREATE OR REPLACE FUNCTION trg_update_station_staff_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE stations SET staff_count = staff_count + 1 WHERE station_id = NEW.station_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE stations SET staff_count = staff_count - 1 WHERE station_id = OLD.station_id;
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' AND NEW.station_id != OLD.station_id THEN
        UPDATE stations SET staff_count = staff_count - 1 WHERE station_id = OLD.station_id;
        UPDATE stations SET staff_count = staff_count + 1 WHERE station_id = NEW.station_id;
        RETURN NEW;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER maintain_staff_count
AFTER INSERT OR UPDATE OR DELETE ON staff
FOR EACH ROW EXECUTE FUNCTION trg_update_station_staff_count();

-- 5. ПРОЕКЦИИ (VIEW)
CREATE VIEW v_known_address_stations AS
SELECT station_id, name, inn, address 
FROM stations 
WHERE address != 'Адрес не указан';

CREATE VIEW v_station_train_stats AS
SELECT s.name AS station_name, COUNT(t.train_id) AS total_trains
FROM stations s
JOIN trains t ON s.station_id = t.station_id
GROUP BY s.name
HAVING COUNT(t.train_id) >= 2;

-- 6. ТЕСТОВЫЕ ДАННЫЕ 
INSERT INTO stations (name, inn, address) VALUES 
('Казанский вокзал', '1234567890', 'Москва, Комсомольская пл., 2'),
('Ижевский вокзал', '0987654321', 'Ижевск, ул. Дружбы, 16');

INSERT INTO train_types (type_name) VALUES ('Скорый'), ('Пригородный электропоезд');
INSERT INTO positions (position_name) VALUES ('Машинист'), ('Проводник'), ('Диспетчер');
INSERT INTO crews (crew_name) VALUES ('Бригада №1'), ('Бригада №2');

INSERT INTO trains (station_id, train_type_id, name) VALUES 
(1, 1, 'Сапсан'),
(1, 2, 'Ласточка'),
(2, 1, 'Италмас');

INSERT INTO staff (inn, station_id, full_name, position_id, crew_id) VALUES 
('111111111111', 1, 'Иванов И.И.', 1, 1),
('222222222222', 1, 'Петров П.П.', 2, 1),
('333333333333', 2, 'Сидоров С.С.', 1, 2);



-- Очистка таблиц перед заполнением 
TRUNCATE TABLE route_data, routes, staff, trains, crews, positions, train_types, stations RESTART IDENTITY CASCADE;

-- 1. ЗАПОЛНЕНИЕ НЕЗАВИСИМЫХ ТАБЛИЦ


INSERT INTO stations (name, inn, address) VALUES
('Ижевский вокзал', '1831000010', 'г. Ижевск, ул. Дружбы, 16'),
('Казанский вокзал', '7708000010', 'г. Москва, Комсомольская пл., 2'),
('Екатеринбург-Пассажирский', '6670000010', 'г. Екатеринбург, ул. Вокзальная, 22'),
('Казань-Пассажирская', '1655000010', 'г. Казань, Привокзальная пл., 1');

INSERT INTO train_types (type_name) VALUES
('Скорый'), 
('Пассажирский'), 
('Фирменный'), 
('Скоростной электропоезд');

INSERT INTO positions (position_name) VALUES
('Машинист'), 
('Помощник машиниста'), 
('Проводник'), 
('Начальник поезда'), 
('Диспетчер');

INSERT INTO crews (crew_name) VALUES
('Бригада №1 "Удмуртия"'), 
('Бригада №2 "Столица"'), 
('Бригада №3 "Урал"');

-- 2. ЗАПОЛНЕНИЕ ЗАВИСИМЫХ ТАБЛИЦ

INSERT INTO trains (station_id, train_type_id, name) VALUES
(1, 3, 'Италмас'),      -- 1: Ижевск, Фирменный
(2, 4, 'Ласточка'),     -- 2: Москва, Скоростной
(3, 3, 'Демидовский'),  -- 3: Екб, Фирменный
(2, 1, 'Сапсан');       -- 4: Москва, Скорый

-- при добавлении сработает триггер и автоматически обновит поле staff_count в таблице stations
INSERT INTO staff (inn, station_id, full_name, position_id, crew_id) VALUES
('183100000001', 1, 'Николаев Иван Сергеевич', 1, 1),
('183100000002', 1, 'Смирнова Анна Игоревна', 3, 1),
('183100000003', 1, 'Петров Алексей Ильич', 5, NULL), -- диспетчер без бригады
('770800000001', 2, 'Иванов Сергей Петрович', 1, 2),
('770800000002', 2, 'Кузнецова Елена Владимировна', 4, 2),
('667000000001', 3, 'Морозов Дмитрий Алексеевич', 1, 3);

-- Добавляем маршруты (Время прибытия строго больше времени отправления)
INSERT INTO routes (owner_station_id, train_id, departure_station_id, arrival_station_id, departure_time, arrival_time, crew_id) VALUES
(1, 1, 1, 2, '2026-05-01 17:40:00', '2026-05-02 10:20:00', 1), -- Ижевск -> Москва (поезд Италмас)
(3, 3, 3, 4, '2026-05-01 10:00:00', '2026-05-01 22:30:00', 3); -- Екб -> Казань (поезд Демидовский)

INSERT INTO route_data (route_id, stop_number, station_id, arrival_time, departure_time) VALUES
-- Остановка для маршрута 1 (Ижевск -> Москва)
(1, 1, 4, '2026-05-01 22:15:00', '2026-05-01 22:45:00'), -- Транзит через Казань
-- Остановка для маршрута 2 (Екб -> Казань)
(2, 1, 1, '2026-05-01 15:30:00', '2026-05-01 16:10:00'); -- Транзит через Ижевск






-- еще несколько должностей для массовки
INSERT INTO positions (position_name) VALUES 
('Старший диспетчер'), ('Техник путей'), ('Обходчик'), ('Кассир')
ON CONFLICT DO NOTHING;

-- добавим сотрудников на Ижевский вокзал (station_id = 1)
INSERT INTO staff (inn, station_id, full_name, position_id, crew_id) VALUES
('183100000010', 1, 'Зайцев Максим Петрович', 2, 1),
('183100000011', 1, 'Волков Артем Денисович', 2, 1),
('183100000012', 1, 'Медведева Дарья Павловна', 3, 1),
('183100000013', 1, 'Соколов Игорь Олегович', 4, 1),
('183100000014', 1, 'Морозова Светлана Юрьевна', 5, NULL),
('183100000015', 1, 'Павлов Кирилл Викторович', 1, NULL);

-- добавим больше поездов
INSERT INTO trains (station_id, train_type_id, name) VALUES
(1, 2, 'Пригородный Ижевск-Балезино'),
(1, 2, 'Пригородный Ижевск-Воткинск'),
(2, 4, 'Невский Экспресс'),
(4, 1, 'Восток');

-- маршруты из Ижевска
INSERT INTO routes (owner_station_id, train_id, departure_station_id, arrival_station_id, departure_time, arrival_time, crew_id) VALUES
(1, 5, 1, 3, '2026-05-03 07:00:00', '2026-05-03 11:30:00', 1),
(1, 6, 1, 4, '2026-05-03 14:20:00', '2026-05-03 16:50:00', 1),
(1, 1, 1, 2, '2026-05-04 17:40:00', '2026-05-05 10:20:00', 1);

-- маршруты из Москвы
INSERT INTO routes (owner_station_id, train_id, departure_station_id, arrival_station_id, departure_time, arrival_time, crew_id) VALUES
(2, 2, 2, 4, '2026-05-03 09:00:00', '2026-05-03 13:00:00', 2),
(2, 7, 2, 3, '2026-05-03 23:30:00', '2026-05-04 08:15:00', 2);

-- добавим данных в route_data (остановки), чтобы отчеты по станциям были полными
INSERT INTO route_data (route_id, stop_number, station_id, arrival_time, departure_time) VALUES
(3, 1, 4, '2026-05-03 09:15:00', '2026-05-03 09:30:00'),
(4, 1, 1, '2026-05-03 15:45:00', '2026-05-03 16:00:00');



























TRUNCATE TABLE route_data, routes, staff, trains, crews, positions, train_types, stations RESTART IDENTITY CASCADE;

INSERT INTO train_types (type_name) VALUES 
('Скорый'), ('Пассажирский'), ('Фирменный'), ('Скоростной'), ('Пригородный'), ('Международный');

INSERT INTO positions (position_name) VALUES 
('Машинист'), ('Помощник машиниста'), ('Проводник'), ('Начальник поезда'), 
('Диспетчер'), ('Старший кассир'), ('Техник путей'), ('Обходчик'), ('Охранник');

-- Генерируем 20 вокзалов 
INSERT INTO stations (name, inn, address)
SELECT 
    t.val || ' вокзал', 
    (1000000000 + t.idx)::text, 
    'г. ' || t.val || ', ул. Железнодорожная, ' || t.idx
FROM unnest(ARRAY['Ижевск', 'Москва', 'Казань', 'Екатеринбург', 'Санкт-Петербург', 'Новосибирск', 
                   'Нижний Новгород', 'Челябинск', 'Самара', 'Омск', 'Ростов-на-Дону', 'Уфа', 
                   'Красноярск', 'Пермь', 'Воронеж', 'Волгоград', 'Краснодар', 'Саратов', 'Тюмень', 'Тольятти']) 
WITH ORDINALITY AS t(val, idx);

-- 3. Генерируем 50 бригад
INSERT INTO crews (crew_name)
SELECT 'Бригада №' || i FROM generate_series(1, 50) AS i;

-- 4. Генерируем 100 поездов
INSERT INTO trains (station_id, train_type_id, name)
SELECT 
    (random() * 19 + 1)::int, 
    (random() * 5 + 1)::int,  
    'Поезд №' || (100 + i)
FROM generate_series(1, 100) AS i;

-- генерируем 300 сотрудников
INSERT INTO staff (inn, station_id, full_name, position_id, crew_id)
SELECT 
    (100000000000 + i)::text, -- ИНН 12 знаков
    (random() * 19 + 1)::int, -- Случайный вокзал
    (ARRAY['Иванов', 'Петров', 'Сидоров', 'Смирнов', 'Кузнецов', 'Попов'])[floor(random()*6)+1] || ' ' || 
    (ARRAY['А.', 'Б.', 'В.', 'Д.', 'Е.', 'М.'])[floor(random()*6)+1] || ' ' || 
    (ARRAY['Иванович', 'Петрович', 'Сергеевич', 'Алексеевич'])[floor(random()*4)+1],
    (random() * 8 + 1)::int, -- Случайная должность
    CASE WHEN random() > 0.2 THEN (random() * 49 + 1)::int ELSE NULL END -- 80% в бригадах
FROM generate_series(1, 300) AS i;

--  генерируем 200 маршрутов
INSERT INTO routes (owner_station_id, train_id, departure_station_id, arrival_station_id, departure_time, arrival_time, crew_id)
SELECT 
    (random() * 19 + 1)::int, -- Владелец
    (random() * 99 + 1)::int, -- Поезд
    (random() * 19 + 1)::int, -- Откуда
    (random() * 19 + 1)::int, -- Куда
    CURRENT_TIMESTAMP + (i || ' hours')::interval, -- Время отпр
    CURRENT_TIMESTAMP + (i + 5 || ' hours')::interval, -- Время приб
    (random() * 49 + 1)::int  -- Бригада
FROM generate_series(1, 200) AS i;

-- генерируем остановки (route_data) для первых 100 маршрутов
INSERT INTO route_data (route_id, stop_number, station_id, arrival_time, departure_time)
SELECT 
    i, 
    1, 
    (random() * 19 + 1)::int,
    CURRENT_TIMESTAMP + (i + 2 || ' hours')::interval,
    CURRENT_TIMESTAMP + (i + 2.5 || ' hours')::interval
FROM generate_series(1, 100) AS i;







SELECT setval('stations_station_id_seq', (SELECT MAX(station_id) FROM stations));