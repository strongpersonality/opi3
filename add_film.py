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
    if os.environ.get('REQUEST_METHOD') != 'POST':
        print("Status: 405 Method Not Allowed")
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': False, 'message': 'Only POST method allowed'}))
        return

    form = cgi.FieldStorage()
    
    name = form.getvalue('name')
    year = form.getvalue('year')
    director_id = form.getvalue('director_id')

    if not all([name, year, director_id]):
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': False, 'message': 'Все поля должны быть заполнены'}))
        return

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "INSERT INTO films (localized_name, year_out, director_id) VALUES (%s, %s, %s)",
            (name, int(year), int(director_id))
        )
        conn.commit()
        
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': True, 'message': 'Фильм успешно добавлен'}))
        
    except Exception as e:
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': False, 'message': 'Ошибка базы данных: {}'.format(str(e))}))
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
