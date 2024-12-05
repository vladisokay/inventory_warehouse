import os
import subprocess
from datetime import datetime

from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, jwt_required
from sqlalchemy import text

from back.auth import auth_bp
from back.db import db, migrate
from back.utils import role_required


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/database_name'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = 'your_secret_key'

    db.init_app(app)
    migrate.init_app(app, db)
    jwt = JWTManager(app)

    with app.app_context():
        # Создаем все таблицы
        db.create_all()

        # Создаем роли по умолчанию, если их нет
        default_roles = [
            {'role_id': 1, 'role_name': 'Администратор', 'permissions': 'all'},
            {'role_id': 2, 'role_name': 'Работник', 'permissions': 'edit'},
            {'role_id': 3, 'role_name': 'Пользователь', 'permissions': 'view'}
        ]

        for role_data in default_roles:
            existing_role = db.session.execute(
                text("SELECT * FROM roles WHERE role_id = :role_id"), {'role_id': role_data['role_id']}
            ).fetchall()

            if not existing_role:
                db.session.execute(
                    text(
                        "INSERT INTO roles (role_id, role_name, permissions) VALUES (:role_id, :role_name, :permissions)"),
                    role_data
                )

        db.session.commit()

    app.register_blueprint(auth_bp, url_prefix='/auth')


    @app.route('/categories', methods=['GET'])
    @jwt_required()
    @role_required([1, 2])  # Администратор или работник
    def get_categories():
        try:
            categories = db.session.execute(
                text("SELECT category_id, category_name, description FROM product_categories")
            ).fetchall()

            category_list = []
            for category in categories:
                category_list.append({
                    'category_id': category.category_id,
                    'category_name': category.category_name,
                    'description': category.description
                })

            return jsonify(category_list), 200
        except Exception as e:
            return jsonify({"message": "Ошибка на сервере"}), 500

    @app.route('/suppliers', methods=['GET'])
    @jwt_required()
    @role_required([1, 2])
    def get_suppliers():
        try:
            suppliers = db.session.execute(
                text("SELECT supplier_id, supplier_name, contact_info, address FROM suppliers")
            ).fetchall()

            # Преобразуем в список словарей
            supplier_list = []
            for supplier in suppliers:
                supplier_list.append({
                    'supplier_id': supplier.supplier_id,
                    'supplier_name': supplier.supplier_name,
                    'contact_info': supplier.contact_info,
                    'address': supplier.address
                })

            return jsonify(supplier_list), 200

        except Exception as e:
            return jsonify({"message": f"Ошибка при получении поставщиков: {str(e)}"}), 500

    @app.route('/inventory', methods=['GET'])
    @jwt_required()
    def get_inventory():
        try:
            # Выполняем основной запрос для инвентаря
            inventory_items = db.session.execute(
                text("""
                    SELECT i.product_id, p.name, p.description, p.price, i.quantity, i.last_updated,
                           i.incoming_this_month, i.outgoing_this_month, c.category_name, s.supplier_name
                    FROM inventory i
                    JOIN products p ON i.product_id = p.product_id
                    LEFT JOIN product_categories c ON p.category_id = c.category_id
                    LEFT JOIN transactions t ON t.product_id = p.product_id
                    LEFT JOIN suppliers s ON t.supplier_id = s.supplier_id
                    WHERE t.transaction_date = (
                        SELECT MAX(transaction_date)
                        FROM transactions
                        WHERE product_id = p.product_id
                    )
                """)
            ).mappings().fetchall()

            result = []

            for item in inventory_items:
                last_updated = item['last_updated'].strftime('%Y-%m-%d %H:%M:%S') if item[
                    'last_updated'] else "Не указана"

                result.append({
                    'product_id': item['product_id'],
                    'name': item['name'],
                    'description': item['description'],
                    'price': float(item['price']),
                    'quantity': item['quantity'],
                    'last_updated': last_updated,
                    'incoming_this_month': item['incoming_this_month'],
                    'outgoing_this_month': item['outgoing_this_month'],
                    'category_name': item['category_name'] if item['category_name'] else "Не указана",
                    'supplier_name': item['supplier_name'] if item['supplier_name'] else "Не указан"
                })

            return jsonify(result), 200
        except Exception as e:
            print(f"Error on server: {e}")
            return jsonify({"message": "Server error"}), 500

    @app.route('/inventory', methods=['POST'])
    @jwt_required()
    @role_required([1, 2])  # Администратор или работник
    def add_product():
        try:
            data = request.get_json()
            name = data['name']
            description = data.get('description', '')
            price = float(data['price'])
            quantity = int(data['quantity'])
            category_id = int(data['category_id'])
            supplier_id = int(data['supplier_id'])

            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Проверяем существование категории и поставщика
            category = db.session.execute(
                text("SELECT * FROM product_categories WHERE category_id = :category_id"),
                {'category_id': category_id}
            ).fetchall()

            supplier = db.session.execute(
                text("SELECT * FROM suppliers WHERE supplier_id = :supplier_id"),
                {'supplier_id': supplier_id}
            ).fetchall()

            if not category:
                return jsonify({"message": "Категория не найдена"}), 404
            if not supplier:
                return jsonify({"message": "Поставщик не найден"}), 404

            # Проверяем, существует ли уже товар с таким названием и категорией
            existing_product = db.session.execute(
                text("""
                    SELECT product_id FROM products WHERE name = :name AND category_id = :category_id
                """),
                {'name': name, 'category_id': category_id}
            ).fetchone()

            if existing_product:
                product_id = existing_product[0]  # Получаем ID существующего товара

                # Проверяем наличие товара в inventory
                existing_inventory = db.session.execute(
                    text("""
                        SELECT * FROM inventory WHERE product_id = :product_id
                    """),
                    {'product_id': product_id}
                ).fetchall()

                if existing_inventory:
                    # Если товар уже есть в инвентаре, обновляем его количество
                    db.session.execute(
                        text("""
                                                UPDATE inventory
                                                SET quantity = quantity + :quantity,
                                                    incoming_this_month = incoming_this_month + :quantity,
                                                    last_updated = :current_time
                                                WHERE product_id = :product_id
                                            """),
                        {'product_id': product_id, 'quantity': quantity, 'current_time': current_time}
                    )
                else:
                    # Если товара нет в inventory, добавляем его
                    db.session.execute(
                        text("""
                                               INSERT INTO inventory (product_id, quantity, incoming_this_month, last_updated)
                                               VALUES (:product_id, :quantity, :quantity, :current_time)
                                           """),
                        {'product_id': product_id, 'quantity': quantity, 'current_time': current_time}
                    )

            else:
                # Если товара нет, добавляем его в таблицу products
                db.session.execute(
                    text("""
                        INSERT INTO products (name, description, price, category_id)
                        VALUES (:name, :description, :price, :category_id)
                    """),
                    {'name': name, 'description': description, 'price': price, 'category_id': category_id}
                )

                # Получаем ID добавленного товара
                product_id_result = db.session.execute(
                    text("""
                        SELECT product_id FROM products WHERE name = :name AND price = :price
                    """),
                    {'name': name, 'price': price}
                ).fetchone()

                if product_id_result:
                    product_id = product_id_result[0]
                else:
                    return jsonify({"message": "Товар не найден после добавления"}), 404

                db.session.execute(
                    text("""
                                   INSERT INTO inventory (product_id, quantity, incoming_this_month, last_updated)
                                   VALUES (:product_id, :quantity, :quantity, :current_time)
                               """),
                    {'product_id': product_id, 'quantity': quantity, 'current_time': current_time}
                )

            # Добавляем запись в таблицу transactions (приход)
            db.session.execute(
                text("""
                    INSERT INTO transactions (product_id, transaction_type, quantity, transaction_date, supplier_id)
                    VALUES (:product_id, 'Приход', :quantity, NOW(), :supplier_id)
                """),
                {'product_id': product_id, 'quantity': quantity, 'supplier_id': supplier_id}
            )

            db.session.commit()

            return jsonify({"message": "Товар успешно добавлен в инвентарь"}), 201
        except Exception as e:
            return jsonify({"message": "Ошибка на сервере"}), 500

    @app.route('/inventory/<int:product_id>', methods=['DELETE'])
    @jwt_required()
    @role_required([1])  # Только Администратор
    def delete_product(product_id):
        try:
            # Удаляем записи из transactions
            db.session.execute(
                text("DELETE FROM transactions WHERE product_id = :product_id"),
                {'product_id': product_id}
            )

            # Удаляем товар из таблицы inventory
            db.session.execute(
                text("DELETE FROM inventory WHERE product_id = :product_id"),
                {'product_id': product_id}
            )

            # Удаляем товар из таблицы products
            db.session.execute(
                text("DELETE FROM products WHERE product_id = :product_id"),
                {'product_id': product_id}
            )

            db.session.commit()

            return jsonify({"message": "Товар успешно удален"}), 200
        except Exception as e:
            return jsonify({"message": "Ошибка на сервере"}), 500

    @app.route('/inventory/<int:product_id>/quantity', methods=['PATCH'])
    @jwt_required()
    @role_required([1, 2])  # Администратор или работник
    def update_quantity(product_id):
        try:
            data = request.get_json()
            action = data.get('action')
            amount = int(data.get('amount', 0))

            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if action not in ['increase', 'decrease']:
                return jsonify({"message": "Некорректное действие. Используйте 'increase' или 'decrease'."}), 400
            if amount <= 0:
                return jsonify({"message": "Количество должно быть положительным числом."}), 400

            # Получаем текущую запись из inventory
            inventory_item = db.session.execute(
                text("SELECT * FROM inventory WHERE product_id = :product_id"),
                {'product_id': product_id}
            ).mappings().fetchone()

            if not inventory_item:
                return jsonify({"message": "Товар не найден"}), 404

            current_quantity = inventory_item['quantity']
            incoming_this_month = inventory_item['incoming_this_month']
            outgoing_this_month = inventory_item['outgoing_this_month']

            # Логика для увеличения или уменьшения количества
            if action == 'increase':
                # Увеличиваем количество
                new_quantity = current_quantity + amount
                new_incoming = incoming_this_month + amount  # Увеличиваем приход за месяц
                db.session.execute(
                    text("""
                        UPDATE inventory 
                        SET quantity = :new_quantity, incoming_this_month = :new_incoming, last_updated = :current_time
                        WHERE product_id = :product_id
                    """),
                    {'new_quantity': new_quantity, 'new_incoming': new_incoming, 'current_time': current_time, 'product_id': product_id, }
                )
                transaction_type = 'Приход'
            elif action == 'decrease':
                # Уменьшаем количество
                if amount > current_quantity:
                    return jsonify({"message": "Недостаточно товара для уменьшения"}), 400
                new_quantity = current_quantity - amount
                new_outgoing = outgoing_this_month + amount  # Увеличиваем отгрузку за месяц
                db.session.execute(
                    text("""
                        UPDATE inventory 
                        SET quantity = :new_quantity, outgoing_this_month = :new_outgoing, last_updated = :current_time
                        WHERE product_id = :product_id
                    """),
                    {'new_quantity': new_quantity, 'new_outgoing': new_outgoing, 'current_time': current_time, 'product_id': product_id}
                )
                transaction_type = 'Расход'

            # Добавляем запись в таблицу transactions
            db.session.execute(
                text("""
                    INSERT INTO transactions (product_id, transaction_type, quantity, transaction_date)
                    VALUES (:product_id, :transaction_type, :quantity, NOW())
                """),
                {'product_id': product_id, 'transaction_type': transaction_type, 'quantity': amount}
            )

            db.session.commit()

            return jsonify({"message": "Количество успешно обновлено"}), 200
        except Exception as e:
            return jsonify({"message": "Ошибка на сервере"}), 500

    @app.route('/categories', methods=['POST'])
    @jwt_required()
    @role_required([1, 2])  # Администратор или работник
    def add_category():
        try:
            data = request.get_json()
            category_name = data['category_name']
            description = data.get('description', '')

            existing_category = db.session.execute(
                text("SELECT * FROM product_categories WHERE category_name = :category_name"),
                {'category_name': category_name}
            ).fetchone()

            if existing_category:
                return jsonify({"message": "Категория с таким названием уже существует"}), 400

            db.session.execute(
                text("""
                    INSERT INTO product_categories (category_name, description)
                    VALUES (:category_name, :description)
                """),
                {'category_name': category_name, 'description': description}
            )
            db.session.commit()

            return jsonify({"message": "Категория успешно добавлена"}), 201
        except Exception as e:
            return jsonify({"message": "Ошибка на сервере"}), 500

    @app.route('/categories/<int:category_id>', methods=['DELETE'])
    @jwt_required()
    @role_required([1])  # Только Администратор
    def delete_category(category_id):
        try:
            category = db.session.execute(
                text("SELECT * FROM product_categories WHERE category_id = :category_id"),
                {'category_id': category_id}
            ).fetchone()

            if not category:
                return jsonify({"message": "Категория не найдена"}), 404

            db.session.execute(
                text("DELETE FROM product_categories WHERE category_id = :category_id"),
                {'category_id': category_id}
            )
            db.session.commit()

            return jsonify({"message": "Категория успешно удалена"}), 200
        except Exception as e:
            return jsonify({"message": "Ошибка на сервере"}), 500

    @app.route('/suppliers', methods=['POST'])
    @jwt_required()
    @role_required([1, 2])  # Администратор или работник
    def add_supplier():
        try:
            data = request.get_json()
            supplier_name = data['supplier_name']
            contact_info = data.get('contact_info', '')
            address = data.get('address', '')

            existing_supplier = db.session.execute(
                text("SELECT * FROM suppliers WHERE supplier_name = :supplier_name"),
                {'supplier_name': supplier_name}
            ).fetchone()

            if existing_supplier:
                return jsonify({"message": "Поставщик с таким названием уже существует"}), 400

            db.session.execute(
                text("""
                    INSERT INTO suppliers (supplier_name, contact_info, address)
                    VALUES (:supplier_name, :contact_info, :address)
                """),
                {'supplier_name': supplier_name, 'contact_info': contact_info, 'address': address}
            )
            db.session.commit()

            return jsonify({"message": "Поставщик успешно добавлен"}), 201
        except Exception as e:
            return jsonify({"message": "Ошибка на сервере"}), 500

    @app.route('/suppliers/<int:supplier_id>', methods=['DELETE'])
    @jwt_required()
    @role_required([1])  # Только Администратор
    def delete_supplier(supplier_id):
        try:
            supplier = db.session.execute(
                text("SELECT * FROM suppliers WHERE supplier_id = :supplier_id"),
                {'supplier_id': supplier_id}
            ).fetchone()

            if not supplier:
                return jsonify({"message": "Поставщик не найден"}), 404

            db.session.execute(
                text("DELETE FROM suppliers WHERE supplier_id = :supplier_id"),
                {'supplier_id': supplier_id}
            )
            db.session.commit()

            return jsonify({"message": "Поставщик успешно удален"}), 200
        except Exception as e:
            return jsonify({"message": "Ошибка на сервере"}), 500

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
