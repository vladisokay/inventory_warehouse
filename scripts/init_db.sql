BEGIN;

-- 1. Создание таблиц

-- Создание таблицы ролей
CREATE TABLE IF NOT EXISTS roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    permissions TEXT
);

-- Создание таблицы пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    role_id INTEGER NOT NULL,
    FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE RESTRICT
);

-- Создание таблицы категорий товаров
CREATE TABLE IF NOT EXISTS product_categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

-- Создание таблицы поставщиков
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id SERIAL PRIMARY KEY,
    supplier_name VARCHAR(100) UNIQUE NOT NULL,
    contact_info VARCHAR(255),
    address VARCHAR(255)
);

-- Создание таблицы товаров
CREATE TABLE IF NOT EXISTS products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    category_id INTEGER NOT NULL,
    FOREIGN KEY (category_id) REFERENCES product_categories(category_id) ON DELETE RESTRICT
);

-- Создание таблицы для отображения информации по складу в клиентском приложении
CREATE TABLE IF NOT EXISTS inventory (
    product_id INTEGER PRIMARY KEY,
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    last_updated TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    incoming_this_month INTEGER NOT NULL DEFAULT 0 CHECK (incoming_this_month >= 0),
    outgoing_this_month INTEGER NOT NULL DEFAULT 0 CHECK (outgoing_this_month >= 0),
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

-- Создание таблицы транзакций
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id SERIAL PRIMARY KEY,
    transaction_date TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    transaction_type VARCHAR(10) NOT NULL CHECK (transaction_type IN ('Приход', 'Расход')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    product_id INTEGER NOT NULL,
    supplier_id INTEGER,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id) ON DELETE SET NULL
);


-- Вставка начальных ролей, если они еще не существуют
INSERT INTO roles (role_name, permissions) VALUES
('Администратор', '{"can_add_product": true, "can_delete_product": true, "can_update_quantity": true, "can_manage_categories": true, "can_manage_suppliers": true}'),
('Работник', '{"can_add_product": true, "can_delete_product": false, "can_update_quantity": true, "can_manage_categories": false, "can_manage_suppliers": false}')
ON CONFLICT (role_name) DO NOTHING;

-- 3. Представления


-- Представление для склада товаров
CREATE VIEW view_product_inventory AS
SELECT
    p.product_id,
    p.name AS product_name,
    pc.category_name,
    p.description,
    p.price,
    i.quantity,
    i.last_updated,
    i.incoming_this_month,
    i.outgoing_this_month,
    s.supplier_name
FROM
    products p
JOIN
    product_categories pc ON p.category_id = pc.category_id
JOIN
    inventory i ON p.product_id = i.product_id
LEFT JOIN
    transactions t ON p.product_id = t.product_id AND t.transaction_type = 'Приход'
LEFT JOIN
    suppliers s ON t.supplier_id = s.supplier_id;

-- Представление для деталей транзакций
CREATE VIEW view_transaction_details AS
SELECT
    t.transaction_id,
    t.transaction_date,
    t.transaction_type,
    t.quantity,
    p.name AS product_name,
    s.supplier_name,
    s.contact_info,
    s.address
FROM
    transactions t
JOIN
    products p ON t.product_id = p.product_id
LEFT JOIN
    suppliers s ON t.supplier_id = s.supplier_id;

-- Представление для разрешений пользователей
CREATE VIEW view_user_permissions AS
SELECT
    u.user_id,
    u.username,
    r.role_name,
    r.permissions
FROM
    users u
JOIN
    roles r ON u.role_id = r.role_id;

-- 4. Создание Функций

-- Функция триггер для обновления склада при транзакции
CREATE OR REPLACE FUNCTION update_inventory_on_transaction()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.transaction_type = 'Приход' THEN
        UPDATE inventory
        SET
            quantity = quantity + NEW.quantity,
            incoming_this_month = incoming_this_month + NEW.quantity,
            last_updated = CURRENT_TIMESTAMP
        WHERE product_id = NEW.product_id;
    ELSIF NEW.transaction_type = 'Расход' THEN
        UPDATE inventory
        SET
            quantity = quantity - NEW.quantity,
            outgoing_this_month = outgoing_this_month + NEW.quantity,
            last_updated = CURRENT_TIMESTAMP
        WHERE product_id = NEW.product_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Функция триггер для проверки достаточного количества при расходе
CREATE OR REPLACE FUNCTION check_inventory_before_withdrawal()
RETURNS TRIGGER AS $$
DECLARE
    current_quantity INTEGER;
