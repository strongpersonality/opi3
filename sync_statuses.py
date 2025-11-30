#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import sys
import os
import json
from datetime import datetime
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

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Update carriers that are issued but have completed issues
        cur.execute("""
            UPDATE carriers 
            SET status = 'Доступен' 
            WHERE id IN (
                SELECT carrier_id 
                FROM issues 
                WHERE status = 'Завершена' 
                AND carrier_id IN (
                    SELECT id FROM carriers WHERE status = 'Выдан'
                )
            )
        """)
        
        updated_count = cur.rowcount
        conn.commit()
        
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({
            'success': True, 
            'message': 'Статусы синхронизированы. Обновлено носителей: {}'.format(updated_count)
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
