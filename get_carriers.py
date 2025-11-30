#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cgi
import sys
import os
import json
sys.path.append(os.path.dirname(__file__))

from database import get_db_connection

def get_carriers():
    """Get carriers with optional filters"""
    form = cgi.FieldStorage()
    title = form.getvalue('title', '').strip()
    director_filter = form.getvalue('director', '')
    genre_filter = form.getvalue('genre', '')
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = """
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
        """
        
        params = []
        
        if title:
            query += " AND f.localized_name ILIKE %s"
            params.append('%{}%'.format(title))
        
        if director_filter:
            query += " AND d.full_name = %s"
            params.append(director_filter)
        
        if genre_filter:
            query += " AND g.name = %s"
            params.append(genre_filter)
        
        query += " GROUP BY c.id, f.localized_name, f.year_out, d.full_name, c.type, c.condition, c.price, c.status"
        query += " ORDER BY f.localized_name"
        
        cur.execute(query, params)
        carriers = cur.fetchall()
        
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
    finally:
        conn.close()

if __name__ == "__main__":
    get_carriers()
