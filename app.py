from flask import Flask, render_template, request, redirect, session, url_for
import psycopg2

app = Flask(__name__)
app.secret_key = 'secret'

def db_conn(user='film_user', pwd='user123'):
    return psycopg2.connect(dbname='filmoteka', user=user, password=pwd, host='localhost')

def get_carriers_with_status():
    conn = db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.id, c.type, c.condition, c.price,
               f.localized_name, f.year_out, d.full_name,
               f.id as film_id
        FROM carriers c
        JOIN films f ON c.film_id = f.id
        JOIN directors d ON f.director_id = d.id
    """)
    carriers_raw = cursor.fetchall()

    cursor.execute("""
        SELECT f.id, array_agg(g.name)
        FROM film_genres fg
        JOIN genres g ON fg.genre_id = g.id
        GROUP BY f.id
    """)
    genres_map = dict(cursor.fetchall())

    cursor.execute("SELECT carrier_id FROM issues WHERE status = 'Активна'")
    issued_carrier_ids = set(cid for (cid,) in cursor.fetchall())
    cursor.execute("SELECT film_id FROM reservations WHERE status = 'Подтверждено'")
    reserved_film_ids = set(fid for (fid,) in cursor.fetchall())

    carriers = []
    for c in carriers_raw:
        carrier_id = c[0]
        film_id = c[7]
        if carrier_id in issued_carrier_ids:
            status = 'Выдан'
        elif film_id in reserved_film_ids:
            status = 'Забронирован'
        elif c[2] == 'Списан':
            status = 'Списан'
        else:
            status = 'Доступен'
        genres = genres_map.get(film_id, [])
        carriers.append({
            'id': carrier_id,
            'type': c[1],
            'condition': c[2],
            'price': c[3],
            'localized_name': c[4],
            'year_out': c[5],
            'director': c[6],
            'genres': genres,
            'status': status
        })

    conn.close()
    return carriers

@app.route('/user', methods=['GET', 'POST'])
def user_page():
    carriers = get_carriers_with_status()
    genre_filter = request.args.get('genre', '')
    director_filter = request.args.get('director', '')
    title_filter = request.args.get('title', '')

    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM genres")
    genres = cursor.fetchall()
    cursor.execute("SELECT id, full_name FROM directors")
    directors = cursor.fetchall()
    conn.close()

    # Фильтрация на уровне Python
    def genre_ok(item):
        return genre_filter == '' or genre_filter in [g for g in item['genres']]

    filtered = []
    for carrier in carriers:
        if carrier['status'] not in ['Доступен', 'Забронирован']:
            continue
        if genre_filter and genre_filter not in carrier['genres']:
            continue
        if director_filter and director_filter != carrier['director']:
            continue
        if title_filter and title_filter.lower() not in carrier['localized_name'].lower():
            continue
        filtered.append(carrier)

    return render_template('user.html', carriers=filtered, genres=genres, directors=directors)

@app.route('/user/take/<int:carrier_id>', methods=['POST'])
def user_take_carrier(carrier_id):
    reader_id = session.get('reader_id', 1)
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.id FROM carriers c 
        JOIN films f ON c.film_id=f.id 
        WHERE c.id=%s
        """, (carrier_id,))
    film_id = cursor.fetchone()[0]
    # Проверяем выдан ли носитель
    cursor.execute("SELECT status FROM issues WHERE carrier_id=%s AND status='Активна'", (carrier_id,))
    if cursor.fetchone():
        conn.close()
        return "Уже выдан", 400
    # Проверяем забронировано ли
    cursor.execute("SELECT status FROM reservations WHERE film_id=%s AND status='Подтверждено'", (film_id,))
    if cursor.fetchone():
        conn.close()
        return "Забронировано", 400
    # Оформляем выдачу
    cursor.execute("""
        INSERT INTO issues (reader_id, carrier_id, given_at, planned_return, status)
        VALUES (%s, %s, CURRENT_DATE, CURRENT_DATE + INTERVAL '14 days', 'Активна')
        """, (reader_id, carrier_id))
    conn.commit()
    conn.close()
    return redirect(url_for('user_page'))

@app.route('/admin')
def admin_page():
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    # Фильмы
    cursor.execute("""
      SELECT f.id, f.localized_name, f.year_out, d.full_name, array_agg(g.name)
      FROM films f
        JOIN directors d ON f.director_id = d.id
        JOIN film_genres fg ON f.id = fg.film_id
        JOIN genres g ON fg.genre_id = g.id
      GROUP BY f.id, d.full_name
    """)
    films = cursor.fetchall()
    # Носители
    cursor.execute("""
      SELECT c.id, c.type, c.condition, c.price,
        f.localized_name, d.full_name 
      FROM carriers c
        JOIN films f ON c.film_id = f.id
        JOIN directors d ON f.director_id = d.id
    """)
    carriers = cursor.fetchall()
    # Выдачи
    cursor.execute("""
      SELECT i.id, i.reader_id, i.carrier_id, i.given_at, i.planned_return, i.real_return, i.status,
        r.fio, c.type, f.localized_name
      FROM issues i
        JOIN readers r ON i.reader_id = r.id
        JOIN carriers c ON i.carrier_id = c.id
        JOIN films f ON c.film_id = f.id
    """)
    issues = cursor.fetchall()
    # Жанры
    cursor.execute("SELECT * FROM genres")
    genres = cursor.fetchall()
    # Режиссёры
    cursor.execute("SELECT * FROM directors")
    directors = cursor.fetchall()
    # Читатели
    cursor.execute("SELECT * FROM readers")
    readers = cursor.fetchall()
    conn.close()
    return render_template('admin.html', films=films, carriers=carriers, issues=issues, genres=genres, directors=directors, readers=readers)

@app.route('/admin/edit_issue/<int:issue_id>', methods=['GET','POST'])
def admin_edit_issue(issue_id):
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    if request.method == 'GET':
        cursor.execute("SELECT * FROM issues WHERE id=%s", (issue_id,))
        issue = cursor.fetchone()
        conn.close()
        return render_template('edit_issue.html', issue=issue)
    else:
        planned_return = request.form['planned_return']
        cursor.execute(
            "UPDATE issues SET planned_return=%s WHERE id=%s",
            (planned_return, issue_id)
        )
        conn.commit()
        conn.close()
        return redirect('/admin')

# Примеры: CRUD для остальных сущностей можно дописать аналогично.

if __name__ == '__main__':
    app.run(debug=True)
