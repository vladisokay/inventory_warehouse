import csv
import json
import threading

import jwt
import requests
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLineEdit, QLabel, QComboBox, QMessageBox, QDialog
)


class InventoryApp(QWidget):
    def __init__(self, token):
        super().__init__()
        self.token = token
        self.setWindowTitle("Управление складом")
        self.setGeometry(100, 100, 1200, 600)

        self.user_role_id = self.get_user_role()

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
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        # Основной макет
        layout = QVBoxLayout()
        layout.addWidget(self.table)

        # Панель с кнопками
        button_layout = QHBoxLayout()

        self.button_refresh = QPushButton("Обновить")
        self.button_refresh.clicked.connect(self.refresh_inventory)
        button_layout.addWidget(self.button_refresh)

        if self.user_role_id in [1, 2]:  # Администратор и Работник
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
        """Определяет роль пользователя на основе JWT токена."""
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
        """Показать информационное сообщение пользователю."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(message)
        msg.setWindowTitle("Информация")
        msg.exec_()

    def show_error(self, message):
        """Показать сообщение об ошибке пользователю."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle("Ошибка")
        msg.exec_()

    def refresh_inventory(self):
        """Обновляет таблицу с инвентарем, получая данные с сервера."""
        def task():
            headers = {'Authorization': f'Bearer {self.token}'}
            try:
                response = requests.get('http://localhost:5000/inventory', headers=headers)
                if response.status_code == 200:
                    inventory = response.json()
                    self.update_table(inventory)
                else:
                    message = response.json().get('message', 'Ошибка получения данных')
                    self.show_error(message)
            except requests.exceptions.ConnectionError:
                self.show_error("Не удалось подключиться к серверу")
            except Exception as e:
                self.show_error(f"Ошибка при получении инвентаря: {e}")

        threading.Thread(target=task).start()

    def update_table(self, inventory):
        """Обновляет таблицу с товарами."""
        self.table.setRowCount(0)  # Очищаем таблицу
        for item in inventory:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(item.get('product_id', ''))))
            self.table.setItem(row, 1, QTableWidgetItem(item.get('name', '')))
            self.table.setItem(row, 2, QTableWidgetItem(item.get('description', '')))
            self.table.setItem(row, 3, QTableWidgetItem(str(item.get('price', ''))))
            self.table.setItem(row, 4, QTableWidgetItem(str(item.get('quantity', ''))))
            self.table.setItem(row, 5, QTableWidgetItem(item.get('last_updated', '')))
            self.table.setItem(row, 6, QTableWidgetItem(str(item.get('incoming_this_month', 'Не указано'))))
            self.table.setItem(row, 7, QTableWidgetItem(str(item.get('outgoing_this_month', 'Не указано'))))
            self.table.setItem(row, 8, QTableWidgetItem(item.get('category_name', 'Не указана')))
            self.table.setItem(row, 9, QTableWidgetItem(item.get('supplier_name', 'Не указан')))

    def add_product_window(self):
        """Открывает окно для добавления нового товара."""
        window = QDialog(self)
        window.setWindowTitle("Добавить товар")
        window.setModal(True)
        window.setFixedSize(400, 400)

        layout = QVBoxLayout()

        # Поля для ввода данных
        name_label = QLabel("Название")
        name_input = QLineEdit()
        layout.addWidget(name_label)
        layout.addWidget(name_input)

        description_label = QLabel("Описание")
        description_input = QLineEdit()
        layout.addWidget(description_label)
        layout.addWidget(description_input)

        price_label = QLabel("Цена")
        price_input = QLineEdit()
        price_input.setPlaceholderText("Введите числовое значение")
        layout.addWidget(price_label)
        layout.addWidget(price_input)

        quantity_label = QLabel("Количество")
        quantity_input = QLineEdit()
        quantity_input.setPlaceholderText("Введите целое число")
        layout.addWidget(quantity_label)
        layout.addWidget(quantity_input)

        category_label = QLabel("Категория")
        category_combo = QComboBox()
        layout.addWidget(category_label)
        layout.addWidget(category_combo)

        supplier_label = QLabel("Поставщик")
        supplier_combo = QComboBox()
        layout.addWidget(supplier_label)
        layout.addWidget(supplier_combo)

        # Загрузка категорий и поставщиков
        self.load_categories(category_combo)
        self.load_suppliers(supplier_combo)

        # Кнопка добавления товара
        add_button = QPushButton("Добавить")
        add_button.clicked.connect(lambda: self.add_product(
            name_input.text(),
            description_input.text(),
            price_input.text(),
            quantity_input.text(),
            category_combo.currentText(),
            supplier_combo.currentText(),
            window
        ))
        layout.addWidget(add_button)

        window.setLayout(layout)
        window.exec_()

    def add_product(self, name, description, price, quantity, category_text, supplier_text, window):
        """Отправляет запрос на добавление нового товара."""
        # Валидация данных
        if not name.strip():
            self.show_error("Название товара не может быть пустым.")
            return
        try:
            price = float(price)
            if price < 0:
                raise ValueError
        except ValueError:
            self.show_error("Цена должна быть неотрицательным числом.")
            return
        try:
            quantity = int(quantity)
            if quantity < 0:
                raise ValueError
        except ValueError:
            self.show_error("Количество должно быть неотрицательным целым числом.")
            return
        try:
            category_id = int(category_text.split(" - ")[0])
        except (IndexError, ValueError):
            self.show_error("Некорректный выбор категории.")
            return
        try:
            supplier_id = int(supplier_text.split(" - ")[0])
        except (IndexError, ValueError):
            self.show_error("Некорректный выбор поставщика.")
            return

        payload = {
            "name": name,
            "description": description,
            "price": price,
            "quantity": quantity,
            "category_id": category_id,
            "supplier_id": supplier_id
        }

        headers = {'Authorization': f'Bearer {self.token}'}

        def task():
            try:
                response = requests.post('http://localhost:5000/inventory', headers=headers, json=payload)
                if response.status_code == 201:
                    self.show_message("Товар успешно добавлен на склад.")
                    window.accept()
                    self.refresh_inventory()
                else:
                    message = response.json().get('message', 'Ошибка добавления товара.')
                    self.show_error(message)
            except requests.exceptions.ConnectionError:
                self.show_error("Не удалось подключиться к серверу.")
            except Exception as e:
                self.show_error(f"Ошибка при добавлении товара: {e}")

        threading.Thread(target=task).start()

    def delete_product(self):
        """Удаляет выбранный товар."""
        selected = self.table.currentRow()
        if selected < 0:
            self.show_error("Выберите товар для удаления.")
            return

        product_id = self.table.item(selected, 0).text()
        product_name = self.table.item(selected, 1).text()

        confirm = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить товар '{product_name}' (ID: {product_id})?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            headers = {'Authorization': f'Bearer {self.token}'}

            def task():
                try:
                    response = requests.delete(f'http://localhost:5000/inventory/{product_id}', headers=headers)
                    if response.status_code == 200:
                        self.show_message("Товар успешно удален.")
                        self.refresh_inventory()
                    else:
                        message = response.json().get('message', 'Ошибка при удалении товара.')
                        self.show_error(message)
                except requests.exceptions.ConnectionError:
                    self.show_error("Не удалось подключиться к серверу.")
                except Exception as e:
                    self.show_error(f"Ошибка при удалении товара: {e}")

            threading.Thread(target=task).start()

    def update_quantity_window(self):
        """Открывает окно выбора изменения количества товара."""
        selected = self.table.currentRow()
        if selected < 0:
            self.show_error("Выберите товар для изменения количества.")
            return

        product_id = self.table.item(selected, 0).text()
        product_name = self.table.item(selected, 1).text()

        try:
            window = QDialog(self)
            window.setWindowTitle(f"Изменить количество: {product_name}")
            window.setModal(True)
            window.setFixedSize(300, 200)
            layout = QVBoxLayout()

            layout.addWidget(QLabel(f"Товар: {product_name} (ID: {product_id})"))

            increase_button = QPushButton("Увеличить количество")
            decrease_button = QPushButton("Уменьшить количество")

            increase_button.clicked.connect(
                lambda: self.modify_quantity(product_id, "increase", window))
            decrease_button.clicked.connect(
                lambda: self.modify_quantity(product_id, "decrease", window))

            layout.addWidget(increase_button)
            layout.addWidget(decrease_button)

            window.setLayout(layout)
            window.exec_()
        except Exception as e:
            self.show_error(f"Ошибка при открытии окна: {e}")

    def modify_quantity(self, product_id, action, parent_window):
        """Открывает окно изменения количества для увеличения или уменьшения."""
        action_text = "увеличить" if action == "increase" else "уменьшить"

        try:
            window = QDialog(self)
            window.setWindowTitle(f"{action_text.capitalize()} количество")
            window.setModal(True)
            window.setFixedSize(300, 250)
            layout = QVBoxLayout()

            layout.addWidget(QLabel(f"Введите количество:"))

            quantity_input = QLineEdit()
            quantity_input.setPlaceholderText("Введите положительное число")
            layout.addWidget(quantity_input)

            if action == "increase":
                layout.addWidget(QLabel("Выберите поставщика:"))
                supplier_combo = QComboBox()
                self.load_suppliers_into_combobox(supplier_combo)
                layout.addWidget(supplier_combo)
            else:
                supplier_combo = None

            def apply_change():
                try:
                    amount_text = quantity_input.text()
                    if not amount_text.strip():
                        raise ValueError("Количество не может быть пустым.")
                    amount = int(amount_text)
                    if amount <= 0:
                        raise ValueError("Количество должно быть положительным числом.")

                    payload = {
                        "action": action,
                        "amount": amount
                    }

                    if action == "increase" and supplier_combo:
                        selected_supplier = supplier_combo.currentText()
                        supplier_id = int(selected_supplier.split(" - ")[0])
                        payload["supplier_id"] = supplier_id
                    elif action == "increase" and not supplier_combo:
                        raise ValueError("Поставщик не выбран.")

                    headers = {'Authorization': f'Bearer {self.token}'}

                    response = requests.patch(
                        f"http://localhost:5000/inventory/{product_id}/quantity",
                        headers=headers,
                        json=payload
                    )

                    if response.status_code == 200:
                        self.show_message(f"Количество успешно {'увеличено' if action == 'increase' else 'уменьшено'}.")
                        window.accept()
                        parent_window.accept()
                        self.refresh_inventory()
                    else:
                        message = response.json().get("message", "Ошибка обновления количества.")
                        self.show_error(message)

                except ValueError as ve:
                    self.show_error(str(ve))
                except requests.exceptions.ConnectionError:
                    self.show_error("Не удалось подключиться к серверу.")
                except Exception as e:
                    self.show_error(f"Ошибка при изменении количества: {e}")

            # Кнопка подтверждения
            apply_button = QPushButton("Применить")
            apply_button.clicked.connect(apply_change)
            layout.addWidget(apply_button)

            window.setLayout(layout)
            window.exec_()
        except Exception as e:
            self.show_error(f"Ошибка при изменении количества: {e}")

    def load_suppliers_into_combobox(self, combobox):
        """Загружает поставщиков в выпадающий список."""
        headers = {'Authorization': f'Bearer {self.token}'}
        try:
            response = requests.get('http://localhost:5000/suppliers', headers=headers)
            if response.status_code == 200:
                suppliers = response.json()
                for supplier in suppliers:
                    combobox.addItem(f"{supplier['supplier_id']} - {supplier['supplier_name']}")
            else:
                self.show_error("Не удалось загрузить поставщиков.")
        except requests.exceptions.ConnectionError:
            self.show_error("Не удалось подключиться к серверу.")
        except Exception as e:
            self.show_error(f"Ошибка при загрузке поставщиков: {e}")

    def manage_categories_window(self):
        """Открывает окно управления категориями."""
        window = QDialog(self)
        window.setWindowTitle("Управление категориями")
        window.setModal(True)
        window.setFixedSize(600, 400)

        layout = QVBoxLayout()

        tree = QTableWidget()
        tree.setColumnCount(3)
        tree.setHorizontalHeaderLabels(["ID", "Название", "Описание"])
        tree.setSelectionBehavior(QTableWidget.SelectRows)
        tree.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(tree)

        # Панель с кнопками
        button_layout = QHBoxLayout()

        refresh_button = QPushButton("Обновить")
        refresh_button.clicked.connect(lambda: self.refresh_categories(tree))
        button_layout.addWidget(refresh_button)

        add_button = QPushButton("Добавить")
        add_button.clicked.connect(lambda: self.add_category(tree))
        button_layout.addWidget(add_button)

        delete_button = QPushButton("Удалить")
        delete_button.clicked.connect(lambda: self.delete_category(tree))
        button_layout.addWidget(delete_button)

        layout.addLayout(button_layout)

        window.setLayout(layout)
        self.refresh_categories(tree)
        window.exec_()

    def refresh_categories(self, tree):
        """Обновляет список категорий в таблице."""
        headers = {'Authorization': f'Bearer {self.token}'}

        def task():
            try:
                response = requests.get('http://localhost:5000/categories', headers=headers)
                if response.status_code == 200:
                    categories = response.json()
                    tree.setRowCount(0)
                    for category in categories:
                        row = tree.rowCount()
                        tree.insertRow(row)
                        tree.setItem(row, 0, QTableWidgetItem(str(category.get('category_id', ''))))
                        tree.setItem(row, 1, QTableWidgetItem(category.get('category_name', '')))
                        tree.setItem(row, 2, QTableWidgetItem(category.get('description', '')))
                else:
                    message = response.json().get('message', 'Не удалось загрузить категории.')
                    self.show_error(message)
            except requests.exceptions.ConnectionError:
                self.show_error("Не удалось подключиться к серверу.")
            except Exception as e:
                self.show_error(f"Ошибка при загрузке категорий: {e}")

        threading.Thread(target=task).start()

    def add_category(self, tree):
        """Открывает окно для добавления новой категории."""
        add_window = QDialog(self)
        add_window.setWindowTitle("Добавить категорию")
        add_window.setModal(True)
        add_window.setFixedSize(400, 300)

        layout = QVBoxLayout()

        name_label = QLabel("Название")
        name_input = QLineEdit()
        layout.addWidget(name_label)
        layout.addWidget(name_input)

        description_label = QLabel("Описание")
        description_input = QLineEdit()
        layout.addWidget(description_label)
        layout.addWidget(description_input)

        def save_category():
            name = name_input.text().strip()
            description = description_input.text().strip()

            if not name:
                self.show_error("Название категории не может быть пустым.")
                return

            payload = {
                'category_name': name,
                'description': description
            }

            headers = {'Authorization': f'Bearer {self.token}'}

            def task():
                try:
                    response = requests.post('http://localhost:5000/categories', headers=headers, json=payload)
                    if response.status_code == 201:
                        self.show_message("Категория успешно добавлена!")
                        add_window.accept()
                        self.refresh_categories(tree)
                    else:
                        message = response.json().get('message', 'Не удалось добавить категорию.')
                        self.show_error(message)
                except requests.exceptions.ConnectionError:
                    self.show_error("Не удалось подключиться к серверу.")
                except Exception as e:
                    self.show_error(f"Ошибка при добавлении категории: {e}")

            threading.Thread(target=task).start()

        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(save_category)
        layout.addWidget(save_button)

        add_window.setLayout(layout)
        add_window.exec_()

    def delete_category(self, tree):
        """Удаляет выбранную категорию."""
        selected_row = tree.currentRow()
        if selected_row < 0:
            self.show_error("Выберите категорию для удаления.")
            return

        category_id = tree.item(selected_row, 0).text()
        category_name = tree.item(selected_row, 1).text()

        confirm = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить категорию '{category_name}' (ID: {category_id})?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            headers = {'Authorization': f'Bearer {self.token}'}

            def task():
                try:
                    response = requests.delete(f'http://localhost:5000/categories/{category_id}', headers=headers)
                    if response.status_code == 200:
                        self.show_message("Категория успешно удалена.")
                        self.refresh_categories(tree)
                    else:
                        message = response.json().get('message', 'Не удалось удалить категорию.')
                        self.show_error(message)
                except requests.exceptions.ConnectionError:
                    self.show_error("Не удалось подключиться к серверу.")
                except Exception as e:
                    self.show_error(f"Ошибка при удалении категории: {e}")

            threading.Thread(target=task).start()

    def manage_suppliers_window(self):
        """Открывает окно управления поставщиками."""
        window = QDialog(self)
        window.setWindowTitle("Управление поставщиками")
        window.setModal(True)
        window.setFixedSize(700, 400)

        layout = QVBoxLayout()

        tree = QTableWidget()
        tree.setColumnCount(4)
        tree.setHorizontalHeaderLabels(["ID", "Название", "Контакты", "Адрес"])
        tree.setSelectionBehavior(QTableWidget.SelectRows)
        tree.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(tree)

        button_layout = QHBoxLayout()

        refresh_button = QPushButton("Обновить")
        refresh_button.clicked.connect(lambda: self.refresh_suppliers(tree))
        button_layout.addWidget(refresh_button)

        add_button = QPushButton("Добавить")
        add_button.clicked.connect(lambda: self.add_supplier(tree))
        button_layout.addWidget(add_button)

        delete_button = QPushButton("Удалить")
        delete_button.clicked.connect(lambda: self.delete_supplier(tree))
        button_layout.addWidget(delete_button)

        layout.addLayout(button_layout)

        window.setLayout(layout)
        self.refresh_suppliers(tree)
        window.exec_()

    def refresh_suppliers(self, tree):
        """Обновляет список поставщиков в таблице."""
        headers = {'Authorization': f'Bearer {self.token}'}

        def task():
            try:
                response = requests.get('http://localhost:5000/suppliers', headers=headers)
                if response.status_code == 200:
                    suppliers = response.json()
                    tree.setRowCount(0)
                    for supplier in suppliers:
                        row = tree.rowCount()
                        tree.insertRow(row)
                        tree.setItem(row, 0, QTableWidgetItem(str(supplier.get('supplier_id', ''))))
                        tree.setItem(row, 1, QTableWidgetItem(supplier.get('supplier_name', '')))
                        tree.setItem(row, 2, QTableWidgetItem(supplier.get('contact_info', '')))
                        tree.setItem(row, 3, QTableWidgetItem(supplier.get('address', '')))
                else:
                    message = response.json().get('message', 'Не удалось загрузить поставщиков.')
                    self.show_error(message)
            except requests.exceptions.ConnectionError:
                self.show_error("Не удалось подключиться к серверу.")
            except Exception as e:
                self.show_error(f"Ошибка при загрузке поставщиков: {e}")

        threading.Thread(target=task).start()

    def add_supplier(self, tree):
        """Открывает окно для добавления нового поставщика."""
        add_window = QDialog(self)
        add_window.setWindowTitle("Добавить поставщика")
        add_window.setModal(True)
        add_window.setFixedSize(400, 300)

        layout = QVBoxLayout()

        name_label = QLabel("Название")
        name_input = QLineEdit()
        layout.addWidget(name_label)
        layout.addWidget(name_input)

        contact_label = QLabel("Контакты")
        contact_input = QLineEdit()
        layout.addWidget(contact_label)
        layout.addWidget(contact_input)

        address_label = QLabel("Адрес")
        address_input = QLineEdit()
        layout.addWidget(address_label)
        layout.addWidget(address_input)

        def save_supplier():
            name = name_input.text().strip()
            contact = contact_input.text().strip()
            address = address_input.text().strip()

            if not name:
                self.show_error("Название поставщика не может быть пустым.")
                return

            payload = {
                'supplier_name': name,
                'contact_info': contact,
                'address': address
            }

            headers = {'Authorization': f'Bearer {self.token}'}

            def task():
                try:
                    response = requests.post('http://localhost:5000/suppliers', headers=headers, json=payload)
                    if response.status_code == 201:
                        self.show_message("Поставщик успешно добавлен!")
                        add_window.accept()
                        self.refresh_suppliers(tree)
                    else:
                        message = response.json().get('message', 'Не удалось добавить поставщика.')
                        self.show_error(message)
                except requests.exceptions.ConnectionError:
                    self.show_error("Не удалось подключиться к серверу.")
                except Exception as e:
                    self.show_error(f"Ошибка при добавлении поставщика: {e}")

            threading.Thread(target=task).start()

        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(save_supplier)
        layout.addWidget(save_button)

        add_window.setLayout(layout)
        add_window.exec_()

    def delete_supplier(self, tree):
        """Удаляет выбранного поставщика."""
        selected_row = tree.currentRow()
        if selected_row < 0:
            self.show_error("Выберите поставщика для удаления.")
            return

        supplier_id = tree.item(selected_row, 0).text()
        supplier_name = tree.item(selected_row, 1).text()

        confirm = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить поставщика '{supplier_name}' (ID: {supplier_id})?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            headers = {'Authorization': f'Bearer {self.token}'}

            def task():
                try:
                    response = requests.delete(f'http://localhost:5000/suppliers/{supplier_id}', headers=headers)
                    if response.status_code == 200:
                        self.show_message("Поставщик успешно удален.")
                        self.refresh_suppliers(tree)
                    else:
                        message = response.json().get('message', 'Не удалось удалить поставщика.')
                        self.show_error(message)
                except requests.exceptions.ConnectionError:
                    self.show_error("Не удалось подключиться к серверу.")
                except Exception as e:
                    self.show_error(f"Ошибка при удалении поставщика: {e}")

            threading.Thread(target=task).start()

    def export_csv(self):
        """Экспортирует данные инвентаря в CSV файл."""
        headers = {'Authorization': f'Bearer {self.token}'}

        def task():
            try:
                response = requests.get('http://localhost:5000/inventory', headers=headers)
                if response.status_code == 200:
                    inventory = response.json()
                    with open("inventory.csv", "w", newline='', encoding='utf-8') as file:
                        writer = csv.writer(file)
                        writer.writerow([
                            "ID", "Название", "Описание", "Цена", "Количество",
                            "Последнее обновление", "Приход за месяц", "Отгрузка за месяц",
                            "Категория", "Поставщик"
                        ])
                        for item in inventory:
                            writer.writerow([
                                item.get('product_id', ''),
                                item.get('name', ''),
                                item.get('description', ''),
                                item.get('price', ''),
                                item.get('quantity', ''),
                                item.get('last_updated', ''),
                                item.get('incoming_this_month', 'Не указано'),
                                item.get('outgoing_this_month', 'Не указано'),
                                item.get('category_name', 'Не указана'),
                                item.get('supplier_name', 'Не указан')
                            ])
                    self.show_message("Данные успешно экспортированы в 'inventory.csv'.")
                else:
                    message = response.json().get('message', 'Ошибка экспорта данных.')
                    self.show_error(message)
            except requests.exceptions.ConnectionError:
                self.show_error("Не удалось подключиться к серверу.")
            except Exception as e:
                self.show_error(f"Ошибка при экспорте данных: {e}")

        threading.Thread(target=task).start()

    def load_categories(self, combobox):
        """Загружает категории из сервера в выпадающий список."""
        headers = {'Authorization': f'Bearer {self.token}'}

        def task():
            try:
                response = requests.get('http://localhost:5000/categories', headers=headers)
                if response.status_code == 200:
                    categories = response.json()
                    combobox.clear()
                    for category in categories:
                        category_id = category.get('category_id')
                        category_name = category.get('category_name')
                        if category_id is not None and category_name:
                            combobox.addItem(f"{category_id} - {category_name}")
                else:
                    message = response.json().get('message', 'Не удалось загрузить категории.')
                    self.show_error(message)
            except requests.exceptions.ConnectionError:
                self.show_error("Не удалось подключиться к серверу.")
            except Exception as e:
                self.show_error(f"Ошибка при загрузке категорий: {e}")

        threading.Thread(target=task).start()

    def load_suppliers(self, combobox):
        """Загружает поставщиков из сервера в выпадающий список."""
        headers = {'Authorization': f'Bearer {self.token}'}

        def task():
            try:
                response = requests.get('http://localhost:5000/suppliers', headers=headers)
                if response.status_code == 200:
                    suppliers = response.json()
                    combobox.clear()
                    for supplier in suppliers:
                        supplier_id = supplier.get('supplier_id')
                        supplier_name = supplier.get('supplier_name')
                        if supplier_id is not None and supplier_name:
                            combobox.addItem(f"{supplier_id} - {supplier_name}")
                else:
                    message = response.json().get('message', 'Не удалось загрузить поставщиков.')
                    self.show_error(message)
            except requests.exceptions.ConnectionError:
                self.show_error("Не удалось подключиться к серверу.")
            except Exception as e:
                self.show_error(f"Ошибка при загрузке поставщиков: {e}")

        threading.Thread(target=task).start()

