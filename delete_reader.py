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
    reader_id = form.getvalue('id')

    if not reader_id:
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': False, 'message': 'ID пользователя обязательно'}))
        return

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Проверяем, есть ли активные выдачи у пользователя
        cur.execute("SELECT COUNT(*) FROM issues WHERE reader_id = %s AND status = 'Активна'", (int(reader_id),))
        active_issues = cur.fetchone()[0]
        
        if active_issues > 0:
            print("Content-Type: application/json; charset=utf-8")
            print()
            print(json.dumps({'success': False, 'message': 'Нельзя удалить пользователя с активными выдачами'}))
            return
        
        cur.execute("DELETE FROM readers WHERE id = %s", (int(reader_id),))
        conn.commit()
        
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': True, 'message': 'Пользователь успешно удален'}))
        
    except Exception as e:
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': False, 'message': 'Ошибка базы данных: {}'.format(str(e))}))
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
