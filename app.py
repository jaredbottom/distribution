from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('permissions.db')
    c = conn.cursor()

    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, name TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS categories
                 (id INTEGER PRIMARY KEY, name TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS job_types
                 (id INTEGER PRIMARY KEY, name TEXT, category_id INTEGER)''')

    c.execute('''CREATE TABLE IF NOT EXISTS user_permissions
                 (user_id INTEGER, category_id INTEGER, job_type_id INTEGER, 
                  isActive INTEGER, PRIMARY KEY (user_id, job_type_id))''')

    # Generate sample data if empty
    if not c.execute("SELECT * FROM users").fetchall():
        users = [(1, "John Doe"), (2, "Jane Smith")]
        c.executemany("INSERT INTO users VALUES (?, ?)", users)

        categories = [(1, "Processing"), (2, "Analysis")]
        c.executemany("INSERT INTO categories VALUES (?, ?)", categories)

        job_types = [(1, "Import", 1), (2, "Export", 1), 
                     (3, "Basic", 2), (4, "Advanced", 2)]
        c.executemany("INSERT INTO job_types VALUES (?, ?, ?)", job_types)

        # Default permissions
        permissions = [
            (1, 1, 1, 1), (1, 1, 2, 0), (1, 2, 3, 1), (1, 2, 4, 0),
            (2, 1, 1, 0), (2, 1, 2, 1), (2, 2, 3, 0), (2, 2, 4, 1)
        ]
        c.executemany("INSERT INTO user_permissions VALUES (?, ?, ?, ?)", permissions)

    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('permissions.db')
    c = conn.cursor()
    users = c.execute("SELECT * FROM users").fetchall()
    conn.close()
    return render_template('index.html', users=users)

@app.route('/overview')
def overview():
    conn = sqlite3.connect('permissions.db')
    c = conn.cursor()

    matrix = c.execute("""
        SELECT u.id, u.name, c.id, c.name, jt.id, jt.name, COALESCE(up.isActive, 0) as isActive
        FROM users u
        CROSS JOIN job_types jt
        JOIN categories c ON c.id = jt.category_id
        LEFT JOIN user_permissions up ON up.user_id = u.id AND up.job_type_id = jt.id
        ORDER BY u.id, c.id, jt.id
    """).fetchall()

    users = {}
    categories = {}

    for user_id, user_name, cat_id, cat_name, jt_id, jt_name, is_active in matrix:
        if user_id not in users:
            users[user_id] = {'name': user_name, 'permissions': {}}
        if cat_id not in categories:
            categories[cat_id] = {'name': cat_name, 'job_types': set()}
        categories[cat_id]['job_types'].add((jt_id, jt_name))
        users[user_id]['permissions'][(cat_id, jt_id)] = is_active

    conn.close()
    return render_template('overview.html', users=users, categories=categories)

@app.route('/permissions/<int:user_id>')
def show_permissions(user_id):
    conn = sqlite3.connect('permissions.db')
    c = conn.cursor()

    user = c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    permissions = c.execute("""
        SELECT c.id, c.name, jt.id, jt.name, COALESCE(up.isActive, 0) as isActive
        FROM categories c
        JOIN job_types jt ON jt.category_id = c.id
        LEFT JOIN user_permissions up ON up.job_type_id = jt.id 
            AND up.user_id = ?
        ORDER BY c.id, jt.id
    """, (user_id,)).fetchall()

    # Group by category
    categories = {}
    for cat_id, cat_name, jt_id, jt_name, is_active in permissions:
        if cat_id not in categories:
            categories[cat_id] = {'name': cat_name, 'job_types': []}
        categories[cat_id]['job_types'].append({
            'id': jt_id,
            'name': jt_name,
            'isActive': is_active
        })

    conn.close()
    return render_template('permissions.html', 
                         user=user, 
                         categories=categories)

@app.route('/update_permissions/<int:user_id>', methods=['POST'])
def update_permissions(user_id):
    conn = sqlite3.connect('permissions.db')
    c = conn.cursor()

    job_types = c.execute("SELECT id, category_id FROM job_types").fetchall()

    for job_type_id, category_id in job_types:
        is_active = request.form.get(f'permission_{job_type_id}') == '1'
        c.execute("""
            INSERT OR REPLACE INTO user_permissions 
            (user_id, category_id, job_type_id, isActive)
            VALUES (?, ?, ?, ?)
        """, (user_id, category_id, job_type_id, int(is_active)))

    conn.commit()
    conn.close()
    return redirect(url_for('show_permissions', user_id=user_id))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
