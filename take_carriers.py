#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import sys
import os
import json
from datetime import datetime, timedelta
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
    
    carrier_id = form.getvalue('carrier_id')
    last_name = form.getvalue('last_name')
    first_name = form.getvalue('first_name')
    middle_name = form.getvalue('middle_name', '')
    phone = form.getvalue('phone')
    
    if not all([carrier_id, last_name, first_name, phone]):
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': False, 'message': 'Все обязательные поля должны быть заполнены'}))
        return

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check carrier availability
        cur.execute("SELECT status FROM carriers WHERE id = %s", (carrier_id,))
        carrier = cur.fetchone()
        
        if not carrier:
            print("Content-Type: application/json; charset=utf-8")
            print()
            print(json.dumps({'success': False, 'message': 'Носитель не найден'}))
            return
            
        if carrier[0] != 'Доступен':
            print("Content-Type: application/json; charset=utf-8")
            print()
            print(json.dumps({'success': False, 'message': 'Носитель недоступен для выдачи'}))
            return
        
        # Create or get reader
        fio = "{} {} {}".format(last_name, first_name, middle_name).strip()
        cur.execute(
            "INSERT INTO readers (fio, phone, registration_date, status) VALUES (%s, %s, %s, %s) ON CONFLICT (fio, phone) DO UPDATE SET fio = EXCLUDED.fio RETURNING id",
            (fio, phone, datetime.now().date(), 'Активен')
        )
        reader_id = cur.fetchone()[0]
        
        # Create issue record
        issue_date = datetime.now().date()
        planned_return = issue_date + timedelta(days=14)
        
        cur.execute(
            "INSERT INTO issues (carrier_id, reader_id, issue_date, planned_return_date, status) VALUES (%s, %s, %s, %s, %s)",
            (carrier_id, reader_id, issue_date, planned_return, 'Активна')
        )
        
        # Update carrier status
        cur.execute(
            "UPDATE carriers SET status = 'Выдан' WHERE id = %s",
            (carrier_id,)
        )
        
        conn.commit()
        
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({
            'success': True, 
            'message': 'Носитель успешно выдан. Вернуть до: {}'.format(planned_return.strftime("%d.%m.%Y"))
        }))
        
    except Exception as e:
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({'success': False, 'message': 'Ошибка базы данных: {}'.format(str(e))}))
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
