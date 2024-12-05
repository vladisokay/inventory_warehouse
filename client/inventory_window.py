import csv
import json
import threading

import requests
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QLabel, QComboBox, QMessageBox, QDialog
)


class InventoryApp(QWidget):
    def __init__(self, token):
        super().__init__()
        self.token = token
        self.setWindowTitle("Управление складом")
        self.setGeometry(100, 100, 1200, 600)

        self.user_role_id = self.get_user_role()

        # Применение стиля
        self.setStyleSheet("""
            QWidget {
                background-color: #f7f7f7;
                font-family: Arial, sans-serif;
                font-size: 14px;
            }
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #005bb5;
            }
            QPushButton:pressed {
                background-color: #004f91;
            }

            QTableWidget {
                border: 1px solid #ddd;
                gridline-color: #ddd;
                background-color: white;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #e7e7e7;
                color: #333;
                font-weight: bold;
                border: 1px solid #ccc;
            }

            QDialog {
                background-color: #f7f7f7;
                font-family: Arial, sans-serif;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #0078d7;
            }
            QLabel {
                color: #333;
                font-weight: bold;
                margin-bottom: 4px;
            }
            QComboBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 6px 12px;
                background-color: white;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #ccc;
                selection-background-color: #0078d7;
                selection-color: white;
            }




        """)

        # Таблица товаров
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID", "Название", "Описание", "Цена", "Количество", "Последнее обновление",
            "Приход за месяц", "Отгрузка за месяц", "Категория", "Поставщик"
        ])
        self.table.setAlternatingRowColors(True)

        # Основной макет
        layout = QVBoxLayout()
        layout.addWidget(self.table)

        # Панель с кнопками
        button_layout = QHBoxLayout()

        self.button_refresh = QPushButton("Обновить")
        self.button_refresh.clicked.connect(self.refresh_inventory)
        button_layout.addWidget(self.button_refresh)

        if self.user_role_id in [1, 2]:  # Администратор и Редактор
            self.button_add = QPushButton("Добавить товар")
            self.button_add.clicked.connect(self.add_product_window)
            button_layout.addWidget(self.button_add)

            self.button_delete = QPushButton("Удалить товар")
            self.button_delete.clicked.connect(self.delete_product)
            button_layout.addWidget(self.button_delete)

            self.button_update = QPushButton("Обновить количество")
            self.button_update.clicked.connect(self.update_quantity_window)
            button_layout.addWidget(self.button_update)

            self.button_manage_categories = QPushButton("Управление категориями")
            self.button_manage_categories.clicked.connect(self.manage_categories_window)
            button_layout.addWidget(self.button_manage_categories)

            self.button_manage_suppliers = QPushButton("Управление поставщиками")
            self.button_manage_suppliers.clicked.connect(self.manage_suppliers_window)
            button_layout.addWidget(self.button_manage_suppliers)


        self.button_export = QPushButton("Экспорт CSV")
        self.button_export.clicked.connect(self.export_csv)
        button_layout.addWidget(self.button_export)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # Загрузка начальных данных
        self.refresh_inventory()
    def get_user_role(self):
        import jwt
        try:
            decoded = jwt.decode(self.token, options={"verify_signature": False})
            identity = json.loads(decoded.get('sub', '{}'))
            role_id = identity.get('role_id')
            if role_id is None:
                raise ValueError("Token does not contain role_id")
            return int(role_id)
        except Exception as e:
            self.show_error(f"Ошибка определения роли пользователя: {e}")
            return None


    def show_message(self, message):
        """Показать сообщение пользователю"""
        msg = QMessageBox()
        msg.setText(message)
        msg.exec_()

    def refresh_inventory(self):
        def task():
            headers = {'Authorization': f'Bearer {self.token}'}
            try:
                response = requests.get('http://localhost:5000/inventory', headers=headers)
                if response.status_code == 200:
                    inventory = response.json()
                    self.update_table(inventory)  # Прямой вызов update_table
                else:
                    message = response.json().get('message', 'Ошибка получения данных')
                    self.show_error(message)
            except requests.exceptions.ConnectionError:
                self.show_error("Не удалось подключиться к серверу")

        threading.Thread(target=task).start()

    def update_table(self, inventory):
        """Обновляет таблицу с товарами."""
        QTableWidget.setRowCount(self.table, 0)  # Сначала очищаем таблицу
        for item in inventory:
            row = self.table.rowCount()  # Получаем количество строк в таблице
            self.table.insertRow(row)  # Вставляем новую строку

            # Заполняем ячейки таблицы данными
            self.table.setItem(row, 0, QTableWidgetItem(str(item['product_id'])))
            self.table.setItem(row, 1, QTableWidgetItem(item['name']))
            self.table.setItem(row, 2, QTableWidgetItem(item['description']))
            self.table.setItem(row, 3, QTableWidgetItem(str(item['price'])))
            self.table.setItem(row, 4, QTableWidgetItem(str(item['quantity'])))
            self.table.setItem(row, 5, QTableWidgetItem(item['last_updated']))
            self.table.setItem(row, 6, QTableWidgetItem(str(item.get('incoming_this_month', 'Не указано'))))
            self.table.setItem(row, 7, QTableWidgetItem(str(item.get('outgoing_this_month', 'Не указано'))))
            self.table.setItem(row, 8, QTableWidgetItem(item.get('category_name', 'Не указана')))
            self.table.setItem(row, 9, QTableWidgetItem(item.get('supplier_name', 'Не указан')))

    def add_product_window(self):
        window = QWidget()
        window.setWindowTitle("Добавить Товар")
        layout = QVBoxLayout()

        fields = {
            "Название": QLineEdit(),
            "Описание": QLineEdit(),
            "Цена": QLineEdit(),
            "Количество": QLineEdit(),
            "Категория": QComboBox(),
            "Поставщик": QComboBox()
        }

        for label, widget in fields.items():
            layout.addWidget(QLabel(label))
            layout.addWidget(widget)

        self.load_categories(fields["Категория"])
        self.load_suppliers(fields["Поставщик"])

        def add_product():
            try:
                payload = {
                    "name": fields["Название"].text(),
                    "description": fields["Описание"].text(),
                    "price": float(fields["Цена"].text()),
                    "quantity": int(fields["Количество"].text()),
                    "category_id": int(fields["Категория"].currentText().split(" - ")[0]),
                    "supplier_id": int(fields["Поставщик"].currentText().split(" - ")[0]),
                }
                headers = {'Authorization': f'Bearer {self.token}'}
                response = requests.post('http://localhost:5000/inventory', headers=headers, json=payload)
                if response.status_code == 201:
                    QMessageBox.information(window, "Успех", "Товар добавлен")
                    window.close()
                    self.refresh_inventory()
                else:
                    self.show_error(response.json().get('message', 'Ошибка добавления товара'))
            except Exception as e:
                self.show_error(str(e))

        add_button = QPushButton("Добавить")
        add_button.clicked.connect(add_product)
        layout.addWidget(add_button)
        window.setLayout(layout)
        window.show()

    def delete_product(self):
        selected = self.table.currentRow()
        if selected < 0:
            self.show_error("Выберите товар для удаления.")
            return
        product_id = self.table.item(selected, 0).text()
        headers = {'Authorization': f'Bearer {self.token}'}
        response = requests.delete(f'http://localhost:5000/inventory/{product_id}', headers=headers)
        if response.status_code == 200:
            QMessageBox.information(self, "Успех", "Товар удален.")
            self.refresh_inventory()
        else:
            self.show_error(response.json().get('message', 'Ошибка при удалении товара'))

    def update_quantity_window(self):
        """Открывает окно выбора изменения количества товара."""
        selected = self.table.currentRow()
        if selected < 0:
            self.show_error("Выберите товар для изменения количества.")
            return

        product_id = self.table.item(selected, 0).text()
        product_name = self.table.item(selected, 1).text()

        try:
            # Создаем модальное окно выбора действия
            window = QDialog(self)
            window.setWindowTitle(f"Изменить количество: {product_name}")
            layout = QVBoxLayout()

            layout.addWidget(QLabel(f"Товар: {product_name} (ID: {product_id})"))

            # Кнопки увеличения и уменьшения количества
            increase_button = QPushButton("Увеличить количество")
            decrease_button = QPushButton("Уменьшить количество")

            increase_button.clicked.connect(
                lambda: self.modify_quantity(product_id, "increase", window))
            decrease_button.clicked.connect(
                lambda: self.modify_quantity(product_id, "decrease", window))

            layout.addWidget(increase_button)
            layout.addWidget(decrease_button)

            window.setLayout(layout)
            window.exec_()  # Модальное окно
        except Exception as e:
            self.show_error(f"Ошибка при открытии окна: {e}")

    def modify_quantity(self, product_id, action, parent_window):
        """Открывает окно изменения количества для увеличения или уменьшения."""
        action_text = "увеличить" if action == "increase" else "уменьшить"

        try:
            window = QDialog(self)
            window.setWindowTitle(f"{action_text.capitalize()} количество")
            layout = QVBoxLayout()

            layout.addWidget(QLabel(f"Введите количество для {action_text}:"))

            # Поле ввода количества
            quantity_input = QLineEdit()
            quantity_input.setPlaceholderText("Введите положительное число")
            layout.addWidget(quantity_input)

            def apply_change():
                try:
                    amount = int(quantity_input.text())
                    if amount <= 0:
                        raise ValueError("Количество должно быть положительным числом.")

                    headers = {'Authorization': f'Bearer {self.token}'}
                    payload = {
                        "action": action,
                        "amount": amount
                    }

                    # Отправляем запрос на сервер
                    response = requests.patch(
                        f"http://localhost:5000/inventory/{product_id}/quantity",
                        headers=headers,
                        json=payload
                    )

                    if response.status_code == 200:
                        data = response.json()

                        # Обновляем таблицу после изменения
                        for row in range(self.table.rowCount()):
                            if self.table.item(row, 0).text() == str(product_id):
                                # Обновляем количество товара
                                current_quantity = int(self.table.item(row, 4).text() or 0)
                                if action == "increase":
                                    new_quantity = current_quantity + amount
                                else:
                                    new_quantity = current_quantity - amount
                                self.table.setItem(row, 4, QTableWidgetItem(str(new_quantity)))

                                # Обновляем приход за месяц
                                current_incoming = int(self.table.item(row, 6).text() or 0)
                                if action == "increase":
                                    new_incoming = current_incoming + amount
                                    self.table.setItem(row, 6, QTableWidgetItem(str(new_incoming)))

                                # Обновляем отгрузку за месяц
                                current_outgoing = int(self.table.item(row, 7).text() or 0)
                                if action == "decrease":
                                    new_outgoing = current_outgoing + amount
                                    self.table.setItem(row, 7, QTableWidgetItem(str(new_outgoing)))

                                break

                        QMessageBox.information(self, "Успех", f"Количество успешно {'увеличено' if action_text == 'увеличить' else 'уменьшено'}.")
                        window.accept()
                        parent_window.accept()
                    else:
                        message = response.json().get("message", "Ошибка обновления количества.")
                        self.show_error(message)

                except ValueError as e:
                    self.show_error(str(e))
                except requests.exceptions.RequestException as e:
                    self.show_error(f"Ошибка подключения: {e}")

            # Кнопка подтверждения
            apply_button = QPushButton("Применить")
            apply_button.clicked.connect(apply_change)

            layout.addWidget(apply_button)
            window.setLayout(layout)
            window.exec_()
        except Exception as e:
            self.show_error(f"Ошибка при изменении количества: {e}")

    def manage_categories_window(self):
        """Открывает окно управления категориями."""
        window = QWidget()
        window.setWindowTitle("Управление категориями")
        window.setGeometry(200, 200, 600, 400)

        layout = QVBoxLayout()
        tree = QTableWidget()
        tree.setColumnCount(3)
        tree.setHorizontalHeaderLabels(["ID", "Название", "Описание"])
        layout.addWidget(tree)

        def refresh_categories():
            headers = {'Authorization': f'Bearer {self.token}'}
            try:
                response = requests.get('http://localhost:5000/categories', headers=headers)
                if response.status_code == 200:
                    categories = response.json()
                    tree.setRowCount(0)
                    for category in categories:
                        try:
                            # Проверка на наличие всех нужных данных
                            category_id = category.get('category_id')
                            category_name = category.get('category_name')
                            description = category.get('description')

                            if not category_id or not category_name or not description:
                                continue  # Пропускаем категории с неполными данными

                            row = tree.rowCount()
                            tree.insertRow(row)
                            tree.setItem(row, 0, QTableWidgetItem(str(category_id)))
                            tree.setItem(row, 1, QTableWidgetItem(category_name))
                            tree.setItem(row, 2, QTableWidgetItem(description))
                        except KeyError as e:
                            print(f"Ошибка доступа к данным категории: {e}")
                else:
                    self.show_error("Не удалось загрузить категории")
            except requests.exceptions.ConnectionError:
                self.show_error("Ошибка подключения к серверу")
            except Exception as e:
                self.show_error(f"Ошибка при обновлении категорий: {e}")

        def add_category():
            add_window = QWidget()
            add_window.setWindowTitle("Добавить категорию")
            add_window.setGeometry(300, 300, 400, 200)

            add_layout = QVBoxLayout()

            name_label = QLabel("Название")
            name_input = QLineEdit()
            description_label = QLabel("Описание")
            description_input = QLineEdit()

            add_layout.addWidget(name_label)
            add_layout.addWidget(name_input)
            add_layout.addWidget(description_label)
            add_layout.addWidget(description_input)

            def save_category():
                headers = {'Authorization': f'Bearer {self.token}'}
                payload = {'category_name': name_input.text(), 'description': description_input.text()}
                try:
                    response = requests.post('http://localhost:5000/categories', headers=headers, json=payload)
                    if response.status_code == 201:
                        QMessageBox.information(add_window, "Успех", "Категория добавлена!")
                        add_window.close()
                        refresh_categories()
                    else:
                        self.show_error("Не удалось добавить категорию")
                except requests.exceptions.ConnectionError:
                    self.show_error("Ошибка подключения к серверу")

            save_button = QPushButton("Сохранить")
            save_button.clicked.connect(save_category)
            add_layout.addWidget(save_button)

            add_window.setLayout(add_layout)
            add_window.show()

        def delete_category():
            selected_row = tree.currentRow()
            if selected_row < 0:
                self.show_error("Выберите категорию для удаления")
                return

            category_id = tree.item(selected_row, 0).text()
            headers = {'Authorization': f'Bearer {self.token}'}

            if QMessageBox.question(window, "Подтверждение", f"Удалить категорию ID {category_id}?") == QMessageBox.Yes:
                try:
                    response = requests.delete(f'http://localhost:5000/categories/{category_id}', headers=headers)
                    if response.status_code == 200:
                        QMessageBox.information(window, "Успех", "Категория удалена!")
                        refresh_categories()
                    else:
                        self.show_error("Не удалось удалить категорию")
                except requests.exceptions.ConnectionError:
                    self.show_error("Ошибка подключения к серверу")

        refresh_button = QPushButton("Обновить")
        refresh_button.clicked.connect(refresh_categories)
        layout.addWidget(refresh_button)

        add_button = QPushButton("Добавить")
        add_button.clicked.connect(add_category)
        layout.addWidget(add_button)

        delete_button = QPushButton("Удалить")
        delete_button.clicked.connect(delete_category)
        layout.addWidget(delete_button)

        refresh_categories()
        window.setLayout(layout)
        window.show()

    def manage_suppliers_window(self):
        """Открывает окно управления поставщиками."""
        window = QWidget()
        window.setWindowTitle("Управление поставщиками")
        window.setGeometry(200, 200, 600, 400)

        layout = QVBoxLayout()
        tree = QTableWidget()
        tree.setColumnCount(4)
        tree.setHorizontalHeaderLabels(["ID", "Название", "Контакты", "Адрес"])
        layout.addWidget(tree)

        def refresh_suppliers():
            headers = {'Authorization': f'Bearer {self.token}'}
            try:
                response = requests.get('http://localhost:5000/suppliers', headers=headers)
                if response.status_code == 200:
                    suppliers = response.json()
                    tree.setRowCount(0)

                    # Проверяем, что каждый поставщик имеет все необходимые поля
                    for supplier in suppliers:
                        if 'supplier_id' in supplier and 'supplier_name' in supplier and 'contact_info' in supplier and 'address' in supplier:
                            row = tree.rowCount()
                            tree.insertRow(row)
                            tree.setItem(row, 0, QTableWidgetItem(str(supplier['supplier_id'])))
                            tree.setItem(row, 1, QTableWidgetItem(supplier['supplier_name']))
                            tree.setItem(row, 2, QTableWidgetItem(supplier['contact_info']))
                            tree.setItem(row, 3, QTableWidgetItem(supplier['address']))
                        else:
                            self.show_error("Некоторые поставщики не содержат обязательных данных.")
                else:
                    self.show_error("Не удалось загрузить поставщиков")
            except requests.exceptions.ConnectionError:
                self.show_error("Ошибка подключения к серверу")
            except Exception as e:
                self.show_error(f"Ошибка при обновлении поставщиков: {e}")

        def add_supplier():
            add_window = QWidget()
            add_window.setWindowTitle("Добавить поставщика")
            add_window.setGeometry(300, 300, 400, 200)

            add_layout = QVBoxLayout()

            name_label = QLabel("Название")
            name_input = QLineEdit()
            contact_label = QLabel("Контакты")
            contact_input = QLineEdit()
            address_label = QLabel("Адрес")
            address_input = QLineEdit()

            add_layout.addWidget(name_label)
            add_layout.addWidget(name_input)
            add_layout.addWidget(contact_label)
            add_layout.addWidget(contact_input)
            add_layout.addWidget(address_label)
            add_layout.addWidget(address_input)

            def save_supplier():
                headers = {'Authorization': f'Bearer {self.token}'}
                payload = {
                    'supplier_name': name_input.text(),
                    'contact_info': contact_input.text(),
                    'address': address_input.text()
                }
                try:
                    response = requests.post('http://localhost:5000/suppliers', headers=headers, json=payload)
                    if response.status_code == 201:
                        QMessageBox.information(add_window, "Успех", "Поставщик добавлен!")
                        add_window.close()
                        refresh_suppliers()
                    else:
                        self.show_error("Не удалось добавить поставщика")
                except requests.exceptions.ConnectionError:
                    self.show_error("Ошибка подключения к серверу")
                except Exception as e:
                    self.show_error(f"Ошибка при добавлении поставщика: {e}")

            save_button = QPushButton("Сохранить")
            save_button.clicked.connect(save_supplier)
            add_layout.addWidget(save_button)

            add_window.setLayout(add_layout)
            add_window.show()

        def delete_supplier():
            selected_row = tree.currentRow()
            if selected_row < 0:
                self.show_error("Выберите поставщика для удаления")
                return

            supplier_id = tree.item(selected_row, 0).text()
            headers = {'Authorization': f'Bearer {self.token}'}

            if QMessageBox.question(window, "Подтверждение",
                                    f"Удалить поставщика ID {supplier_id}?") == QMessageBox.Yes:
                try:
                    response = requests.delete(f'http://localhost:5000/suppliers/{supplier_id}', headers=headers)
                    if response.status_code == 200:
                        QMessageBox.information(window, "Успех", "Поставщик удален!")
                        refresh_suppliers()
                    else:
                        self.show_error("Не удалось удалить поставщика")
                except requests.exceptions.ConnectionError:
                    self.show_error("Ошибка подключения к серверу")
                except Exception as e:
                    self.show_error(f"Ошибка при удалении поставщика: {e}")

        refresh_button = QPushButton("Обновить")
        refresh_button.clicked.connect(refresh_suppliers)
        layout.addWidget(refresh_button)

        add_button = QPushButton("Добавить")
        add_button.clicked.connect(add_supplier)
        layout.addWidget(add_button)

        delete_button = QPushButton("Удалить")
        delete_button.clicked.connect(delete_supplier)
        layout.addWidget(delete_button)

        refresh_suppliers()
        window.setLayout(layout)
        window.show()

    def export_csv(self):
        headers = {'Authorization': f'Bearer {self.token}'}
        response = requests.get('http://localhost:5000/inventory', headers=headers)
        if response.status_code == 200:
            inventory = response.json()
            with open("inventory.csv", "w", newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["ID", "Название", "Описание", "Цена", "Количество", "Последнее обновление"])
                for item in inventory:
                    writer.writerow([
                        item['product_id'],
                        item['name'],
                        item['description'],
                        item['price'],
                        item['quantity'],
                        item['last_updated']
                    ])
            QMessageBox.information(self, "Успех", "Данные экспортированы в inventory.csv")
        else:
            self.show_error(response.json().get('message', 'Ошибка экспорта данных'))

    def load_categories(self, combobox):
        headers = {'Authorization': f'Bearer {self.token}'}
        response = requests.get('http://localhost:5000/categories', headers=headers)
        if response.status_code == 200:
            categories = response.json()
            for category in categories:
                combobox.addItem(f"{category['category_id']} - {category['category_name']}")

    def load_suppliers(self, combobox):
        headers = {'Authorization': f'Bearer {self.token}'}
        response = requests.get('http://localhost:5000/suppliers', headers=headers)
        if response.status_code == 200:
            suppliers = response.json()
            for supplier in suppliers:
                combobox.addItem(f"{supplier['supplier_id']} - {supplier['supplier_name']}")

    def show_error(self, message):
        QMessageBox.critical(self, "Ошибка", message)
