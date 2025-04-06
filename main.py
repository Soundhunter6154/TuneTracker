# main.py
import sys
from PyQt6.QtWidgets import QApplication
from database import create_tables
from gui import MainWindow

if __name__ == "__main__":
    create_tables()  # Initialize database
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
