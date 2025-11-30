#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json
sys.path.append(os.path.dirname(__file__))

from database import get_db_connection

def get_genres():
    """Get all genres"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, name FROM genres ORDER BY name")
        genres = cur.fetchall()
        result = [{'id': row[0], 'name': row[1]} for row in genres]
        
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps(result))
    finally:
        conn.close()

if __name__ == "__main__":
    get_genres()
