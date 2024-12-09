import sys
import sqlite3
import asyncio
import aiohttp
import logging
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QProgressBar,
    QStatusBar,
)
from PyQt5.QtCore import QThread, pyqtSignal


class StatusBarLogger(logging.Handler):
    """Кастомный обработчик логов для отправки в статус-бар"""

    def __init__(self, status_bar):
        super().__init__()
        self.status_bar = status_bar

    def emit(self, record):
        """Передаем лог-сообщение в статус-бар"""
        msg = self.format(record)
        self.status_bar.showMessage(msg, 3000)


class Worker(QThread):
    update_data = pyqtSignal(list)  # Сигнал для передачи данных в интерфейс
    update_progress = pyqtSignal(int)  # Сигнал для обновления прогресс-бара
    update_status = pyqtSignal(str)  # Сигнал для обновления состояния статус-бара

    def __init__(self):
        super().__init__()

    async def fetch_data(self):
        """Асинхронная загрузка данных с сервера с обновлением прогресса"""
        self.update_status.emit("Загрузка данных с сервера...")  # Обновление статуса
        logging.info("Начало загрузки данных с сервера...")

        # Симуляция загрузки с прогрессом
        for i in range(0, 101, 10):  # Обновляем прогресс каждое 10%
            self.update_progress.emit(i)  # Обновление прогресса
            await asyncio.sleep(0.5)  # Искусственная задержка для симуляции загрузки

        url = "https://jsonplaceholder.typicode.com/posts"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()

        logging.info("Загрузка данных завершена.")
        self.update_status.emit("Загрузка данных завершена.")  # Обновление статуса
        return data

    async def save_to_database(self, data):
        """Асинхронное сохранение данных в SQLite"""
        self.update_status.emit("Сохранение данных в базу данных...")  # Обновление статуса
        logging.info("Начало сохранения данных в базу данных...")

        # Симуляция сохранения с прогрессом
        for i in range(0, 101, 10):  # Обновляем прогресс каждое 10%
            self.update_progress.emit(i)  # Обновление прогресса
            await asyncio.sleep(0.5)  # Искусственная задержка для симуляции сохранения

        conn = sqlite3.connect("posts.db")
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                title TEXT,
                body TEXT
            )
        """
        )
        for post in data:
            cursor.execute(
                "INSERT OR REPLACE INTO posts (id, title, body) VALUES (?, ?, ?)",
                (post["id"], post["title"], post["body"]),
            )
        conn.commit()
        conn.close()
        logging.info("Данные успешно сохранены в базу данных.")
        self.update_status.emit("Данные успешно сохранены.")  # Обновление статуса

    def run(self):
        """Запуск асинхронной загрузки данных и их сохранение в фоновом потоке"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.update_progress.emit(0)  # Начало загрузки
        data = loop.run_until_complete(self.fetch_data())
        loop.run_until_complete(self.save_to_database(data))
        self.update_progress.emit(100)  # Завершение загрузки
        self.update_data.emit(data)  # Передача данных в UI


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Асинхронное обновление данных")

        # Основные элементы интерфейса
        self.layout = QVBoxLayout()
        self.button = QPushButton("Загрузить данные")
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "Body"])
        self.progress_bar = QProgressBar()
        self.status_bar = QStatusBar()

        self.layout.addWidget(self.button)
        self.layout.addWidget(self.table)
        self.layout.addWidget(self.progress_bar)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)
        self.setStatusBar(self.status_bar)

        # Соединяем кнопку с началом работы
        self.button.clicked.connect(self.start_loading)

        # Подготовка фонового потока и рабочего объекта
        self.worker = Worker()
        self.worker.update_data.connect(self.display_data)
        self.worker.update_progress.connect(self.update_progress)
        self.worker.update_status.connect(self.update_status_bar)

        # Настройка логирования
        log_handler = StatusBarLogger(self.status_bar)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.INFO)

    def start_loading(self):
        """Запуск загрузки данных"""
        self.progress_bar.setValue(0)
        self.button.setEnabled(False)
        logging.info("Запуск загрузки данных...")
        self.worker.start()  # Запуск фонового потока

    def update_progress(self, progress):
        """Обновление прогресса"""
        self.progress_bar.setValue(progress)

    def update_status_bar(self, message):
        """Обновление состояния статус-бара"""
        self.status_bar.showMessage(message, 3000)

    def display_data(self, data):
        """Отображение данных в таблице"""
        self.table.setRowCount(len(data))  # Устанавливаем количество строк
        for row_idx, post in enumerate(data):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(post["id"])))
            self.table.setItem(row_idx, 1, QTableWidgetItem(post["title"]))
            self.table.setItem(row_idx, 2, QTableWidgetItem(post["body"]))
        self.button.setEnabled(True)
        logging.info("Данные успешно загружены!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
