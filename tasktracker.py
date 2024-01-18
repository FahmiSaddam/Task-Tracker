import sys
import mysql.connector
from datetime import datetime, timedelta
from PyQt6.QtCore import Qt, QTimer, QDate, QModelIndex
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QLineEdit, QTextEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QTreeView, QWidget, QMessageBox, QDialog, QSystemTrayIcon, QCalendarWidget 
    )
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QIcon, QGuiApplication


class TodoApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set koneksi database di sini
        self.db = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='data'
        )
        self.cursor = self.db.cursor()

        self.setWindowTitle("Task Tracker App")
        self.set_app_size()
        self.setStyleSheet("QMainWindow { background-color: #D3D3D3; }")
        self.create_treeview_model()

        self.task_times = {}
        self.task_entry = QLineEdit(self)
        self.task_entry.setPlaceholderText("Masukkan Nama Tugas")
        self.task_details_entry = QTextEdit(self)
        self.task_details_entry.setPlaceholderText("Masukkan Detail Tugas")

        self.add_task_button = QPushButton("Tambah Tugas", self)
        self.add_task_button.clicked.connect(self.add_task)

        self.todo_treeview = QTreeView(self)
        self.todo_treeview.setModel(self.treeview_model)
        self.todo_treeview.header().setStretchLastSection(True)
        
        self.todo_treeview.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)

        self.delete_task_button = QPushButton("Hapus Tugas", self)
        self.delete_task_button.clicked.connect(self.delete_task)

        self.edit_task_button = QPushButton("Edit Tugas", self)
        self.edit_task_button.clicked.connect(self.edit_task)

        self.entry_date_calendar = QCalendarWidget(self)
        self.last_updated_calendar = QCalendarWidget(self)

        top_layout = QGridLayout()
        top_layout.addWidget(QLabel("Masukkan Nama Tugas:"), 0, 0)
        top_layout.addWidget(self.task_entry, 0, 1)
        top_layout.addWidget(self.add_task_button, 0, 2)
        top_layout.addWidget(QLabel("Detail Tugas:"), 1, 0)
        top_layout.addWidget(self.task_details_entry, 1, 1, 1, 2)
        top_layout.addWidget(QLabel("Tanggal Masuk Tugas:"), 2, 0)
        top_layout.addWidget(self.entry_date_calendar, 2, 1)
        top_layout.addWidget(QLabel("Tanggal Terakhir Dikumpulkan:"), 3, 0)
        top_layout.addWidget(self.last_updated_calendar, 3, 1)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.delete_task_button)
        button_layout.addWidget(self.edit_task_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.todo_treeview)
        main_layout.addLayout(button_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.check_overdue_tasks_timer = QTimer()
        self.check_overdue_tasks_timer.timeout.connect(self.check_overdue_tasks)
        self.check_overdue_tasks_timer.start(60 * 60 * 1000)  # Check every 1 hour
        
        self.todo_treeview.setEditTriggers(QTreeView.EditTrigger.DoubleClicked | QTreeView.EditTrigger.SelectedClicked)
        self.todo_treeview.clicked.connect(self.treeview_item_clicked)
        self.selected_row = None  # Menyimpan indeks baris yang dipilih
        self.populate_treeview_from_db()
        
        self.search_entry = QLineEdit(self)
        self.search_entry.setPlaceholderText("Cari Tugas")
        self.search_entry.textChanged.connect(self.search_task_auto)

        self.search_button = QPushButton("Cari", self)
        self.search_button.clicked.connect(self.search_task)

        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_entry)
        search_layout.addWidget(self.search_button)
        main_layout.addLayout(search_layout)


        
    def set_app_size(self):
        # Mendapatkan ukuran layar utama
        primary_screen = QGuiApplication.primaryScreen()
        screen_geometry = primary_screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # Atur ukuran layar aplikasi (misalnya, 80% dari ukuran layar)
        app_width = int(screen_width * 0.8)
        app_height = int(screen_height * 0.8)
        self.resize(app_width, app_height)
        
    def search_task(self):
        search_text = self.search_entry.text().strip().lower()
        model = self.treeview_model

        # Hapus hasil pencarian sebelumnya dari QTreeView
        model.removeRows(0, model.rowCount())

        sql = "SELECT nama_tugas, detail_tugas, tanggal_masuk, tanggal_terakhir FROM tasktracker WHERE LOWER(nama_tugas) LIKE %s"
        value = f"%{search_text}%"

        self.cursor.execute(sql, (value,))
        records = self.cursor.fetchall()
        for row in records:
            task, details, entry_date, last_updated = row
            entry_date = entry_date.strftime("%Y-%m-%d") if entry_date else ""
            last_updated = last_updated.strftime("%Y-%m-%d") if last_updated else ""
            self.add_treeview_item(task, details, QDate.fromString(entry_date, "yyyy-MM-dd"), QDate.fromString(last_updated, "yyyy-MM-dd"))

        self.todo_treeview.selectionModel().clearSelection()

    def search_task_auto(self):
        search_text = self.search_entry.text().strip().lower()
        model = self.treeview_model

        # Hapus hasil pencarian sebelumnya dari QTreeView
        model.removeRows(0, model.rowCount())

        if not search_text:
            self.populate_treeview_from_db()
            return

        sql = "SELECT nama_tugas, detail_tugas, tanggal_masuk, tanggal_terakhir FROM tasktracker WHERE LOWER(nama_tugas) LIKE %s"
        value = f"%{search_text}%"

        self.cursor.execute(sql, (value,))
        records = self.cursor.fetchall()
        for row in records:
            task, details, entry_date, last_updated = row
            entry_date = entry_date.strftime("%Y-%m-%d") if entry_date else ""
            last_updated = last_updated.strftime("%Y-%m-%d") if last_updated else ""
            self.add_treeview_item(task, details, QDate.fromString(entry_date, "yyyy-MM-dd"), QDate.fromString(last_updated, "yyyy-MM-dd"))

        self.todo_treeview.selectionModel().clearSelection()

    def create_treeview_model(self):
        self.treeview_model = QStandardItemModel()
        self.treeview_model.setHorizontalHeaderLabels(['Tugas', 'Detail', 'Tanggal Masuk Tugas', 'Tanggal Terakhir Dikumpulkan'])
    
    def add_treeview_item(self, task, details, entry_date, last_updated):
        model = self.todo_treeview.model()
        item_task = QStandardItem(task)
        item_task.setEditable(False)
        item_details = QStandardItem(details)
        item_details.setEditable(False)
        item_entry_date = QStandardItem(entry_date.toString("yyyy-MM-dd"))
        item_entry_date.setEditable(False)
        item_last_updated = QStandardItem(last_updated.toString("yyyy-MM-dd"))
        item_last_updated.setEditable(False)
        model.appendRow([item_task, item_details, item_entry_date, item_last_updated])

        # Set initial column widths
        for column in range(model.columnCount()):
            self.todo_treeview.setColumnWidth(column, 150)  # Adjust the width based on your preference

    def populate_treeview_from_db(self):
        sql = "SELECT nama_tugas, detail_tugas, tanggal_masuk, tanggal_terakhir FROM tasktracker"
        self.cursor.execute(sql)
        records = self.cursor.fetchall()
        for row in records:
            task, details, entry_date, last_updated = row
            entry_date = entry_date.strftime("%Y-%m-%d") if entry_date else ""
            last_updated = last_updated.strftime("%Y-%m-%d") if last_updated else ""
            self.add_treeview_item(task, details, QDate.fromString(entry_date, "yyyy-MM-dd"), QDate.fromString(last_updated, "yyyy-MM-dd"))
        
        self.todo_treeview.selectionModel().clearSelection()

    def treeview_item_clicked(self, index):
        self.selected_row = index.row()  # Simpan indeks baris yang dipilih

        # Menangani pengeditan langsung
        if self.selected_row is not None:
            self.todo_treeview.edit(index)

    def check_overdue_tasks(self):
        now = datetime.now()
        tasks_to_delete = []  # List untuk menyimpan tugas yang akan dihapus

        for task, last_updated in self.task_times.items():
            delta = now - last_updated
            if delta > timedelta(days=1):  # Jika tanggal terakhir diperbarui sudah terlewati 1 hari (contoh: bisa disesuaikan dengan interval waktu yang diinginkan)
                tasks_to_delete.append(task)

        for task in tasks_to_delete:
            # Hapus tugas dari database
            sql = "DELETE FROM tasktracker WHERE nama_tugas = %s"
            try:
                self.cursor.execute(sql, (task,))
                self.db.commit()
                del self.task_times[task]
            except Exception as e:
                self.db.rollback()
                QMessageBox.warning(self, "Peringatan", f"Gagal menghapus tugas: {str(e)}")

            # Hapus tugas dari QTreeView
            for row in range(self.treeview_model.rowCount()):
                index = self.treeview_model.index(row, 0)
                if index.data(Qt.ItemDataRole.DisplayRole) == task:
                    self.treeview_model.removeRow(row)
                    break

        # Set timer kembali untuk memeriksa tugas yang terlewati berikutnya
        self.check_overdue_tasks_timer.start(60 * 60 * 1000)  # Check every 1 hour again
        
    def add_task(self):
        task = self.task_entry.text().strip()
        details = self.task_details_entry.toPlainText().strip()
        entry_date = self.entry_date_calendar.selectedDate()
        last_updated = self.last_updated_calendar.selectedDate()

        if not task or not details or entry_date.isNull() or last_updated.isNull():
            QMessageBox.warning(self, "Peringatan", "Harap isi semua kolom.")
            return
        
        sql = "INSERT INTO tasktracker (nama_tugas, detail_tugas, tanggal_masuk, tanggal_terakhir) VALUES (%s, %s, %s, %s)"
        values = (task, details, entry_date.toString("yyyy-MM-dd"), last_updated.toString("yyyy-MM-dd"))
        try:
            self.cursor.execute(sql, values)
            self.db.commit()
            QMessageBox.information(self, "Informasi", "Tugas berhasil ditambahkan ke database.")
        except Exception as e:
            self.db.rollback()
            QMessageBox.warning(self, "Peringatan", f"Terjadi kesalahan: {str(e)}")

        self.add_treeview_item(task, details, entry_date, last_updated)
        self.task_times[task] = datetime.now()
        self.task_entry.clear()
        self.task_details_entry.clear()

    def delete_task(self):
        selected_indexes = self.todo_treeview.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Peringatan", "Pilih sebuah tugas untuk dihapus.")
            return

        row = selected_indexes[0].row()
        task = self.todo_treeview.model().item(row, 0).text()

        sql = "DELETE FROM tasktracker WHERE nama_tugas = %s"
        try:
            self.cursor.execute(sql, (task,))
            self.db.commit()
            del self.task_times[task]
            self.todo_treeview.model().removeRow(row)  # Menghapus baris dari QTreeView setelah dihapus dari database
            QMessageBox.information(self, "Informasi", "Tugas berhasil dihapus dari database.")
        except Exception as e:
            self.db.rollback()
            QMessageBox.warning(self, "Peringatan", f"Terjadi kesalahan: {str(e)}")

        # Kembali memuat ulang data dari database setelah penghapusan
        self.populate_treeview_from_db()


    def edit_task(self):
        selected_indexes = self.todo_treeview.selectedIndexes()
        if selected_indexes:
            row = selected_indexes[0].row()
            old_task = self.todo_treeview.model().item(row, 0).text()
            old_details = self.todo_treeview.model().item(row, 1).text()
            old_entry_date = self.todo_treeview.model().item(row, 2).text()
            old_last_updated = self.todo_treeview.model().item(row, 3).text()

            edit_window = QDialog(self)
            edit_window.setWindowTitle("Edit Tugas")
            edit_window.setFixedSize(400, 300)

            layout = QVBoxLayout(edit_window)

            edit_task_entry = QLineEdit(edit_window)
            edit_task_entry.setText(old_task)
            layout.addWidget(edit_task_entry)

            edit_details_entry = QTextEdit(edit_window)
            edit_details_entry.setPlainText(old_details)
            layout.addWidget(edit_details_entry)

            entry_date_label = QLabel("Tanggal Masuk Tugas:", edit_window)
            layout.addWidget(entry_date_label)
            entry_date_calendar = QCalendarWidget(edit_window)
            entry_date_calendar.setSelectedDate(QDate.fromString(old_entry_date, "yyyy-MM-dd"))
            layout.addWidget(entry_date_calendar)

            last_updated_label = QLabel("Tanggal Terakhir Dikumpulkan:", edit_window)
            layout.addWidget(last_updated_label)
            last_updated_calendar = QCalendarWidget(edit_window)
            last_updated_calendar.setSelectedDate(QDate.fromString(old_last_updated, "yyyy-MM-dd"))
            layout.addWidget(last_updated_calendar)

            save_button = QPushButton("Simpan", edit_window)

            def save_edited_task():
                new_task = edit_task_entry.text().strip()
                new_details = edit_details_entry.toPlainText().strip()
                new_entry_date = entry_date_calendar.selectedDate()
                new_last_updated = last_updated_calendar.selectedDate()

                if not new_task or not new_details or new_entry_date.isNull() or new_last_updated.isNull():
                    QMessageBox.warning(edit_window, "Peringatan", "Harap isi semua kolom.")
                    return

                self.todo_treeview.model().item(row, 0).setText(new_task)
                self.todo_treeview.model().item(row, 1).setText(new_details)
                self.todo_treeview.model().item(row, 2).setText(new_entry_date.toString("yyyy-MM-dd"))
                self.todo_treeview.model().item(row, 3).setText(new_last_updated.toString("yyyy-MM-dd"))
                del self.task_times[old_task]
                self.task_times[new_task] = datetime.now()

                sql = "UPDATE tasktracker SET nama_tugas = %s, detail_tugas = %s, tanggal_masuk = %s, tanggal_terakhir = %s WHERE nama_tugas = %s"
                values = (new_task, new_details, new_entry_date.toString("yyyy-MM-dd"), new_last_updated.toString("yyyy-MM-dd"), old_task)
                try:
                    self.cursor.execute(sql, values)
                    self.db.commit()
                    QMessageBox.information(self, "Informasi", "Tugas berhasil diperbarui di database.")
                    edit_window.accept()
                except Exception as e:
                    self.db.rollback()
                    QMessageBox.warning(self, "Peringatan", f"Terjadi kesalahan: {str(e)}")

            save_button.clicked.connect(save_edited_task)
            layout.addWidget(save_button)

            edit_window.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app_icon = QIcon('icons8-check-64.ico')
    app.setWindowIcon(app_icon)
    tray_icon = QSystemTrayIcon(app_icon, app)
    tray_icon.show()
    window = TodoApp()
    window.show()
    sys.exit(app.exec())
