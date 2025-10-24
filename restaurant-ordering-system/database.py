import sqlite3
import os
from datetime import datetime

DATABASE = "restaurant.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if os.path.exists(DATABASE):
        print(f"Database {DATABASE} already exists. Skipping initialization.")
        return

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            category TEXT,
            available INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            items TEXT NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    sample_menu = [
        ("漢堡", 100, "經典牛肉漢堡附薯條", "主菜"),
        ("起司漢堡", 120, "附起司與特製醬料的漢堡", "主菜"),
        ("可樂", 30, "冰可樂", "飲料"),
        ("巧克力蛋糕", 70, "濃郁巧克力蛋糕", "甜點"),
    ]

    cursor.executemany(
        "INSERT INTO menu_items (name, price, description, category) VALUES (?, ?, ?, ?)",
        sample_menu,
    )

    conn.commit()
    conn.close()
    print(f"Database {DATABASE} initialized successfully with sample menu!")
