import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ecotrack.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        daily_goal REAL DEFAULT 20.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    # Create footprint_logs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS footprint_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        transport_miles REAL DEFAULT 0.0,
        transport_type TEXT DEFAULT 'active',
        electricity_kwh REAL DEFAULT 0.0,
        diet_type TEXT DEFAULT 'average',
        carbon_emissions REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(user_id, date)
    );
    ''')

    # Create achievements table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        badge_icon TEXT NOT NULL,
        target_type TEXT NOT NULL,
        target_value INTEGER NOT NULL
    );
    ''')

    # Create user_achievements table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        achievement_id INTEGER NOT NULL,
        unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(achievement_id) REFERENCES achievements(id) ON DELETE CASCADE,
        UNIQUE(user_id, achievement_id)
    );
    ''')

    # Create recommendations table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        suggestion TEXT NOT NULL,
        completed INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # Seed achievements if they don't exist
    default_achievements = [
        ('first_log', 'First Footprint', 'Log your carbon footprint for the first time.', '👣', 'log_count', 1),
        ('eco_traveler', 'Eco Traveler', 'Log active transport or public transit.', '🚴', 'eco_commute', 1),
        ('plant_powered', 'Plant-Based Power', 'Log a vegetarian or vegan diet style.', '🥗', 'diet_type', 1),
        ('carbon_saver', 'Carbon Saver', 'Keep your daily emissions under 10 kg CO2.', '🌱', 'low_emission', 1),
        ('streak_3', 'Green Streak', 'Log your footprint for 3 consecutive days.', '🔥', 'streak', 3),
        ('task_finisher', 'Action Taker', 'Complete your first eco recommendation.', '✅', 'completed_recommendations', 1)
    ]

    for achievement in default_achievements:
        cursor.execute('''
        INSERT OR IGNORE INTO achievements (key, name, description, badge_icon, target_type, target_value)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', achievement)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
