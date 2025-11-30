#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json
sys.path.append(os.path.dirname(__file__))

from database import get_db_connection

def get_films():
    """Get all films"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT f.id, f.localized_name, f.year_out, d.full_name as director,
                   ARRAY_AGG(DISTINCT g.name) as genres
            FROM films f
            LEFT JOIN directors d ON f.director_id = d.id
            LEFT JOIN film_genres fg ON f.id = fg.film_id
            LEFT JOIN genres g ON fg.genre_id = g.id
            GROUP BY f.id, f.localized_name, f.year_out, d.full_name
            ORDER BY f.localized_name
        """)
        films = cur.fetchall()
        
        result = []
        for row in films:
            result.append({
                'id': row[0],
                'name': row[1],
                'year': row[2],
                'director': row[3],
                'genres': row[4] if row[4] and row[4][0] is not None else []
            })
        
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps(result))
    finally:
        conn.close()

if __name__ == "__main__":
    get_films()
