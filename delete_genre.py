#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import sys
import os
import json
sys.path.append(os.path.dirname(__file__))

from database import get_db_connection

cgitb.enable()

def main():
    if os.environ.get('REQUEST_METHOD') != 'DELETE':
        print("Status: 405 Method Not Allowed")
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': False, 'message': 'Only DELETE method allowed'}))
        return

    form = cgi.FieldStorage()
    genre_id = form.getvalue('id')

    if not genre_id:
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': False, 'message': 'ID жанра обязательно'}))
        return

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Проверяем, используется ли жанр в фильмах
        cur.execute("SELECT COUNT(*) FROM film_genres WHERE genre_id = %s", (int(genre_id),))
        film_count = cur.fetchone()[0]
        
        if film_count > 0:
            print("Content-Type: application/json; charset=utf-8")
            print()
            print(json.dumps({'success': False, 'message': 'Нельзя удалить жанр, который используется в фильмах'}))
            return
        
        cur.execute("DELETE FROM genres WHERE id = %s", (int(genre_id),))
        conn.commit()
        
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': True, 'message': 'Жанр успешно удален'}))
        
    except Exception as e:
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': False, 'message': 'Ошибка базы данных: {}'.format(str(e))}))
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
