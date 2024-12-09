import sys
import sqlite3
import asyncio
import aiohttp
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
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer


class Worker(QObject):
    update_data = pyqtSignal(list)  # Сигнал для передачи данных в интерфейс

    async def fetch_data(self):
        """Асинхронная загрузка данных с сервера"""
        url = "https://jsonplaceholder.typicode.com/posts"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()

    async def save_to_database(self, data):
        """Асинхронное сохранение данных в SQLite"""
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

    async def fetch_and_save(self):
        """Асинхронная загрузка и сохранение данных"""
        data = await self.fetch_data()
        await self.save_to_database(data)
        self.update_data.emit(data)  # Передача данных в интерфейс


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
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.run_async_task)
        self.worker.update_data.connect(self.display_data)

        # Таймер для периодической проверки обновлений
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_updates)
        self.timer.start(10000)  # Проверка каждые 10 секунд

    def start_loading(self):
        """Запуск загрузки данных"""
        self.progress_bar.setValue(0)
        self.button.setEnabled(False)
        self.status_bar.showMessage("Загрузка данных...")
        self.thread.start()

    def run_async_task(self):
        """Асинхронный запуск загрузки данных"""
        asyncio.run(self.worker.fetch_and_save())
        self.thread.quit()

    def display_data(self, data):
        """Отображение данных в таблице"""
        self.table.setRowCount(len(data))  # Устанавливаем количество строк
        for row_idx, post in enumerate(data):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(post["id"])))
            self.table.setItem(row_idx, 1, QTableWidgetItem(post["title"]))
            self.table.setItem(row_idx, 2, QTableWidgetItem(post["body"]))
        self.progress_bar.setValue(100)
        self.button.setEnabled(True)
        self.status_bar.showMessage("Данные успешно загружены!", 3000)

    def check_updates(self):
        """Проверка обновлений данных"""
        self.status_bar.showMessage("Проверка обновлений данных...")
        asyncio.run(self.update_data())

    async def update_data(self):
        """Асинхронная проверка обновлений на сервере"""
        new_data = await self.worker.fetch_data()
        self.display_data(new_data)
        self.status_bar.showMessage("Данные обновлены!", 3000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
