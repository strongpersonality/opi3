#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import get_db_connection

def get_directors():
    """Get all directors for filters"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, full_name FROM directors ORDER BY full_name")
        directors = cur.fetchall()
        return directors
    finally:
        conn.close()

def get_directors_json():
    """API endpoint for directors"""
    directors = get_directors()
    result = [{'id': row[0], 'name': row[1]} for row in directors]
    
    print("Content-Type: application/json; charset=utf-8")
    print()
    print(json.dumps(result))

if __name__ == "__main__":
    get_directors_json()
