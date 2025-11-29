from flask import Flask, render_template, request, redirect, session, url_for, jsonify
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

@app.route('/api/user/take/<int:carrier_id>', methods=['POST'])
def api_user_take_carrier(carrier_id):
    reader_id = session.get('reader_id', 1)
    conn = db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT f.id FROM carriers c 
            JOIN films f ON c.film_id=f.id 
            WHERE c.id=%s
            """, (carrier_id,))
        film_id = cursor.fetchone()[0]
        # Проверяем выдан ли носитель
        cursor.execute("SELECT status FROM issues WHERE carrier_id=%s AND status='Активна'", (carrier_id,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Уже выдан'}), 400
        # Проверяем забронировано ли
        cursor.execute("SELECT status FROM reservations WHERE film_id=%s AND status='Подтверждено'", (film_id,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Забронировано'}), 400
        # Оформляем выдачу
        cursor.execute("""
            INSERT INTO issues (reader_id, carrier_id, given_at, planned_return, status)
            VALUES (%s, %s, CURRENT_DATE, CURRENT_DATE + INTERVAL '14 days', 'Активна')
            """, (reader_id, carrier_id))
        conn.commit()
        return jsonify({'success': True, 'message': 'Носитель успешно взят'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

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

# CRUD для фильмов
@app.route('/api/admin/films', methods=['GET'])
def api_get_films():
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.id, f.localized_name, f.year_out, d.full_name, array_agg(g.name)
        FROM films f
        JOIN directors d ON f.director_id = d.id
        JOIN film_genres fg ON f.id = fg.film_id
        JOIN genres g ON fg.genre_id = g.id
        GROUP BY f.id, d.full_name
    """)
    films = cursor.fetchall()
    conn.close()
    return jsonify([{
        'id': f[0], 'name': f[1], 'year': f[2], 
        'director': f[3], 'genres': f[4]
    } for f in films])

@app.route('/api/admin/films', methods=['POST'])
def api_create_film():
    data = request.json
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO films (localized_name, year_out, director_id) VALUES (%s, %s, %s) RETURNING id",
            (data['name'], data['year'], data['director_id'])
        )
        film_id = cursor.fetchone()[0]
        
        # Добавляем жанры
        for genre_id in data['genre_ids']:
            cursor.execute(
                "INSERT INTO film_genres (film_id, genre_id) VALUES (%s, %s)",
                (film_id, genre_id)
            )
        
        conn.commit()
        return jsonify({'success': True, 'id': film_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/films/<int:film_id>', methods=['PUT'])
def api_update_film(film_id):
    data = request.json
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE films SET localized_name=%s, year_out=%s, director_id=%s WHERE id=%s",
            (data['name'], data['year'], data['director_id'], film_id)
        )
        
        # Обновляем жанры
        cursor.execute("DELETE FROM film_genres WHERE film_id=%s", (film_id,))
        for genre_id in data['genre_ids']:
            cursor.execute(
                "INSERT INTO film_genres (film_id, genre_id) VALUES (%s, %s)",
                (film_id, genre_id)
            )
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/films/<int:film_id>', methods=['DELETE'])
def api_delete_film(film_id):
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM films WHERE id=%s", (film_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

# CRUD для носителей
@app.route('/api/admin/carriers', methods=['GET'])
def api_get_carriers():
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.type, c.condition, c.price, f.localized_name, d.full_name 
        FROM carriers c
        JOIN films f ON c.film_id = f.id
        JOIN directors d ON f.director_id = d.id
    """)
    carriers = cursor.fetchall()
    conn.close()
    return jsonify([{
        'id': c[0], 'type': c[1], 'condition': c[2], 
        'price': c[3], 'film_name': c[4], 'director': c[5]
    } for c in carriers])

@app.route('/api/admin/carriers', methods=['POST'])
def api_create_carrier():
    data = request.json
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO carriers (type, condition, price, film_id) VALUES (%s, %s, %s, %s) RETURNING id",
            (data['type'], data['condition'], data['price'], data['film_id'])
        )
        carrier_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({'success': True, 'id': carrier_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/carriers/<int:carrier_id>', methods=['PUT'])
def api_update_carrier(carrier_id):
    data = request.json
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE carriers SET type=%s, condition=%s, price=%s, film_id=%s WHERE id=%s",
            (data['type'], data['condition'], data['price'], data['film_id'], carrier_id)
        )
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/carriers/<int:carrier_id>', methods=['DELETE'])
def api_delete_carrier(carrier_id):
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM carriers WHERE id=%s", (carrier_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

# CRUD для выдач
@app.route('/api/admin/issues', methods=['GET'])
def api_get_issues():
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.id, i.reader_id, i.carrier_id, i.given_at, i.planned_return, i.real_return, i.status,
            r.fio, c.type, f.localized_name
        FROM issues i
        JOIN readers r ON i.reader_id = r.id
        JOIN carriers c ON i.carrier_id = c.id
        JOIN films f ON c.film_id = f.id
    """)
    issues = cursor.fetchall()
    conn.close()
    return jsonify([{
        'id': i[0], 'reader_id': i[1], 'carrier_id': i[2], 'given_at': str(i[3]),
        'planned_return': str(i[4]), 'real_return': str(i[5]) if i[5] else None,
        'status': i[6], 'reader_name': i[7], 'carrier_type': i[8], 'film_name': i[9]
    } for i in issues])

