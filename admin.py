#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import os
import sys
sys.path.append(os.path.dirname(__file__))

from database import get_db_connection

cgitb.enable()

def get_all_admin_data():
    """Get all data for admin panel"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Films
        cur.execute("""
            SELECT f.id, f.localized_name, f.year_out, d.full_name as director,
                   ARRAY_AGG(DISTINCT g.name) as genres
            FROM films f
            LEFT JOIN directors d ON f.director_id = d.id
            LEFT JOIN film_genres fg ON f.id = fg.film_id
            LEFT JOIN genres g ON fg.genre_id = g.id
            GROUP BY f.id, f.localized_name, f.year_out, d.full_name
            ORDER BY f.localized_name
        """)
        films = cur.fetchall()
        
        # Carriers
        cur.execute("""
            SELECT c.id, c.type, c.condition, c.price, c.status,
                   f.localized_name as film_name, d.full_name as director
            FROM carriers c
            JOIN films f ON c.film_id = f.id
            JOIN directors d ON f.director_id = d.id
            WHERE c.status != 'Удален'
            ORDER BY f.localized_name
        """)
        carriers = cur.fetchall()
        
        # Issues
        cur.execute("""
            SELECT i.id, i.carrier_id, i.reader_id, i.issue_date, i.planned_return_date, 
                   i.actual_return_date, i.status, r.fio as reader_fio,
                   c.type as carrier_type, f.localized_name as film_name
            FROM issues i
            JOIN readers r ON i.reader_id = r.id
            JOIN carriers c ON i.carrier_id = c.id
            JOIN films f ON c.film_id = f.id
            ORDER BY i.issue_date DESC
        """)
        issues = cur.fetchall()
        
        # Readers
        cur.execute("SELECT id, fio, phone, registration_date, status FROM readers ORDER BY fio")
        readers = cur.fetchall()
        
        # Genres
        cur.execute("SELECT id, name FROM genres ORDER BY name")
        genres = cur.fetchall()
        
        # Directors
        cur.execute("SELECT id, full_name FROM directors ORDER BY full_name")
        directors = cur.fetchall()
        
        return films, carriers, issues, readers, genres, directors
    finally:
        conn.close()

def render_template(template_file, **context):
    """Функция рендеринга шаблона для админки"""
    template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', template_file)
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # Замена переменных в формате {{ variable }}
    for key, value in context.items():
        placeholder = '{{ ' + key + ' }}'
        
        if isinstance(value, list):
            # Для списков генерируем HTML
            if key == 'films':
                html_content = generate_films_table(value)
            elif key == 'carriers':
                html_content = generate_carriers_table(value)
            elif key == 'issues':
                html_content = generate_issues_table(value)
            elif key == 'readers':
                html_content = generate_readers_table(value)
            elif key == 'genres':
                html_content = generate_genres_table(value)
            elif key == 'directors':
                html_content = generate_directors_table(value)
            else:
                html_content = str(value)
        else:
            html_content = str(value) if value is not None else ''
        
        template = template.replace(placeholder, html_content)
    
    print("Content-Type: text/html; charset=utf-8")
    print()
    print(template)

def generate_films_table(films):
    """Генерирует HTML таблицу фильмов"""
    if not films:
        return '<div class="text-center py-4"><p>Нет фильмов</p></div>'
    
    rows = []
    for film in films:
        film_id, name, year, director, genres = film
        genres_str = ', '.join(genres) if genres and genres[0] is not None else '—'
        
        row = '''
        <tr data-film-id="{0}">
            <td><strong>{1}</strong></td>
            <td>{2}</td>
            <td>{3}</td>
            <td>{4}</td>
            <td>
                <button class="btn btn-danger btn-sm delete-film-btn" data-film-id="{0}">Удалить</button>
            </td>
        </tr>
        '''.format(film_id, name, year, director, genres_str)
        rows.append(row)
    
    return '''
    <table class="table table-striped">
        <thead class="table-dark">
            <tr>
                <th>Название</th>
                <th>Год</th>
                <th>Режиссёр</th>
                <th>Жанры</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            {0}
        </tbody>
    </table>
    '''.format('\n'.join(rows))

def generate_carriers_table(carriers):
    """Генерирует HTML таблицу носителей"""
    if not carriers:
        return '<div class="text-center py-4"><p>Нет носителей</p></div>'
    
    rows = []
    for carrier in carriers:
        carrier_id, carrier_type, condition, price, status, film_name, director = carrier
        
        # Condition badge
        if condition == 'Отличное':
            condition_badge = '<span class="badge bg-success">Отличное</span>'
        elif condition == 'Хорошее':
            condition_badge = '<span class="badge bg-primary">Хорошее</span>'
        elif condition == 'Удовлетворительное':
            condition_badge = '<span class="badge bg-warning">Удовл.</span>'
        else:
            condition_badge = '<span class="badge bg-secondary">{}</span>'.format(condition)
        
        # Price
        price_html = '{:.2f} ₽'.format(price) if price > 0 else '<span class="text-muted">Бесплатно</span>'
        
        # Status badge
        if status == 'Доступен':
            status_badge = '<span class="badge bg-success">Доступен</span>'
        elif status == 'Выдан':
            status_badge = '<span class="badge bg-warning">Выдан</span>'
        elif status == 'На реставрации':
            status_badge = '<span class="badge bg-info">На реставрации</span>'
        else:
            status_badge = '<span class="badge bg-secondary">{}</span>'.format(status)
        
        row = '''
        <tr data-carrier-id="{0}">
            <td><span class="badge bg-info">{1}</span></td>
            <td><strong>{2}</strong></td>
            <td>{3}</td>
            <td>{4}</td>
            <td>{5}</td>
            <td>{6}</td>
            <td>
                <button class="btn btn-danger btn-sm delete-carrier-btn" data-carrier-id="{0}">Удалить</button>
            </td>
        </tr>
        '''.format(carrier_id, carrier_type, film_name, condition_badge, price_html, status_badge, director)
        rows.append(row)
    
    return '''
    <table class="table table-striped">
        <thead class="table-dark">
            <tr>
                <th>Тип</th>
                <th>Фильм</th>
                <th>Состояние</th>
                <th>Цена</th>
                <th>Статус</th>
                <th>Режиссёр</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            {0}
        </tbody>
    </table>
    '''.format('\n'.join(rows))

def generate_issues_table(issues):
    """Генерирует HTML таблицу выдач"""
    if not issues:
        return '<div class="text-center py-4"><p>Нет выдач</p></div>'
    
    rows = []
    for issue in issues:
        issue_id, carrier_id, reader_id, issue_date, planned_return, actual_return, status, reader_fio, carrier_type, film_name = issue
        
        # Status badge
        if status == 'Активна':
            status_badge = '<span class="badge bg-warning">Активна</span>'
        elif status == 'Завершена':
            status_badge = '<span class="badge bg-success">Завершена</span>'
        else:
            status_badge = '<span class="badge bg-danger">{}</span>'.format(status)
        
        actual_return_html = actual_return if actual_return else "—"
        
        row = '''
        <tr data-issue-id="{0}">
            <td><strong>{1}</strong> ({2})</td>
            <td>{3}</td>
            <td>{4}</td>
            <td>{5}</td>
            <td>{6}</td>
            <td>{7}</td>
            <td>
                <button class="btn btn-danger btn-sm delete-issue-btn" data-issue-id="{0}">Удалить</button>
            </td>
        </tr>
        '''.format(issue_id, film_name, carrier_type, reader_fio, issue_date, planned_return, actual_return_html, status_badge)
        rows.append(row)
    
    return '''
    <table class="table table-striped">
        <thead class="table-dark">
            <tr>
                <th>Носитель</th>
                <th>Пользователь</th>
                <th>Дата выдачи</th>
                <th>План. возврат</th>
                <th>Факт. возврат</th>
                <th>Статус</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            {0}
        </tbody>
    </table>
    '''.format('\n'.join(rows))

def generate_readers_table(readers):
    """Генерирует HTML таблицу пользователей"""
    if not readers:
        return '<div class="text-center py-4"><p>Нет пользователей</p></div>'
    
    rows = []
    for reader in readers:
        reader_id, fio, phone, reg_date, status = reader
        
        # Status badge
        if status == 'Активен':
            status_badge = '<span class="badge bg-success">Активен</span>'
        elif status == 'Заблокирован':
            status_badge = '<span class="badge bg-danger">Заблокирован</span>'
        else:
            status_badge = '<span class="badge bg-secondary">{}</span>'.format(status)
        
        phone_html = phone if phone else "—"
        
        row = '''
        <tr data-reader-id="{0}">
            <td>{0}</td>
            <td><strong>{1}</strong></td>
            <td>{2}</td>
            <td>{3}</td>
            <td>{4}</td>
            <td>
                <button class="btn btn-danger btn-sm delete-reader-btn" data-reader-id="{0}">Удалить</button>
            </td>
        </tr>
        '''.format(reader_id, fio, phone_html, reg_date, status_badge)
        rows.append(row)
    
    return '''
    <table class="table table-striped">
        <thead class="table-dark">
            <tr>
                <th>ID</th>
                <th>ФИО</th>
                <th>Телефон</th>
                <th>Дата регистрации</th>
                <th>Статус</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            {0}
        </tbody>
    </table>
    '''.format('\n'.join(rows))

def generate_genres_table(genres):
    """Генерирует HTML таблицу жанров"""
    if not genres:
        return '<div class="text-center py-4"><p>Нет жанров</p></div>'
    
    rows = []
    for genre in genres:
        genre_id, name = genre
        
        row = '''
        <tr data-genre-id="{0}">
            <td>{0}</td>
            <td><strong>{1}</strong></td>
            <td>
                <button class="btn btn-danger btn-sm delete-genre-btn" data-genre-id="{0}">Удалить</button>
            </td>
        </tr>
        '''.format(genre_id, name)
        rows.append(row)
    
    return '''
    <table class="table table-striped">
        <thead class="table-dark">
            <tr>
                <th>ID</th>
                <th>Название</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            {0}
        </tbody>
    </table>
    '''.format('\n'.join(rows))

def generate_directors_table(directors):
    """Генерирует HTML таблицу режиссеров"""
    if not directors:
        return '<div class="text-center py-4"><p>Нет режиссеров</p></div>'
    
    rows = []
    for director in directors:
        director_id, name = director
        
        row = '''
        <tr data-director-id="{0}">
            <td>{0}</td>
            <td><strong>{1}</strong></td>
            <td>
                <button class="btn btn-danger btn-sm delete-director-btn" data-director-id="{0}">Удалить</button>
            </td>
        </tr>
        '''.format(director_id, name)
        rows.append(row)
    
    return '''
    <table class="table table-striped">
        <thead class="table-dark">
            <tr>
                <th>ID</th>
                <th>ФИО</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            {0}
        </tbody>
    </table>
    '''.format('\n'.join(rows))

def main():
    # Получение всех данных для админки
    films, carriers, issues, readers, genres, directors = get_all_admin_data()
    
    # Рендеринг HTML-шаблона
    render_template('admin.html', 
                   films=films,
                   carriers=carriers,
                   issues=issues,
                   readers=readers,
                   genres=genres,
                   directors=directors)

if __name__ == '__main__':
    main()
