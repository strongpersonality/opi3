#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import psycopg2

db_config = {
    'dbname': 'filmoteka',
    'user': 'postgres',
    'password': '123456',
    'host': 'localhost'
}

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(**db_config)
