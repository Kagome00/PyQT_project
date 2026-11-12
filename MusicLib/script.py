import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QPushButton
)

from MusicLib.classes import NewSong, init_db


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        init_db()  # создаём таблицы, если их нет

        self.setWindowTitle("Главное окно")
        self.resize(400, 200)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        btn = QPushButton("Открыть новое окно")
        btn.clicked.connect(self.on_button_click)
        layout.addWidget(btn)

    def on_button_click(self):
        dlg = NewSong(self)
        dlg.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
