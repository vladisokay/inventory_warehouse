# Inventory Management System

## Описание проекта

Этот проект представляет собой систему управления складом, которая позволяет отслеживать товары, их категории, количество на складе и историю взаимодействия с поставщиками. Он предоставляет удобный интерфейс для администраторов, работников и пользователей для взаимодействия с данными склада.

Проект состоит из двух частей:
1. **Backend**: Flask API для взаимодействия с клиентом и базой данных.
2. **Frontend**: PyQt приложение для взаимодействия с товаром на складе через графический интерфейс.

Проект позволяет выполнять следующие действия:
- Управление категориями товаров.
- Управление поставщиками.
- Управление пользователями и ролями.
- Просмотр и редактирование данных склада.
- Ведение учета товара


## Стек технологий

- **Backend**: 
    - Flask (Python Web Framework)
    - PostgreSQL (СУБД)
    - SQLAlchemy (ORM)
    - psycopg2 (PostgreSQL Python клиент)
  
- **Frontend**: 
    - PyQt (для создания графического интерфейса клиентского приложения)

- **Дополнительно**:
    - Requests (для выполнения HTTP запросов)
    - Mermaid/PlantUML для визуализации диаграмм

## Установка

### Требования

1. Python 3.7+
2. PostgreSQL 12+ (или выше)

### Шаги для установки

1. **Клонирование репозитория**

   Склонируйте репозиторий на свой локальный компьютер:

   ```bash
   git clone https://github.com/vladisokay/inventory_warehouse.git
   cd inventory_warehouse
2. **Установка зависимостей**

    Установите зависимости проекта с помощью pip:

   ```bash
   pip install -r requirements.txt

3. **Настройка базы данных**

    Создайте базу данных и выполните скрипт для инициализации базы данных.

    Создайте базу данных в PostgreSQL:

    ```sql
     createdb inventory_db
   ```
   Настройте подключение в файле back/app.py:
    
    ```python
        app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/database_name'
   ```
4. **Запустите скрипт инициализации базы данных:**
    


5. **Запустите сервер:**

   ```bash
    python back/app.py
   ```
   
6. **Запустите клиентское приложение**
   ```python
   python client/main.py 
   ```