@app.route('/api/admin/issues', methods=['POST'])
def api_create_issue():
    data = request.json
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO issues (reader_id, carrier_id, given_at, planned_return, status)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """, (data['reader_id'], data['carrier_id'], data['given_at'], data['planned_return'], data['status']))
        issue_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({'success': True, 'id': issue_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/issues/<int:issue_id>', methods=['PUT'])
def api_update_issue(issue_id):
    data = request.json
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE issues SET reader_id=%s, carrier_id=%s, given_at=%s, 
            planned_return=%s, real_return=%s, status=%s WHERE id=%s
        """, (data['reader_id'], data['carrier_id'], data['given_at'], 
              data['planned_return'], data.get('real_return'), data['status'], issue_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/issues/<int:issue_id>', methods=['DELETE'])
def api_delete_issue(issue_id):
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM issues WHERE id=%s", (issue_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

# CRUD для пользователей
@app.route('/api/admin/readers', methods=['GET'])
def api_get_readers():
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM readers")
    readers = cursor.fetchall()
    conn.close()
    return jsonify([{
        'id': r[0], 'fio': r[1], 'phone': r[2], 
        'reg_date': str(r[3]), 'status': r[4]
    } for r in readers])

@app.route('/api/admin/readers', methods=['POST'])
def api_create_reader():
    data = request.json
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO readers (fio, phone, reg_date, status) 
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (data['fio'], data['phone'], data['reg_date'], data['status']))
        reader_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({'success': True, 'id': reader_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/readers/<int:reader_id>', methods=['PUT'])
def api_update_reader(reader_id):
    data = request.json
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE readers SET fio=%s, phone=%s, reg_date=%s, status=%s WHERE id=%s
        """, (data['fio'], data['phone'], data['reg_date'], data['status'], reader_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/readers/<int:reader_id>', methods=['DELETE'])
def api_delete_reader(reader_id):
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM readers WHERE id=%s", (reader_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

# CRUD для жанров
@app.route('/api/admin/genres', methods=['GET'])
def api_get_genres():
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM genres")
    genres = cursor.fetchall()
    conn.close()
    return jsonify([{'id': g[0], 'name': g[1]} for g in genres])

@app.route('/api/admin/genres', methods=['POST'])
def api_create_genre():
    data = request.json
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO genres (name) VALUES (%s) RETURNING id", (data['name'],))
        genre_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({'success': True, 'id': genre_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/genres/<int:genre_id>', methods=['PUT'])
def api_update_genre(genre_id):
    data = request.json
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE genres SET name=%s WHERE id=%s", (data['name'], genre_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/genres/<int:genre_id>', methods=['DELETE'])
def api_delete_genre(genre_id):
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM genres WHERE id=%s", (genre_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

# CRUD для режиссёров
@app.route('/api/admin/directors', methods=['GET'])
def api_get_directors():
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM directors")
    directors = cursor.fetchall()
    conn.close()
    return jsonify([{'id': d[0], 'name': d[1]} for d in directors])

@app.route('/api/admin/directors', methods=['POST'])
def api_create_director():
    data = request.json
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO directors (full_name) VALUES (%s) RETURNING id", (data['name'],))
        director_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({'success': True, 'id': director_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/directors/<int:director_id>', methods=['PUT'])
def api_update_director(director_id):
    data = request.json
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE directors SET full_name=%s WHERE id=%s", (data['name'], director_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/directors/<int:director_id>', methods=['DELETE'])
def api_delete_director(director_id):
    conn = db_conn(user='film_admin', pwd='admin123')
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM directors WHERE id=%s", (director_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
