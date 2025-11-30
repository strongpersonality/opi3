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
    director_id = form.getvalue('id')

    if not director_id:
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': False, 'message': 'ID режиссера обязательно'}))
        return

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Проверяем, есть ли фильмы у этого режиссера
        cur.execute("SELECT COUNT(*) FROM films WHERE director_id = %s", (int(director_id),))
        film_count = cur.fetchone()[0]
        
        if film_count > 0:
            print("Content-Type: application/json; charset=utf-8")
            print()
            print(json.dumps({'success': False, 'message': 'Нельзя удалить режиссера, у которого есть фильмы'}))
            return
        
        cur.execute("DELETE FROM directors WHERE id = %s", (int(director_id),))
        conn.commit()
        
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': True, 'message': 'Режиссер успешно удален'}))
        
    except Exception as e:
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': False, 'message': 'Ошибка базы данных: {}'.format(str(e))}))
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