BEGIN
    IF NEW.transaction_type = 'Расход' THEN
        SELECT quantity INTO current_quantity FROM inventory WHERE product_id = NEW.product_id;
        IF current_quantity < NEW.quantity THEN
            RAISE EXCEPTION 'Недостаточно товара на складе для транзакции расхода. Продукт ID: %, Запрашиваемое количество: %, Доступно: %',
                NEW.product_id, NEW.quantity, current_quantity;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Функция для получения прав пользователя
CREATE OR REPLACE FUNCTION get_user_permissions(p_user_id INTEGER)
RETURNS TABLE (
    role_name VARCHAR,
    permissions TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.role_name,
        r.permissions
    FROM
        users u
    JOIN
        roles r ON u.role_id = r.role_id
    WHERE
        u.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Функция для расчета общей стоимости товара на складе
CREATE OR REPLACE FUNCTION calculate_total_inventory_value()
RETURNS NUMERIC AS $$
DECLARE
    total_value NUMERIC := 0;
BEGIN
    SELECT SUM(p.price * i.quantity) INTO total_value
    FROM
        products p
    JOIN
        inventory i ON p.product_id = i.product_id;
    RETURN total_value;
END;
$$ LANGUAGE plpgsql;

-- 5. Процедуры

-- Процедура для добавления нового товара
CREATE OR REPLACE PROCEDURE add_new_product(
    p_name VARCHAR,
    p_description TEXT,
    p_price NUMERIC,
    p_category_id INTEGER,
    p_initial_quantity INTEGER,
    p_supplier_id INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_product_id INTEGER;
BEGIN
    INSERT INTO products (name, description, price, category_id)
    VALUES (p_name, p_description, p_price, p_category_id)
    RETURNING product_id INTO v_product_id;

    INSERT INTO inventory (product_id, quantity, incoming_this_month, outgoing_this_month)
    VALUES (v_product_id, p_initial_quantity, p_initial_quantity, 0);

    INSERT INTO transactions (product_id, transaction_type, quantity, supplier_id)
    VALUES (v_product_id, 'Приход', p_initial_quantity, p_supplier_id);
END;
$$;

-- Процедура для записи транзакции
CREATE OR REPLACE PROCEDURE record_transaction(
    p_product_id INTEGER,
    p_transaction_type VARCHAR,
    p_quantity INTEGER,
    p_supplier_id INTEGER DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO transactions (product_id, transaction_type, quantity, supplier_id)
    VALUES (p_product_id, p_transaction_type, p_quantity, p_supplier_id);
END;
$$;

-- Процедура для удаления товара
CREATE OR REPLACE PROCEDURE delete_product(p_product_id INTEGER)
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM transactions WHERE product_id = p_product_id;

    DELETE FROM inventory WHERE product_id = p_product_id;

    DELETE FROM products WHERE product_id = p_product_id;
END;
$$;

-- Процедура для удаления категории
CREATE OR REPLACE PROCEDURE delete_category(p_category_id INTEGER)
LANGUAGE plpgsql
AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM products WHERE category_id = p_category_id) THEN
        RAISE EXCEPTION 'Невозможно удалить категорию, так как существуют товары, принадлежащие ей.';
    END IF;

    DELETE FROM product_categories WHERE category_id = p_category_id;
END;
$$;

-- Процедура для добавления новой категории
CREATE OR REPLACE PROCEDURE add_category_proc(p_category_name VARCHAR, p_description TEXT)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO product_categories (category_name, description)
    VALUES (p_category_name, p_description);
END;
$$;

-- Процедура для добавления нового поставщика
CREATE OR REPLACE PROCEDURE add_supplier_proc(p_supplier_name VARCHAR, p_contact_info VARCHAR, p_address VARCHAR)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO suppliers (supplier_name, contact_info, address)
    VALUES (p_supplier_name, p_contact_info, p_address);
END;
$$;

-- Процедура для удаления поставщика
CREATE OR REPLACE PROCEDURE delete_supplier(p_supplier_id INTEGER)
LANGUAGE plpgsql
AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM transactions WHERE supplier_id = p_supplier_id) THEN
        RAISE EXCEPTION 'Невозможно удалить поставщика, так как существуют транзакции, связанные с ним.';
    END IF;
    DELETE FROM suppliers WHERE supplier_id = p_supplier_id;
END;
$$;

-- 6. Создание триггеров

-- Триггер для обновления склада после вставки транзакции
CREATE TRIGGER trg_update_inventory
AFTER INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION update_inventory_on_transaction();

-- Триггер для проверки склада перед вставкой транзакции расхода
CREATE TRIGGER trg_check_inventory
BEFORE INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION check_inventory_before_withdrawal();

COMMIT;

