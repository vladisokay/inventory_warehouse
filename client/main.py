import sys

from PyQt5.QtWidgets import QApplication

from client.inventory_window  import InventoryApp
from client.login_window import LoginWindow


def on_login_success(token):
    """Обработчик успешного входа."""
    global inventory_window  # Делаем объект глобальным, чтобы он не уничтожался
    inventory_window = InventoryApp(token)  # Создаем окно управления складом
    inventory_window.show()  # Показываем главное окно

if __name__ == "__main__":
    app = QApplication(sys.argv)


    # Создаем окно авторизации
    login_window = LoginWindow(on_login_success)
    login_window.show()

    sys.exit(app.exec_())  # Запуск главного цикла приложения
