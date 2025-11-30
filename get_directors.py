#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json
sys.path.append(os.path.dirname(__file__))

from database import get_db_connection

def get_directors():
    """Get all directors"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, full_name FROM directors ORDER BY full_name")
        directors = cur.fetchall()
        result = [{'id': row[0], 'name': row[1]} for row in directors]
        
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps(result))
    finally:
        conn.close()

if __name__ == "__main__":
    get_directors()
