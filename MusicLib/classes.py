import sqlite3
import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel,
    QPushButton, QLineEdit, QMessageBox, QFileDialog
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music.db")


def init_db():
    # Создаёт таблицы, если их нет, и добавляет колонку cover_path при необходимости.
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                genres TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                album TEXT,
                year INTEGER,
                genre TEXT NOT NULL,
                cover_path TEXT,
                FOREIGN KEY (group_id) REFERENCES groups(id)
            )
        """)
        try:
            db.execute("ALTER TABLE songs ADD COLUMN cover_path TEXT")
        except sqlite3.OperationalError:
            pass


# Окно добавления песни
class NewSong(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Информация о песне")
        self.resize(320, 520)

        self.cover_path = None

        self.SongNameLabel = QLabel("Название песни:")
        self.SongName = QLineEdit()

        self.SongAuthorLabel = QLabel("Исполнитель:")
        self.SongAuthor = QLineEdit()

        self.SongAlbumLabel = QLabel("Альбом:")
        self.SongAlbum = QLineEdit()

        self.SongYearLabel = QLabel("Год:")
        self.SongYear = QLineEdit()

        self.SongGenreLabel = QLabel("Жанр:")
        self.SongGenre = QLineEdit()

        self.CoverLabel = QLabel("Обложка не выбрана")
        self.CoverLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.CoverLabel.setFixedHeight(140)
        self.CoverLabel.setStyleSheet("border: 1px solid gray;")

        self.CoverButton = QPushButton("Выбрать картинку")
        self.CoverButton.clicked.connect(self.choose_cover)

        self.ClearCoverButton = QPushButton("Убрать картинку")
        self.ClearCoverButton.clicked.connect(self.clear_cover)

        self.SaveButton = QPushButton("Сохранить")
        self.CancelButton = QPushButton("Отмена")

        layout = QVBoxLayout(self)

        layout.addWidget(self.CoverLabel)
        layout.addWidget(self.CoverButton)
        layout.addWidget(self.ClearCoverButton)

        layout.addWidget(self.SongNameLabel)
        layout.addWidget(self.SongName)
        layout.addWidget(self.SongAuthorLabel)
        layout.addWidget(self.SongAuthor)
        layout.addWidget(self.SongAlbumLabel)
        layout.addWidget(self.SongAlbum)
        layout.addWidget(self.SongYearLabel)
        layout.addWidget(self.SongYear)
        layout.addWidget(self.SongGenreLabel)
        layout.addWidget(self.SongGenre)
        layout.addWidget(self.SaveButton)
        layout.addWidget(self.CancelButton)

        self.SaveButton.clicked.connect(self.save_song)
        self.CancelButton.clicked.connect(self.reject)

    # Выбор файла для обложки
    def choose_cover(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите обложку",
            "",
            "Изображения (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if not path:
            return

        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, "Ошибка", "Не удалось открыть изображение")
            return

        self.cover_path = os.path.abspath(path)
        self.CoverLabel.setPixmap(
            pixmap.scaled(
                self.CoverLabel.width(),
                self.CoverLabel.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )

    def clear_cover(self):
        self.cover_path = None
        self.CoverLabel.clear()
        self.CoverLabel.setText("Обложка не выбрана")

    # Сохранение заполненных ранее переменных и внесение их в бд
    def save_song(self):
        name = self.SongName.text().strip()
        author = self.SongAuthor.text().strip()
        album = self.SongAlbum.text().strip()
        year = self.SongYear.text().strip()
        genre = self.SongGenre.text().strip()

        if not name or not author or not genre:
            QMessageBox.warning(
                self, "Ошибка",
                "Заполните название, исполнителя и жанр!"
            )
            return

        if year:
            try:
                year = int(year)
            except ValueError:
                QMessageBox.warning(self, "Ошибка", "Год должен быть числом!")
                return
        else:
            year = None

        try:
            with sqlite3.connect(DB_PATH) as db:
                result = db.execute(
                    "SELECT id FROM groups WHERE name = ?",
                    (author,)
                ).fetchone()

                if result:
                    author_id = result[0]
                else:
                    cursor = db.execute(
                        "INSERT INTO groups (name, genres) VALUES (?, ?)",
                        (author, genre)
                    )
                    author_id = cursor.lastrowid

                db.execute("""
                    INSERT INTO songs
                    (group_id, title, album, year, genre, cover_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (author_id, name, album, year, genre, self.cover_path))

            QMessageBox.information(self, "Успех", "Песня успешно добавлена!")
            self.accept()

        except sqlite3.Error as error:
            QMessageBox.critical(self, "Ошибка базы данных", str(error))


# Окно с информацией о песне
class TrackInfoDialog(QDialog):
    def __init__(self, title, artist, album, year, genre,
                 cover_path=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle(f"Трек: {title}")
        self.resize(320, 420)

        layout = QVBoxLayout(self)

        if cover_path and os.path.exists(cover_path):
            pixmap = QPixmap(cover_path)
            if not pixmap.isNull():
                cover = QLabel()
                cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cover.setPixmap(
                    pixmap.scaled(
                        260, 260,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
                layout.addWidget(cover)
        else:
            no_cover = QLabel("Обложка отсутствует")
            no_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_cover.setStyleSheet("color: gray;")
            layout.addWidget(no_cover)

        layout.addWidget(QLabel(f"<b>Название:</b> {title}"))
        layout.addWidget(QLabel(f"<b>Исполнитель:</b> {artist}"))
        layout.addWidget(QLabel(f"<b>Альбом:</b> {album or '—'}"))
        layout.addWidget(QLabel(f"<b>Год:</b> {year or '—'}"))
        layout.addWidget(QLabel(f"<b>Жанр:</b> {genre}"))

        btn = QPushButton("Закрыть")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
