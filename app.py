from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import psycopg2
from datetime import datetime, timedelta
import traceback

app = Flask(__name__)
app.secret_key = 'filmoteka_secret_key_2024'

def db_conn(user='film_user', pwd='user123'):
    try:
        conn = psycopg2.connect(
            dbname='filmoteka', 
            user=user, 
            password=pwd, 
            host='localhost',
            connect_timeout=10
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

def get_carriers_with_status():
    conn = None
    try:
        conn = db_conn()
        cursor = conn.cursor()

        # Получаем все носители с информацией о фильмах и режиссёрах
        cursor.execute("""
            SELECT c.id, c.type, c.condition, c.price, c.status,
                   f.localized_name, f.year_out, d.full_name,
                   f.id as film_id
            FROM carriers c
            JOIN films f ON c.film_id = f.id
            JOIN directors d ON f.director_id = d.id
            ORDER BY f.localized_name
        """)
        carriers_raw = cursor.fetchall()

        # Получаем жанры для фильмов
        cursor.execute("""
            SELECT fg.film_id, array_agg(g.name)
            FROM film_genres fg
            JOIN genres g ON fg.genre_id = g.id
            GROUP BY fg.film_id
        """)
        genres_map = dict(cursor.fetchall())

        # Получаем активные выдачи
        cursor.execute("SELECT carrier_id FROM issues WHERE status = 'Активна'")
        issued_carrier_ids = set(cid for (cid,) in cursor.fetchall())
        
        # Получаем подтверждённые бронирования
        cursor.execute("""
            SELECT film_id FROM reservations 
            WHERE status = 'Подтверждено' 
            AND period @> CURRENT_DATE
        """)
        reserved_film_ids = set(fid for (fid,) in cursor.fetchall())

        carriers = []
        for c in carriers_raw:
            carrier_id = c[0]
            film_id = c[8]
            
            # Определяем статус носителя
            if carrier_id in issued_carrier_ids:
                status = 'Выдан'
            elif film_id in reserved_film_ids:
                status = 'Забронирован'
            elif c[4] == 'Списан':
                status = 'Списан'
            elif c[4] == 'На реставрации':
                status = 'На реставрации'
            else:
                status = 'Доступен'
                
            genres = genres_map.get(film_id, [])
            carriers.append({
                'id': carrier_id,
                'type': c[1],
                'condition': c[2],
                'price': float(c[3]) if c[3] else 0.0,
                'status': status,
                'localized_name': c[5],
                'year_out': c[6],
                'director': c[7],
                'genres': genres,
                'film_id': film_id
            })

        return carriers

    except Exception as e:
        print(f"Error in get_carriers_with_status: {e}")
        print(traceback.format_exc())
        return []
    finally:
        if conn:
            conn.close()

@app.route('/')
def index():
    return redirect('/user')

@app.route('/user')
def user_page():
    try:
        carriers = get_carriers_with_status()
        
        # Получаем параметры фильтрации
        genre_filter = request.args.get('genre', '')
        director_filter = request.args.get('director', '')
        title_filter = request.args.get('title', '')

        conn = db_conn()
        cursor = conn.cursor()
        
        # Получаем списки для фильтров
        cursor.execute("SELECT id, name FROM genres ORDER BY name")
        genres = cursor.fetchall()
        
        cursor.execute("SELECT id, full_name FROM directors ORDER BY full_name")
        directors = cursor.fetchall()
        conn.close()

        # Фильтрация носителей
        filtered_carriers = []
        for carrier in carriers:
            # Показываем только доступные и забронированные носители
            if carrier['status'] not in ['Доступен', 'Забронирован']:
                continue
                
            # Фильтр по жанру
            if genre_filter and genre_filter not in carrier['genres']:
                continue
                
            # Фильтр по режиссёру
            if director_filter and director_filter != carrier['director']:
                continue
                
            # Фильтр по названию
            if title_filter and title_filter.lower() not in carrier['localized_name'].lower():
                continue
                
            filtered_carriers.append(carrier)

        return render_template('user.html', 
                             carriers=filtered_carriers, 
                             genres=genres, 
                             directors=directors)
    except Exception as e:
        print(f"Error in user_page: {e}")
        return f"Ошибка загрузки страницы: {e}", 500

@app.route('/api/user/take/<int:carrier_id>', methods=['POST'])
def api_user_take_carrier(carrier_id):
    # В реальном приложении здесь должна быть аутентификация
    reader_id = session.get('reader_id', 1)  # По умолчанию первый читатель
    
    conn = None
    try:
        conn = db_conn()
        cursor = conn.cursor()

        # Проверяем, доступен ли носитель
        cursor.execute("""
            SELECT status, film_id FROM carriers WHERE id = %s
        """, (carrier_id,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({'success': False, 'message': 'Носитель не найден'}), 404
            
        carrier_status, film_id = result
        
        if carrier_status != 'Доступен':
            return jsonify({'success': False, 'message': 'Носитель недоступен'}), 400
        
        # Проверяем, не выдан ли уже носитель
        cursor.execute("""
            SELECT id FROM issues 
            WHERE carrier_id = %s AND status = 'Активна'
        """, (carrier_id,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Носитель уже выдан'}), 400
        
        # Проверяем, нет ли активных бронирований для этого фильма
        cursor.execute("""
            SELECT id FROM reservations 
            WHERE film_id = %s AND status = 'Подтверждено' AND period @> CURRENT_DATE
        """, (film_id,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Фильм забронирован'}), 400
        
        # Создаём выдачу
        given_at = datetime.now().date()
        planned_return = given_at + timedelta(days=14)
        
        cursor.execute("""
            INSERT INTO issues (reader_id, carrier_id, given_at, planned_return, status)
            VALUES (%s, %s, %s, %s, 'Активна')
        """, (reader_id, carrier_id, given_at, planned_return))
        
        # Обновляем статус носителя
        cursor.execute("""
            UPDATE carriers SET status = 'Выдан' WHERE id = %s
        """, (carrier_id,))
        
        conn.commit()
        return jsonify({
            'success': True, 
            'message': f'Носитель успешно взят до {planned_return}'
        })
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error in api_user_take_carrier: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/admin')
def admin_page():
    try:
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        
        # Фильмы с жанрами
        cursor.execute("""
            SELECT f.id, f.localized_name, f.year_out, d.full_name, 
                   array_agg(g.name) as genres
            FROM films f
            LEFT JOIN directors d ON f.director_id = d.id
            LEFT JOIN film_genres fg ON f.id = fg.film_id
            LEFT JOIN genres g ON fg.genre_id = g.id
            GROUP BY f.id, d.full_name
            ORDER BY f.localized_name
        """)
        films = cursor.fetchall()
        
        # Носители
        cursor.execute("""
            SELECT c.id, c.type, c.condition, c.price, c.status,
                   f.localized_name, d.full_name, f.id as film_id
            FROM carriers c
            JOIN films f ON c.film_id = f.id
            JOIN directors d ON f.director_id = d.id
            ORDER BY f.localized_name
        """)
        carriers = cursor.fetchall()
        
        # Выдачи
        cursor.execute("""
            SELECT i.id, i.reader_id, i.carrier_id, i.given_at, 
                   i.planned_return, i.real_return, i.status,
                   r.fio, c.type, f.localized_name
            FROM issues i
            JOIN readers r ON i.reader_id = r.id
            JOIN carriers c ON i.carrier_id = c.id
            JOIN films f ON c.film_id = f.id
            ORDER BY i.given_at DESC
        """)
        issues = cursor.fetchall()
        
        # Жанры
        cursor.execute("SELECT id, name FROM genres ORDER BY name")
        genres = cursor.fetchall()
        
        # Режиссёры
        cursor.execute("SELECT id, full_name FROM directors ORDER BY full_name")
        directors = cursor.fetchall()
        
        # Читатели
        cursor.execute("SELECT id, fio, phone, registration_date, status FROM readers ORDER BY fio")
        readers = cursor.fetchall()
        
        conn.close()
        
        return render_template('admin.html', 
                             films=films, 
                             carriers=carriers, 
                             issues=issues, 
                             genres=genres, 
                             directors=directors, 
                             readers=readers)
    except Exception as e:
        print(f"Error in admin_page: {e}")
        print(traceback.format_exc())
        return f"Ошибка загрузки админ-панели: {e}", 500

# API endpoints для админ-панели
@app.route('/api/admin/directors', methods=['GET'])
def api_get_directors():
    try:
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        cursor.execute("SELECT id, full_name FROM directors ORDER BY full_name")
        directors = cursor.fetchall()
        conn.close()
        return jsonify([{'id': d[0], 'name': d[1]} for d in directors])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/films', methods=['GET'])
def api_get_films():
    try:
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.id, f.localized_name, f.year_out, d.full_name, 
                   array_agg(g.name) as genres
            FROM films f
            LEFT JOIN directors d ON f.director_id = d.id
            LEFT JOIN film_genres fg ON f.id = fg.film_id
            LEFT JOIN genres g ON fg.genre_id = g.id
            GROUP BY f.id, d.full_name
            ORDER BY f.localized_name
        """)
        films = cursor.fetchall()
        conn.close()
        return jsonify([{
            'id': f[0], 
            'name': f[1], 
            'year': f[2], 
            'director': f[3], 
            'genres': f[4] if f[4] else []
        } for f in films])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/carriers', methods=['GET'])
def api_get_carriers():
    try:
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.type, c.condition, c.price, c.status,
                   f.localized_name, d.full_name
            FROM carriers c
            JOIN films f ON c.film_id = f.id
            JOIN directors d ON f.director_id = d.id
            ORDER BY f.localized_name
        """)
        carriers = cursor.fetchall()
        conn.close()
        return jsonify([{
            'id': c[0], 'type': c[1], 'condition': c[2], 
            'price': float(c[3]) if c[3] else 0.0, 'status': c[4],
            'film_name': c[5], 'director': c[6]
        } for c in carriers])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/issues', methods=['GET'])
def api_get_issues():
    try:
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.id, i.reader_id, i.carrier_id, i.given_at, 
                   i.planned_return, i.real_return, i.status,
                   r.fio, c.type, f.localized_name
            FROM issues i
            JOIN readers r ON i.reader_id = r.id
            JOIN carriers c ON i.carrier_id = c.id
            JOIN films f ON c.film_id = f.id
            ORDER BY i.given_at DESC
        """)
        issues = cursor.fetchall()
        conn.close()
        return jsonify([{
            'id': i[0], 'reader_id': i[1], 'carrier_id': i[2], 
            'given_at': str(i[3]), 'planned_return': str(i[4]),
            'real_return': str(i[5]) if i[5] else None, 'status': i[6],
            'reader_name': i[7], 'carrier_type': i[8], 'film_name': i[9]
        } for i in issues])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/readers', methods=['GET'])
def api_get_readers():
    try:
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        cursor.execute("SELECT id, fio, phone, registration_date, status FROM readers ORDER BY fio")
        readers = cursor.fetchall()
        conn.close()
        return jsonify([{
            'id': r[0], 'fio': r[1], 'phone': r[2], 
            'reg_date': str(r[3]), 'status': r[4]
        } for r in readers])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/genres', methods=['GET'])
def api_get_genres():
    try:
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM genres ORDER BY name")
        genres = cursor.fetchall()
        conn.close()
        return jsonify([{'id': g[0], 'name': g[1]} for g in genres])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# CRUD операции для удаления
@app.route('/api/admin/films/<int:film_id>', methods=['DELETE'])
def api_delete_film(film_id):
    conn = None
    try:
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM films WHERE id = %s", (film_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/carriers/<int:carrier_id>', methods=['DELETE'])
def api_delete_carrier(carrier_id):
    conn = None
    try:
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM carriers WHERE id = %s", (carrier_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/issues/<int:issue_id>', methods=['DELETE'])
def api_delete_issue(issue_id):
    conn = None
    try:
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        
        # Получаем carrier_id перед удалением выдачи
        cursor.execute("SELECT carrier_id FROM issues WHERE id = %s", (issue_id,))
        result = cursor.fetchone()
        if result:
            carrier_id = result[0]
            # Обновляем статус носителя обратно на "Доступен"
            cursor.execute("UPDATE carriers SET status = 'Доступен' WHERE id = %s", (carrier_id,))
        
        # Удаляем выдачу
        cursor.execute("DELETE FROM issues WHERE id = %s", (issue_id,))
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/readers/<int:reader_id>', methods=['DELETE'])
def api_delete_reader(reader_id):
    conn = None
    try:
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM readers WHERE id = %s", (reader_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/genres/<int:genre_id>', methods=['DELETE'])
def api_delete_genre(genre_id):
    conn = None
    try:
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM genres WHERE id = %s", (genre_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/directors/<int:director_id>', methods=['DELETE'])
def api_delete_director(director_id):
    conn = None
    try:
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM directors WHERE id = %s", (director_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

# Новые API для создания записей
@app.route('/api/admin/carriers', methods=['POST'])
def api_create_carrier():
    conn = None
    try:
        data = request.json
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO carriers (film_id, type, condition, price, status, date_bought)
            VALUES (%s, %s, %s, %s, 'Доступен', CURRENT_DATE)
            RETURNING id
        """, (data['film_id'], data['type'], data['condition'], data['price']))
        
        carrier_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({'success': True, 'id': carrier_id})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/films', methods=['POST'])
def api_create_film():
    conn = None
    try:
        data = request.json
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO films (localized_name, year_out, director_id)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (data['name'], data['year'], data['director_id']))
        
        film_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({'success': True, 'id': film_id})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/readers', methods=['POST'])
def api_create_reader():
    conn = None
    try:
        data = request.json
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO readers (fio, phone, status)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (data['fio'], data['phone'], data['status']))
        
        reader_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({'success': True, 'id': reader_id})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/genres', methods=['POST'])
def api_create_genre():
    conn = None
    try:
        data = request.json
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO genres (name)
            VALUES (%s)
            RETURNING id
        """, (data['name'],))
        
        genre_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({'success': True, 'id': genre_id})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/directors', methods=['POST'])
def api_create_director():
    conn = None
    try:
        data = request.json
        conn = db_conn(user='film_admin', pwd='admin123')
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO directors (full_name)
            VALUES (%s)
            RETURNING id
        """, (data['name'],))
        
        director_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({'success': True, 'id': director_id})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
