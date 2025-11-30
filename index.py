#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import os
import sys
import traceback
import locale

# Устанавливаем локаль для корректной работы с UTF-8
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    except:
        locale.setlocale(locale.LC_ALL, '')

# Включаем отладку
cgitb.enable()

# Добавляем путь к текущей директории
sys.path.append(os.path.dirname(__file__))

# Принудительно устанавливаем кодировку для stdout
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

try:
    from database import get_db_connection
    from jinja2 import Environment, FileSystemLoader
except ImportError as e:
    print("Content-Type: text/plain; charset=utf-8")
    print("Status: 500 Internal Server Error")
    print()
    print("Import Error: {}".format(e))
    sys.exit(1)

def get_directors():
    """Get all directors"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, full_name FROM directors ORDER BY full_name")
        directors = cur.fetchall()
        return directors
    except Exception as e:
        print("Content-Type: text/plain; charset=utf-8")
        print("Status: 500 Internal Server Error")
        print()
        print("Database Error in get_directors: {}".format(e))
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def get_genres():
    """Get all genres"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM genres ORDER BY name")
        genres = cur.fetchall()
        return genres
    except Exception as e:
        print("Content-Type: text/plain; charset=utf-8")
        print("Status: 500 Internal Server Error")
        print()
        print("Database Error in get_genres: {}".format(e))
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def search_carriers(title_filter='', director_filter='', genre_filter=''):
    """Get filtered carriers"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT DISTINCT 
                c.id,
                f.localized_name,
                f.year_out,
                d.full_name as director,
                c.type,
                c.condition,
                c.price,
                c.status,
                ARRAY_AGG(DISTINCT g.name) FILTER (WHERE g.name IS NOT NULL) as genres
            FROM carriers c
            JOIN films f ON c.film_id = f.id
            JOIN directors d ON f.director_id = d.id
            LEFT JOIN film_genres fg ON f.id = fg.film_id
            LEFT JOIN genres g ON fg.genre_id = g.id
            WHERE c.status = 'Доступен'
        """
        
        params = []
        
        if title_filter:
            query += " AND f.localized_name ILIKE %s"
            params.append('%{}%'.format(title_filter))
        
        if director_filter:
            query += " AND d.full_name = %s"
            params.append(director_filter)
        
        if genre_filter:
            query += " AND g.name = %s"
            params.append(genre_filter)
        
        query += " GROUP BY c.id, f.localized_name, f.year_out, d.full_name, c.type, c.condition, c.price, c.status"
        query += " ORDER BY f.localized_name"
        
        cur.execute(query, params)
        carriers_data = cur.fetchall()
        
        carriers = []
        for row in carriers_data:
            carriers.append({
                'id': row[0],
                'localized_name': row[1],
                'year_out': row[2],
                'director': row[3],
                'type': row[4],
                'condition': row[5],
                'price': float(row[6]) if row[6] else 0.0,
                'status': row[7],
                'genres': row[8] if row[8] else []
            })
        
        return carriers
    except Exception as e:
        print("Content-Type: text/plain; charset=utf-8")
        print("Status: 500 Internal Server Error")
        print()
        print("Database Error in search_carriers: {}".format(e))
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def render_template_jinja(template_file, **context):
    """Функция рендеринга с Jinja2"""
    try:
        templates_path = os.path.join(os.path.dirname(__file__), '..', 'templates')
        
        # Настраиваем Jinja2 с правильной кодировкой
        env = Environment(
            loader=FileSystemLoader(templates_path, encoding='utf-8'),
            autoescape=True
        )
        
        template = env.get_template(template_file)
        html_output = template.render(**context)
        
        print("Content-Type: text/html; charset=utf-8")
        print()
        print(html_output)
        
    except Exception as e:
        print("Content-Type: text/plain; charset=utf-8")
        print("Status: 500 Internal Server Error")
        print()
        print("Jinja2 Template Error: {}".format(str(e)))
        traceback.print_exc()

def main():
    try:
        # Устанавливаем кодировку для всей программы
        import locale
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        
        # Получение параметров фильтра из запроса
        form = cgi.FieldStorage()
        title_filter = form.getvalue('title', '')
        director_filter = form.getvalue('director', '')
        genre_filter = form.getvalue('genre', '')
        
        # Получение данных для фильтров
        directors = get_directors()
        genres = get_genres()
        
        # Получение отфильтрованных носителей
        carriers = search_carriers(title_filter, director_filter, genre_filter)
        
        # Подготавливаем данные для шаблона
        template_context = {
            'directors': directors,
            'genres': genres,
            'carriers': carriers,
            'selected_director': director_filter,
            'selected_genre': genre_filter,
            'title': title_filter
        }
        
        # Рендеринг HTML-шаблона с Jinja2
        render_template_jinja('user.html', **template_context)
                       
    except Exception as e:
        print("Content-Type: text/plain; charset=utf-8")
        print("Status: 500 Internal Server Error")
        print()
        print("Main Error: {}".format(str(e)))
        traceback.print_exc()

if __name__ == '__main__':
    main()
