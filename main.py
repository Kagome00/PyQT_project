import csv
import sys
import sqlite3

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt

from MusicLib.classes import NewSong, TrackInfoDialog, init_db, DB_PATH

class OlympResult(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Плейлист")
        self.resize(1000, 600)

        init_db()

        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(5)
        self.tableWidget.setHorizontalHeaderLabels([
            "Название песни", "Исполнитель", "Альбом", "Год", "Жанр"
        ])
        self.tableWidget.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.tableWidget.setSelectionMode(
            QTableWidget.SelectionMode.ExtendedSelection
        )

        self.genres = QComboBox()
        self.authors = QComboBox()

        self.delete_btn = QPushButton("Удалить выбранный")
        self.Csv_import = QPushButton("Импортировать CSV")
        self.Csv_export = QPushButton("Экспортировать CSV")
        self.AddTrack = QPushButton("Добавить трек")

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.genres)
        top_layout.addWidget(self.authors)
        top_layout.addWidget(self.Csv_import)
        top_layout.addWidget(self.Csv_export)
        top_layout.addWidget(self.AddTrack)
        top_layout.addWidget(self.delete_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.tableWidget)
        self.setLayout(main_layout)

        self.genres.currentIndexChanged.connect(self.update_table)
        self.authors.currentIndexChanged.connect(self.update_table)

        self.Csv_import.clicked.connect(self.import_csv)
        self.Csv_export.clicked.connect(self.export_csv)
        self.AddTrack.clicked.connect(self.addtrackfunc)
        self.delete_btn.clicked.connect(self.delete_movie)

        self.tableWidget.cellDoubleClicked.connect(
            self.on_track_double_click
        )

        self.load_filters()
        self.update_table()

    def connect_db(self):
        return sqlite3.connect(DB_PATH)

    def load_filters(self):
        previous_genre = self.genres.currentText()
        previous_author = self.authors.currentText()

        with self.connect_db() as db:
            genres = db.execute(
                "SELECT DISTINCT genre FROM songs "
                "WHERE genre IS NOT NULL ORDER BY genre"
            ).fetchall()

            authors = db.execute(
                "SELECT DISTINCT name FROM groups "
                "ORDER BY name"
            ).fetchall()

        self.genres.blockSignals(True)
        self.authors.blockSignals(True)

        self.genres.clear()
        self.genres.addItem("Все жанры")
        self.genres.addItems([str(row[0]) for row in genres])

        self.authors.clear()
        self.authors.addItem("Все исполнители")
        self.authors.addItems([str(row[0]) for row in authors])

        genre_index = self.genres.findText(previous_genre)
        author_index = self.authors.findText(previous_author)

        self.genres.setCurrentIndex(
            genre_index if genre_index >= 0 else 0
        )
        self.authors.setCurrentIndex(
            author_index if author_index >= 0 else 0
        )

        self.genres.blockSignals(False)
        self.authors.blockSignals(False)

    def update_table(self):
        genre = self.genres.currentText()
        author = self.authors.currentText()

        try:
            with self.connect_db() as db:
                total = db.execute(
                    "SELECT COUNT(*) FROM songs"
                ).fetchone()[0]

                print("Путь к базе:", DB_PATH)
                print("Всего песен в базе:", total)

                query = """
                    SELECT
songs.id,
                        songs.title,
                        COALESCE(groups.name, 'Неизвестен'),
                        songs.album,
                        songs.year,
                        songs.genre,
                        songs.cover_path
                    FROM songs
                    LEFT JOIN groups
                        ON songs.group_id = groups.id
                    WHERE 1=1
                """

                params = []

                if genre and genre != "Все жанры":
                    query += " AND songs.genre = ?"
                    params.append(genre)

                if author and author != "Все исполнители":
                    query += " AND groups.name = ?"
                    params.append(author)

                query += """
                    ORDER BY songs.genre, groups.name, songs.title
                """

                rows = db.execute(query, params).fetchall()

            print("Найдено песен:", len(rows))

            self.tableWidget.clearContents()
            self.tableWidget.setRowCount(len(rows))

            for i, row in enumerate(rows):
                song_id = row[0]
                cover_path = row[6]

                values = row[1:6]

                for j, value in enumerate(values):
                    item = QTableWidgetItem(
                        str(value) if value is not None else ""
                    )

                    if j == 0:
                        item.setData(
                            Qt.ItemDataRole.UserRole,
                            {
                                "id": song_id,
                                "cover_path": cover_path
                            }
                        )

                    self.tableWidget.setItem(i, j, item)

            self.tableWidget.resizeColumnsToContents()

        except sqlite3.Error as error:
            QMessageBox.critical(
                self,
                "Ошибка базы данных",
                str(error)
            )

    def addtrackfunc(self):
        dialog = NewSong(self)

        if dialog.exec():
            self.load_filters()
            self.update_table()

    def on_track_double_click(self, row, column):
        self.opentrackfunc(row)

    def opentrackfunc(self, row):
        if self.tableWidget.item(row, 0) is None:
            return

        title = self.tableWidget.item(row, 0).text()
        artist = self.tableWidget.item(row, 1).text()
        album = self.tableWidget.item(row, 2).text()
        year = self.tableWidget.item(row, 3).text()
        genre = self.tableWidget.item(row, 4).text()

        meta = self.tableWidget.item(row, 0).data(
            Qt.ItemDataRole.UserRole
        ) or {}

        cover_path = meta.get("cover_path")

        dialog = TrackInfoDialog(
            title, artist, album, year, genre, cover_path, self
        )
        dialog.exec()

    def import_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите CSV-файл",
            "",
            "CSV (*.csv)"
        )

        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as file:
                sample = file.read(4096)
                file.seek(0)

                try:
                    delimiter = csv.Sniffer().sniff(
                        sample, delimiters=";,\t"
                    ).delimiter
                except csv.Error:
                    delimiter = ";"

                reader = csv.DictReader(file, delimiter=delimiter)

                required = [
                    "Название", "Исполнитель", "Альбом", "Год", "Жанр"
                ]

                if not reader.fieldnames or not all(
                    column in reader.fieldnames for column in required
                ):
                    QMessageBox.warning(
                        self,
                        "Ошибка",
                        "В CSV должны быть столбцы: "
+ ", ".join(required)
                    )
                    return

                added = 0

                with self.connect_db() as db:
                    for row in reader:
                        title = (row.get("Название") or "").strip()
                        author = (row.get("Исполнитель") or "").strip()
                        album = (row.get("Альбом") or "").strip()
                        year_text = (row.get("Год") or "").strip()
                        genre = (row.get("Жанр") or "").strip()

                        if not title or not author or not genre:
                            continue

                        try:
                            year = int(year_text) if year_text else None
                        except ValueError:
                            year = None

                        db.execute(
                            """
                            INSERT OR IGNORE INTO groups (name, genres)
                            VALUES (?, ?)
                            """,
                            (author, genre)
                        )

                        group_id = db.execute(
                            "SELECT id FROM groups WHERE name = ?",
                            (author,)
                        ).fetchone()[0]

                        exists = db.execute(
                            """
                            SELECT id FROM songs
                            WHERE title = ?
                              AND group_id = ?
                              AND COALESCE(album, '') = ?
                            """,
                            (title, group_id, album)
                        ).fetchone()

                        if exists:
                            continue

                        db.execute(
                            """
                            INSERT INTO songs
                            (group_id, title, album, year, genre, cover_path)
                            VALUES (?, ?, ?, ?, ?, NULL)
                            """,
                            (group_id, title, album or None, year, genre)
                        )

                        added += 1

            self.load_filters()
            self.update_table()

            QMessageBox.information(
                self,
                "Импорт завершён",
                f"Добавлено песен: {added}"
            )

        except (OSError, sqlite3.Error, csv.Error) as error:
            QMessageBox.critical(
                self,
                "Ошибка импорта",
                str(error)
            )

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт в CSV",
            "playlist.csv",
            "CSV (*.csv)"
        )

        if not path:
            return

        try:
            with self.connect_db() as db:
                rows = db.execute(
                    """
                    SELECT
                        songs.title,
                        COALESCE(groups.name, 'Неизвестен'),
                        songs.album,
                        songs.year,
                        songs.genre
                    FROM songs
                    LEFT JOIN groups
                        ON songs.group_id = groups.id
                    ORDER BY songs.title
                    """
                ).fetchall()

            with open(
                path, "w", newline="", encoding="utf-8-sig"
            ) as file:
                writer = csv.writer(file, delimiter=";")
                writer.writerow([
                    "Название", "Исполнитель", "Альбом", "Год", "Жанр"
                ])
                writer.writerows(rows)

            QMessageBox.information(
                self,
                "Готово",
                "Плейлист успешно экспортирован!"
            )

        except (OSError, sqlite3.Error) as error:
            QMessageBox.critical(
                self,
"Ошибка экспорта",
                str(error)
            )

    def delete_movie(self):
        selected_rows = self.tableWidget.selectionModel().selectedRows()

        if not selected_rows:
            QMessageBox.warning(
                self,
                "Внимание",
                "Выберите треки для удаления!"
            )
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить выбранные треки ({len(selected_rows)})?",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        ids_to_delete = []

        for index in selected_rows:
            row = index.row()
            item = self.tableWidget.item(row, 0)

            if item is None:
                continue

            meta = item.data(Qt.ItemDataRole.UserRole) or {}
            song_id = meta.get("id")

            if song_id is not None:
                ids_to_delete.append(song_id)

        if not ids_to_delete:
            return

        try:
            with self.connect_db() as db:
                placeholders = ",".join(
                    "?" for _ in ids_to_delete
                )

                db.execute(
                    f"DELETE FROM songs WHERE id IN ({placeholders})",
                    ids_to_delete
                )

                db.execute(
                    """
                    DELETE FROM groups
                    WHERE id NOT IN (
                        SELECT DISTINCT group_id FROM songs
                    )
                    """
                )

            self.load_filters()
            self.update_table()

            QMessageBox.information(
                self,
                "Готово",
                f"Удалено треков: {len(ids_to_delete)}"
            )

        except sqlite3.Error as error:
            QMessageBox.critical(
                self,
                "Ошибка базы данных",
                str(error)
            )

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = OlympResult()
    window.show()

    sys.exit(app.exec())