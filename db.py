import sqlite3
import logging

# Set up logging
logging.basicConfig(filename='project.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_FILE = "chat_history.db"

def init_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        logging.info("Database initialized successfully.")
    except Exception as e:
        logging.error(f"Error initializing database: {e}")
    finally:
        conn.close()

def insert_message(session_id, role, content):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO chats (session_id, role, content) VALUES (?, ?, ?)", (session_id, role, content))
        conn.commit()
        logging.info(f"Inserted message | Session: {session_id} | Role: {role} | Content: {content[:50]}")
    except Exception as e:
        logging.error(f"Error inserting message: {e}")
    finally:
        conn.close()

def get_messages(session_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT role, content FROM chats WHERE session_id = ? ORDER BY timestamp", (session_id,))
        messages = [{"role": row[0], "content": row[1]} for row in c.fetchall()]
        logging.info(f"Fetched {len(messages)} messages for session: {session_id}")
        return messages
    except Exception as e:
        logging.error(f"Error getting messages for session {session_id}: {e}")
        return []
    finally:
        conn.close()

def delete_session(session_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM chats WHERE session_id = ?", (session_id,))
        conn.commit()
        logging.info(f"Deleted session: {session_id}")
    except Exception as e:
        logging.error(f"Error deleting session {session_id}: {e}")
    finally:
        conn.close()

def get_all_sessions():
    session_titles = {}
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        c.execute("""
            SELECT session_id, MAX(timestamp) as last_active
            FROM chats
            GROUP BY session_id
            ORDER BY last_active DESC
        """)
        session_time_map = {row[0]: row[1] for row in c.fetchall()}

        for session_id in session_time_map.keys():
            c.execute("""
                SELECT content FROM chats
                WHERE session_id = ? AND role = 'user'
                ORDER BY timestamp ASC
                LIMIT 1
            """, (session_id,))
            row = c.fetchone()
            title = row[0][:40] + "..." if row and len(row[0]) > 40 else row[0] if row else "(No Title)"
            session_titles[session_id] = title

        logging.info(f"Retrieved {len(session_titles)} sessions.")
    except Exception as e:
        logging.error(f"Error getting all sessions: {e}")
    finally:
        conn.close()
    return session_titles

def get_cached_response(user_input):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            SELECT a.content 
            FROM chats u 
            JOIN chats a ON u.session_id = a.session_id 
            WHERE u.role = 'user' AND a.role = 'assistant'
              AND u.content = ?
              AND a.timestamp > u.timestamp
            ORDER BY a.timestamp ASC
            LIMIT 1
        """, (user_input,))
        row = c.fetchone()
        if row:
            logging.info(f"Cached response found for input: {user_input[:50]}")
        return row[0] if row else None
    except Exception as e:
        logging.error(f"Error getting cached response: {e}")
        return None
    finally:
        conn.close()

def delete_last_assistant_message(session_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            DELETE FROM chats 
            WHERE session_id = ? AND role = 'assistant' 
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (session_id,))
        conn.commit()
        logging.info(f"Deleted last assistant message for session: {session_id}")
    except Exception as e:
        logging.error(f"Error deleting last assistant message: {e}")
    finally:
        conn.close()
