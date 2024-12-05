-- Таблица ролей
CREATE TABLE roles
(
    role_id     serial PRIMARY KEY,
    role_name   varchar(50) NOT NULL UNIQUE,
    permissions varchar(255)
);

ALTER TABLE roles OWNER TO admin;

-- Таблица категорий продуктов
CREATE TABLE product_categories
(
    category_id   serial PRIMARY KEY,
    category_name varchar(100) NOT NULL UNIQUE,
    description   text
);

ALTER TABLE product_categories OWNER TO admin;

-- Таблица поставщиков
CREATE TABLE suppliers
(
    supplier_id   serial PRIMARY KEY,
    supplier_name varchar(100) NOT NULL,
    contact_info  varchar(255),
    address       varchar(255)
);

ALTER TABLE suppliers OWNER TO admin;

-- Таблица пользователей
CREATE TABLE users
(
    user_id       serial PRIMARY KEY,
    username      varchar(50) NOT NULL UNIQUE,
    password_hash varchar(255) NOT NULL,
    role_id       integer REFERENCES roles(role_id)
);

ALTER TABLE users OWNER TO admin;

-- Таблица продуктов
CREATE TABLE products
(
    product_id  serial PRIMARY KEY,
    name        varchar(100) NOT NULL,
    description text,
    price       numeric(10, 2) NOT NULL,
    category_id integer REFERENCES product_categories(category_id)
);

ALTER TABLE products OWNER TO admin;

-- Таблица инвентаря
CREATE TABLE inventory
(
    inventory_id        serial PRIMARY KEY,
    product_id          integer REFERENCES products(product_id),
    quantity            integer NOT NULL,
    last_updated        timestamp DEFAULT CURRENT_TIMESTAMP,
    incoming_this_month integer DEFAULT 0 NOT NULL,
    outgoing_this_month integer DEFAULT 0 NOT NULL
);

ALTER TABLE inventory OWNER TO admin;

-- Таблица транзакций
CREATE TABLE transactions
(
    transaction_id   serial PRIMARY KEY,
    product_id       integer NOT NULL REFERENCES products(product_id),
    transaction_type varchar(50) NOT NULL,
    quantity         integer NOT NULL,
    transaction_date timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    supplier_id      integer REFERENCES suppliers(supplier_id)
);

ALTER TABLE transactions OWNER TO admin;

-- Вставка начальных данных в таблицы

INSERT INTO roles (role_name, permissions) VALUES
('Администратор', 'Все права'),
('Работник', 'Редактирование данных'),
('Пользователь', 'Просмотр данных');

INSERT INTO product_categories (category_name, description) VALUES
('Электроника', 'Все электронные устройства'),
('Мебель', 'Домашняя и офисная мебель'),
('Канцелярия', 'Товары для офиса и учебы'),
('Бытовая техника', 'Все виды бытовой техники'),
('Одежда', 'Мужская и женская одежда');

INSERT INTO suppliers (supplier_name, contact_info, address) VALUES
('Вася Пупкин', 'info@supplierA.com', 'г. Москва, ул. Ленина, д. 10'),
('Гоша Гнилов', '+7-495-123-4567', 'г. Санкт-Петербург, ул. Невский проспект, д. 5'),
('Петр Иванов', 'contact@techsuppliers.ru', 'г. Екатеринбург, ул. Ленина, д. 12'),
('Оля Ковальчук', 'support@furnitureworld.com', 'г. Нижний Новгород, ул. Октябрьская, д. 15'),
('Ирина Павлова', 'sales@clothesstore.ru', 'г. Казань, ул. Мира, д. 20');


INSERT INTO products (name, description, price, category_id) VALUES
('Телевизор 4K', '42 дюйма, 4K, Smart TV', 45000.00, 1),
('Микроволновка Samsung', 'Микроволновая печь, 25 литров', 15000.00, 4),
('Стул офисный', 'Эргономичный офисный стул', 5000.00, 2),
('Карандаши', 'Набор из 12 карандашей', 100.00, 3),
('Футболка Nike', 'Футболка с логотипом Nike', 2500.00, 5),
('Ноутбук HP', '15.6 дюймов, процессор i5, 8GB RAM', 70000.00, 1),
('Холодильник Bosch', 'Холодильник с морозильной камерой', 30000.00, 4),
('Кофемашина Philips', 'Автоматическая кофемашина', 25000.00, 4),
('Рабочий стол IKEA', 'Простой рабочий стол из древесины', 8000.00, 2),
('Пенал', 'Пластиковый пенал для канцелярии', 150.00, 3);

INSERT INTO inventory (product_id, quantity, last_updated, incoming_this_month, outgoing_this_month) VALUES
(1, 10, CURRENT_TIMESTAMP, 5, 3),
(2, 15, CURRENT_TIMESTAMP, 3, 2),
(3, 50, CURRENT_TIMESTAMP, 20, 10),
(4, 100, CURRENT_TIMESTAMP, 50, 30),
(5, 30, CURRENT_TIMESTAMP, 15, 5),
(6, 5, CURRENT_TIMESTAMP, 2, 0),
(7, 8, CURRENT_TIMESTAMP, 5, 1),
(8, 12, CURRENT_TIMESTAMP, 7, 3),
(9, 20, CURRENT_TIMESTAMP, 10, 5),
(10, 40, CURRENT_TIMESTAMP, 30, 25);

INSERT INTO transactions (product_id, transaction_type, quantity, transaction_date, supplier_id) VALUES
(1, 'Приход', 10, CURRENT_TIMESTAMP, 1),
(2, 'Приход', 15, CURRENT_TIMESTAMP, 3),
(3, 'Расход', 10, CURRENT_TIMESTAMP, NULL),
(4, 'Приход', 50, CURRENT_TIMESTAMP, 4),
(5, 'Приход', 20, CURRENT_TIMESTAMP, 5),
(6, 'Приход', 5, CURRENT_TIMESTAMP, 1),
(7, 'Расход', 3, CURRENT_TIMESTAMP, NULL),
(8, 'Приход', 12, CURRENT_TIMESTAMP, 2),
(9, 'Приход', 8, CURRENT_TIMESTAMP, 3),
(10, 'Расход', 30, CURRENT_TIMESTAMP, NULL);



