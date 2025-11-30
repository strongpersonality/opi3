#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import get_db_connection

def get_carriers():
    """Get all carriers for user page"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT DISTINCT 
                c.id,
                f.localized_name,
                f.year_out,
                d.full_name as director,
                c.type,
                c.condition,
                c.price,
                c.status,
                ARRAY_AGG(DISTINCT g.name) FILTER (WHERE g.name IS NOT NULL) as genres
            FROM carriers c
            JOIN films f ON c.film_id = f.id
            JOIN directors d ON f.director_id = d.id
            LEFT JOIN film_genres fg ON f.id = fg.film_id
            LEFT JOIN genres g ON fg.genre_id = g.id
            WHERE c.status != 'Удален'
            GROUP BY c.id, f.localized_name, f.year_out, d.full_name, c.type, c.condition, c.price, c.status
            ORDER BY f.localized_name
        """)
        carriers = cur.fetchall()
        return carriers
    finally:
        conn.close()

def get_carriers_json():
    """API endpoint for carriers"""
    carriers = get_carriers()
    result = []
    for row in carriers:
        result.append({
            'id': row[0],
            'localized_name': row[1],
            'year_out': row[2],
            'director': row[3],
            'type': row[4],
            'condition': row[5],
            'price': float(row[6]) if row[6] else 0.0,
            'status': row[7],
            'genres': row[8] if row[8] else []
        })
    
    print("Content-Type: application/json; charset=utf-8")
    print()
    print(json.dumps(result))

if __name__ == "__main__":
    get_carriers_json()
