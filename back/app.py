import logging

from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, jwt_required
from sqlalchemy import text

from back.auth import auth_bp
from back.db import db, migrate
from back.utils import role_required

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
            logger.error(f"Ошибка при получении категорий: {e}")
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
            logger.error(f"Ошибка при получении поставщиков: {e}")
            return jsonify({"message": f"Ошибка при получении поставщиков: {str(e)}"}), 500

    @app.route('/inventory', methods=['GET'])
    @jwt_required()
    def get_inventory():
        try:
            # Используем представление view_product_inventory для получения информации об инвентаре
            inventory_items = db.session.execute(
                text("""
                    SELECT 
                        product_id,
                        product_name AS name,
                        category_name,
                        description,
                        price,
                        quantity,
                        last_updated,
                        incoming_this_month,
                        outgoing_this_month,
                        supplier_name
                    FROM view_product_inventory
                """)
            ).mappings().fetchall()

            result = []

            for item in inventory_items:
                last_updated = item['last_updated'].strftime('%Y-%m-%d %H:%M:%S') if item['last_updated'] else "Не указана"

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
            logger.error(f"Ошибка при получении данных склада: {e}")
            return jsonify({"message": "Ошибка на сервере"}), 500

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

                db.session.execute(
                    text("""
                        CALL record_transaction(:product_id, 'Приход', :quantity, :supplier_id)
                    """),
                    {
                        'product_id': product_id,
                        'quantity': quantity,
                        'supplier_id': supplier_id
                    }
                )
            else:
                db.session.execute(
                    text("""
                        CALL add_new_product(:name, :description, :price, :category_id, :quantity, :supplier_id)
                    """),
                    {
                        'name': name,
                        'description': description,
                        'price': price,
                        'category_id': category_id,
                        'quantity': quantity,
                        'supplier_id': supplier_id
                    }
                )

            db.session.commit()

            return jsonify({"message": "Товар успешно добавлен на склад"}), 201
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при добавлении товара: {e}")
            return jsonify({"message": "Ошибка на сервере"}), 500

    @app.route('/inventory/<int:product_id>/quantity', methods=['PATCH'])
    @jwt_required()
    @role_required([1, 2])  # Администратор или работник
    def update_quantity(product_id):
        try:
            data = request.get_json()
            action = data.get('action')
            amount = int(data.get('amount', 0))
            supplier_id = data.get('supplier_id')

            if action not in ['increase', 'decrease']:
                return jsonify({"message": "Некорректное действие. Используйте 'increase' или 'decrease'."}), 400
            if amount <= 0:
                return jsonify({"message": "Количество должно быть положительным числом."}), 400

            # Определяем тип транзакции
            transaction_type = 'Приход' if action == 'increase' else 'Расход'

            # Валидация supplier_id
            if action == 'increase':
                if not supplier_id:
                    return jsonify({"message": "Для прихода необходим идентификатор поставщика."}), 400
            elif action == 'decrease':
                pass

            db.session.execute(
                text("""
                    CALL record_transaction(:product_id, :transaction_type, :quantity, :supplier_id)
                """),
                {
                    'product_id': product_id,
                    'transaction_type': transaction_type,
                    'quantity': amount,
                    'supplier_id': supplier_id
                }
            )

            db.session.commit()

            return jsonify({"message": "Количество успешно обновлено"}), 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при обновлении количества товара (ID: {product_id}): {e}")
            return jsonify({"message": "Ошибка на сервере"}), 500


    @app.route('/inventory/<int:product_id>', methods=['DELETE'])
    @jwt_required()
    @role_required([1])  # Только Администратор
    def delete_product_endpoint(product_id):
        try:
            db.session.execute(
                text("""
                    CALL delete_product(:product_id)
                """),
                {'product_id': product_id}
            )
            db.session.commit()
            return jsonify({"message": "Товар успешно удален"}), 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при удалении товара (ID: {product_id}): {e}")
            return jsonify({"message": "Ошибка на сервере"}), 500

    @app.route('/categories', methods=['POST'])
    @jwt_required()
    @role_required([1, 2])  # Администратор или работник
    def add_category_endpoint():
        try:
            data = request.get_json()
            category_name = data['category_name']
            description = data.get('description', '')

            # Проверяем, существует ли уже категория с таким названием
            existing_category = db.session.execute(
                text("SELECT * FROM product_categories WHERE category_name = :category_name"),
                {'category_name': category_name}
            ).fetchone()

            if existing_category:
                return jsonify({"message": "Категория с таким названием уже существует"}), 400

            db.session.execute(
                text("""
                    CALL add_category_proc(:category_name, :description)
                """),
                {'category_name': category_name, 'description': description}
            )
            db.session.commit()

            return jsonify({"message": "Категория успешно добавлена"}), 201
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при добавлении категории '{category_name}': {e}")
            return jsonify({"message": "Ошибка на сервере"}), 500

    @app.route('/categories/<int:category_id>', methods=['DELETE'])
    @jwt_required()
    @role_required([1])  # Только Администратор
    def delete_category_endpoint(category_id):
        try:
            db.session.execute(
                text("""
                    CALL delete_category(:category_id)
                """),
                {'category_id': category_id}
            )
            db.session.commit()
            return jsonify({"message": "Категория успешно удалена"}), 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при удалении категории (ID: {category_id}): {e}")
            if 'невозможно удалить категорию' in str(e).lower():
                return jsonify({"message": str(e)}), 400
            return jsonify({"message": "Ошибка на сервере"}), 500

    @app.route('/suppliers', methods=['POST'])
    @jwt_required()
    @role_required([1, 2])  # Администратор или работник
    def add_supplier_endpoint():
        try:
            data = request.get_json()
            supplier_name = data['supplier_name']
            contact_info = data.get('contact_info', '')
            address = data.get('address', '')

            # Проверяем, существует ли уже поставщик с таким названием
            existing_supplier = db.session.execute(
                text("SELECT * FROM suppliers WHERE supplier_name = :supplier_name"),
                {'supplier_name': supplier_name}
            ).fetchone()

            if existing_supplier:
                return jsonify({"message": "Поставщик с таким названием уже существует"}), 400

            db.session.execute(
                text("""
                    CALL add_supplier_proc(:supplier_name, :contact_info, :address)
                """),
                {'supplier_name': supplier_name, 'contact_info': contact_info, 'address': address}
            )
            db.session.commit()

            return jsonify({"message": "Поставщик успешно добавлен"}), 201
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при добавлении поставщика '{supplier_name}': {e}")
            return jsonify({"message": "Ошибка на сервере"}), 500

    @app.route('/suppliers/<int:supplier_id>', methods=['DELETE'])
    @jwt_required()
    @role_required([1])  # Только Администратор
    def delete_supplier_endpoint(supplier_id):
        try:
            db.session.execute(
                text("""
                    CALL delete_supplier(:supplier_id)
                """),
                {'supplier_id': supplier_id}
            )
            db.session.commit()
            return jsonify({"message": "Поставщик успешно удален"}), 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при удалении поставщика (ID: {supplier_id}): {e}")
            if 'невозможно удалить поставщика' in str(e).lower():
                return jsonify({"message": str(e)}), 400
            return jsonify({"message": "Ошибка на сервере"}), 500


    @app.route('/transactions', methods=['GET'])
    @jwt_required()
    @role_required([1, 2])  # Администратор или работник
    def get_transactions():
        try:
            transactions = db.session.execute(
                text("""
                    SELECT 
                        transaction_id,
                        transaction_date,
                        transaction_type,
                        quantity,
                        product_name,
                        supplier_name,
                        contact_info,
                        address
                    FROM view_transaction_details
                """)
            ).mappings().fetchall()

            transaction_list = []
            for txn in transactions:
                transaction_list.append({
                    'transaction_id': txn['transaction_id'],
                    'transaction_date': txn['transaction_date'].strftime('%Y-%m-%d %H:%M:%S') if txn['transaction_date'] else "Не указана",
                    'transaction_type': txn['transaction_type'],
                    'quantity': txn['quantity'],
                    'product_name': txn['product_name'],
                    'supplier_name': txn['supplier_name'] if txn['supplier_name'] else "Не указан",
                    'contact_info': txn['contact_info'] if txn['contact_info'] else "Не указано",
                    'address': txn['address'] if txn['address'] else "Не указано"
                })

            return jsonify(transaction_list), 200
        except Exception as e:
            logger.error(f"Ошибка при получении транзакций: {e}")
            return jsonify({"message": "Ошибка на сервере"}), 500

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
