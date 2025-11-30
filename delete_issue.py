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
    issue_id = form.getvalue('id')

    if not issue_id:
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': False, 'message': 'ID выдачи обязательно'}))
        return

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Получаем carrier_id перед удалением
        cur.execute("SELECT carrier_id FROM issues WHERE id = %s", (int(issue_id),))
        result = cur.fetchone()
        
        if not result:
            print("Content-Type: application/json; charset=utf-8")
            print()
            print(json.dumps({'success': False, 'message': 'Выдача не найдена'}))
            return
            
        carrier_id = result[0]
        
        # Удаляем выдачу
        cur.execute("DELETE FROM issues WHERE id = %s", (int(issue_id),))
        
        # Обновляем статус носителя на "Доступен"
        cur.execute("UPDATE carriers SET status = 'Доступен' WHERE id = %s", (carrier_id,))
        
        conn.commit()
        
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': True, 'message': 'Выдача успешно удалена. Носитель снова доступен.'}))
        
    except Exception as e:
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': False, 'message': 'Ошибка базы данных: {}'.format(str(e))}))
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
