import sqlite3
import os
import json
from datetime import datetime
import numpy as np
from sentence_transformers import SentenceTransformer

class MemoryManager:
    def __init__(self, db_path="memory.db"):
        self.db_path = db_path
        self._model = None # Lazy load
        self._init_db()

    @property
    def model(self):
        if self._model is None:
            # Lightweight semantic model
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._model

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for chat messages
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table for user facts (Personal RAG)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT,
                category TEXT,
                embedding BLOB,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Table for dynamic automations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS automations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                trigger_type TEXT,
                trigger_config TEXT,
                action_type TEXT,
                action_config TEXT,
                last_run DATETIME,
                enabled INTEGER DEFAULT 1
            )
        ''')
        # Table for system configuration (Passcode, etc.)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    def add_message(self, chat_id, role, content):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
            (chat_id, role, content)
        )
        conn.commit()
        conn.close()

    def get_history(self, chat_id, limit=10):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY timestamp DESC LIMIT ?",
            (chat_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        # Return in correct chronological order
        return [{"role": r, "content": c} for r, c in reversed(rows)]

    def clear_history(self, chat_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()

    def save_fact(self, fact, category="general"):
        # Generate embedding for the fact
        embedding = self.model.encode(fact).tobytes()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_facts (fact, category, embedding) VALUES (?, ?, ?)",
            (fact, category, embedding)
        )
        conn.commit()
        conn.close()

    def get_relevant_facts(self, query, limit=5):
        """Semantic search using Vector Embeddings (Cosine Similarity)."""
        query_embedding = self.model.encode(query)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, fact, embedding FROM user_facts")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows: return []

        similarities = []
        for row_id, fact, emb_blob in rows:
            if emb_blob:
                fact_embedding = np.frombuffer(emb_blob, dtype=np.float32)
                # Simple cosine similarity: (A dot B) / (||A|| * ||B||)
                # SentenceTransformer embeddings are usually normalized, so simple dot product works
                score = np.dot(query_embedding, fact_embedding)
                similarities.append((fact, score))
        
        # Sort by similarity score descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in similarities[:limit]]
    def get_all_facts(self, category=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if category:
            cursor.execute("SELECT id, fact, category, timestamp FROM user_facts WHERE category = ? ORDER BY timestamp DESC", (category,))
        else:
            cursor.execute("SELECT id, fact, category, timestamp FROM user_facts ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "fact": r[1], "category": r[2], "timestamp": r[3]} for r in rows]

    def delete_fact(self, fact_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_facts WHERE id = ?", (fact_id,))
        conn.commit()
        conn.close()

    # --- Automation Management ---
    def add_automation(self, name, t_type, t_config, a_type, a_config):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO automations (name, trigger_type, trigger_config, action_type, action_config) VALUES (?, ?, ?, ?, ?)",
            (name, t_type, json.dumps(t_config), a_type, json.dumps(a_config))
        )
        conn.commit()
        conn.close()

    def get_automations(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM automations")
        rows = cursor.fetchall()
        conn.close()
        return [{
            "id": r[0], "name": r[1], "trigger_type": r[2], 
            "trigger_config": json.loads(r[3]), "action_type": r[4], 
            "action_config": json.loads(r[5]), "last_run": r[6], "enabled": r[7]
        } for r in rows]

    def delete_automation(self, auto_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM automations WHERE id = ?", (auto_id,))
        conn.commit()
        conn.close()

    def update_automation_run_time(self, auto_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE automations SET last_run = CURRENT_TIMESTAMP WHERE id = ?", (auto_id,))
        conn.commit()
        conn.close()

    # --- System Settings (Generic Key-Value) ---
    def set_setting(self, key, value):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()

    def get_setting(self, key):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    # --- Security Settings ---
    def set_passcode(self, passcode_hash):
        self.set_setting('passcode', passcode_hash)

    def get_passcode(self):
        return self.get_setting('passcode')
