from datetime import datetime, timedelta
import json
import sqlite3
import os
from typing import Dict, List, Any
from app.storage.db_service import StorageService

storage_service = StorageService()

def init_analytics_db():
    """Initialize analytics database"""
    cursor = storage_service.conn.cursor() # type: ignore
    
    # Searches table - PostgreSQL syntax
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS searches (
            id SERIAL PRIMARY KEY,
            session_id TEXT,
            origin TEXT,
            destination TEXT,
            departure_date TEXT,
            return_date TEXT,
            passengers TEXT,
            travel_class TEXT,
            user_ip TEXT,
            user_agent TEXT,
            location TEXT,
            timestamp TEXT
        )
    ''')
    
    # Interested users table - only fields you're actually using
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interested_users (
            id SERIAL PRIMARY KEY,
            session_id TEXT,
            email TEXT,
            name TEXT,
            flight_offer_id TEXT,
            user_ip TEXT,
            location TEXT,
            timestamp TEXT
        )
    ''')
    
    # Not interested users table - only fields you're actually using
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS not_interested_users (
            id SERIAL PRIMARY KEY,
            session_id TEXT,
            reason TEXT,
            feedback TEXT,
            user_ip TEXT,
            location TEXT,
            timestamp TEXT
        )
    ''')
    
    storage_service.conn.commit() # type: ignore

def track_search(search_data: Dict[str, Any]):
    """Track flight search"""
    init_analytics_db()
    cursor = storage_service.conn.cursor() # type: ignore
    
    cursor.execute('''
        INSERT INTO searches (
            session_id, origin, destination, departure_date, return_date,
            passengers, travel_class, user_ip, user_agent, location, timestamp
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        search_data['session_id'],
        search_data['origin'],
        search_data['destination'],
        search_data['departure_date'],
        search_data.get('return_date'),
        json.dumps(search_data['passengers']),
        search_data['travel_class'],
        search_data['user_ip'],
        search_data['user_agent'],
        json.dumps(search_data['location']),
        search_data['timestamp']
    ))
    
    storage_service.conn.commit() # type: ignore

def track_interest(interest_data: Dict[str, Any]):
    """Track interested user"""
    init_analytics_db()
    cursor = storage_service.conn.cursor() # type: ignore
    
    cursor.execute('''
        INSERT INTO interested_users (
            session_id, email, name, flight_offer_id,
            user_ip, location, timestamp
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    ''', (
        interest_data['session_id'],
        interest_data.get('email', ''),
        interest_data.get('name', ''),
        interest_data.get('flight_offer_id', ''),
        interest_data['user_ip'],
        json.dumps(interest_data['location']),
        interest_data['timestamp']
    ))
    
    storage_service.conn.commit() # type: ignore

def track_no_interest(no_interest_data: Dict[str, Any]):
    """Track not interested user"""
    init_analytics_db()
    cursor = storage_service.conn.cursor() # type: ignore
    
    cursor.execute('''
        INSERT INTO not_interested_users (
            session_id, reason, feedback, user_ip, location, timestamp
        ) VALUES (%s, %s, %s, %s, %s, %s)
    ''', (
        no_interest_data['session_id'],
        no_interest_data.get('reason', ''),
        no_interest_data.get('feedback', ''),
        no_interest_data['user_ip'],
        json.dumps(no_interest_data['location']),
        no_interest_data['timestamp']
    ))
    
    storage_service.conn.commit() # type: ignore

def get_analytics() -> Dict[str, Any]:
    """Get analytics data"""
    init_analytics_db()
    cursor = storage_service.conn.cursor() # type: ignore
    
    # Total searches
    cursor.execute('SELECT COUNT(*) FROM searches')
    total_searches = cursor.fetchone()[0] # type: ignore
    
    # Unique users (by session_id)
    cursor.execute('SELECT COUNT(DISTINCT session_id) FROM searches')
    unique_users = cursor.fetchone()[0] # type: ignore
    
    # Searches in last 24 hours
    yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
    cursor.execute('SELECT COUNT(*) FROM searches WHERE timestamp > ?', (yesterday,))
    searches_24h = cursor.fetchone()[0] # type: ignore
    
    # Top routes
    cursor.execute('''
        SELECT origin, destination, COUNT(*) as count 
        FROM searches 
        GROUP BY origin, destination 
        ORDER BY count DESC 
        LIMIT 10
    ''')
    top_routes = [{'route': f"{row[0]} → {row[1]}", 'count': row[2]} for row in cursor.fetchall()]
    
    # Countries
    cursor.execute('SELECT location FROM searches WHERE location != "null"')
    locations = []
    for row in cursor.fetchall():
        try:
            location = json.loads(row[0])
            if location.get('country') and location['country'] != 'Unknown':
                locations.append(location['country'])
        except:
            continue
    
    from collections import Counter
    country_counts = Counter(locations).most_common(10)
    
    # Interested users
    cursor.execute('SELECT COUNT(*) FROM interested_users')
    interested_count = cursor.fetchone()[0] # type: ignore
    
    # Not interested users
    cursor.execute('SELECT COUNT(*) FROM not_interested_users')
    not_interested_count = cursor.fetchone()[0] # type: ignore
    
    # Conversion rate
    conversion_rate = (interested_count / unique_users * 100) if unique_users > 0 else 0
    
    storage_service.conn.close() # type: ignore
    
    return {
        'total_searches': total_searches,
        'unique_users': unique_users,
        'searches_last_24h': searches_24h,
        'interested_users': interested_count,
        'not_interested_users': not_interested_count,
        'conversion_rate': round(conversion_rate, 2),
        'top_routes': top_routes,
        'top_countries': [{'country': country, 'count': count} for country, count in country_counts],
    }
