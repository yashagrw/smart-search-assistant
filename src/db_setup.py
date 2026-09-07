import sqlite3
import random
import string
import os
from datetime import datetime, timedelta

# Define absolute database path relative to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'local_data.db')

def random_string(prefix, length=8):
    return prefix + ''.join(random.choices(string.digits, k=length))

def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))

def random_address():
    streets = ["Main St", "Oak Ave", "Pine Rd", "Maple Dr", "Cedar Ln", "Elm St", "Birch Blvd", "Spruce Ct"]
    cities = ["Springfield", "Riverside", "Franklin", "Greenville", "Bristol", "Clinton", "Fairview", "Salem"]
    states = ["CA", "TX", "NY", "FL", "IL", "PA", "OH", "GA"]
    return f"{random.randint(100,9999)} {random.choice(streets)}, {random.choice(cities)}, {random.choice(states)}"

def setup_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create client table
    c.execute('''CREATE TABLE IF NOT EXISTS client (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )''')

    # Create projects table
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        groupNumber TEXT NOT NULL,
        status TEXT CHECK(status IN ('open', 'cancelled')) NOT NULL,
        client_id INTEGER,
        createdAt TEXT NOT NULL,
        updatedAt TEXT NOT NULL,
        FOREIGN KEY(client_id) REFERENCES client(id)
    )''')

    # Create orders table with address column
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        createdAt TEXT NOT NULL,
        updatedAt TEXT NOT NULL,
        fileNum TEXT NOT NULL,
        displayStatus TEXT CHECK(displayStatus IN ('open', 'cancelled', 'order_processing', 'closed')) NOT NULL,
        status TEXT CHECK(status IN ('in_escrow', 'cancelled', 'closed')) NOT NULL,
        address TEXT NOT NULL
    )''')

    # Create FTS5 virtual tables for full-text search
    c.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS projects_fts USING fts5(
        name, groupNumber, content='projects', content_rowid='id'
    )''')
    c.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS orders_fts USING fts5(
        fileNum, address, content='orders', content_rowid='id'
    )''')

    # Insert dummy clients
    client_names = [f'Client {i}' for i in range(1, 21)]
    c.executemany('INSERT INTO client (name) VALUES (?)', [(name,) for name in client_names])

    # Insert deterministic benchmark records for consistent testing
    now = datetime.now()
    now_iso = now.isoformat()
    
    deterministic_projects = [
        ('Project P185602', 'P64852978', 'open', 1, now_iso, now_iso),
        ('Project P352635', 'P19283746', 'cancelled', 2, now_iso, now_iso),
        ('Project Alpha', 'P99887766', 'open', 3, now_iso, now_iso)
    ]
    c.executemany('''INSERT INTO projects (name, groupNumber, status, client_id, createdAt, updatedAt) 
                     VALUES (?, ?, ?, ?, ?, ?)''', deterministic_projects)

    deterministic_orders = [
        (now_iso, now_iso, 'END1234567', 'order_processing', 'in_escrow', '123 Main St, Springfield, CA'),
        (now_iso, now_iso, 'END7654321', 'closed', 'closed', '456 Oak Ave, Riverside, TX')
    ]
    c.executemany('''INSERT INTO orders (createdAt, updatedAt, fileNum, displayStatus, status, address) 
                     VALUES (?, ?, ?, ?, ?, ?)''', deterministic_orders)

    # Insert remaining random projects
    statuses = ['open', 'cancelled']
    for i in range(97):
        name = f'Project {random_string("P", 6)}'
        groupNumber = random_string('P', 8)
        status = random.choice(statuses)
        client_id = random.randint(1, 20)
        createdAt = random_date(now - timedelta(days=365), now).isoformat()
        updatedAt = random_date(datetime.fromisoformat(createdAt), now).isoformat()
        c.execute('''INSERT INTO projects (name, groupNumber, status, client_id, createdAt, updatedAt) VALUES (?, ?, ?, ?, ?, ?)''',
                  (name, groupNumber, status, client_id, createdAt, updatedAt))

    # Insert remaining random orders
    display_statuses = ['open', 'cancelled', 'order_processing', 'closed']
    order_statuses = ['in_escrow', 'cancelled', 'closed']
    for i in range(98):
        createdAt = random_date(now - timedelta(days=365), now).isoformat()
        updatedAt = random_date(datetime.fromisoformat(createdAt), now).isoformat()
        fileNum = random_string('END', 7)
        displayStatus = random.choice(display_statuses)
        status = random.choice(order_statuses)
        address = random_address()
        c.execute('''INSERT INTO orders (createdAt, updatedAt, fileNum, displayStatus, status, address) VALUES (?, ?, ?, ?, ?, ?)''',
                  (createdAt, updatedAt, fileNum, displayStatus, status, address))

    # Populate FTS tables
    c.execute('INSERT INTO projects_fts(rowid, name, groupNumber) SELECT id, name, groupNumber FROM projects')
    c.execute('INSERT INTO orders_fts(rowid, fileNum, address) SELECT id, fileNum, address FROM orders')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    setup_db()
    print('Database and FTS tables created with dummy data.')