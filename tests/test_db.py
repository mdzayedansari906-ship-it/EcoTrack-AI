import unittest
import sys
import os
import sqlite3

# Adjust path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db

class TestDatabase(unittest.TestCase):
    def setUp(self):
        # We can temporarily patch the database path or just init and verify tables
        db.init_db()

    def test_database_tables(self):
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        # Verify tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row['name'] for row in cursor.fetchall()]
        
        self.assertIn('users', tables)
        self.assertIn('footprint_logs', tables)
        self.assertIn('achievements', tables)
        self.assertIn('user_achievements', tables)
        self.assertIn('recommendations', tables)
        
        # Verify achievements are seeded
        cursor.execute("SELECT COUNT(*) FROM achievements;")
        count = cursor.fetchone()[0]
        self.assertGreaterEqual(count, 5)
        
        conn.close()

if __name__ == '__main__':
    unittest.main()
