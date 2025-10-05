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
    
    # Price alerts table - NEW
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_alerts (
            id SERIAL PRIMARY KEY,
            email TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            departure_date TEXT NOT NULL,
            return_date TEXT,
            passengers TEXT,
            travel_class TEXT,
            session_id TEXT,
            user_ip TEXT,
            location TEXT,
            created_at TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE
        )
    ''')
    
    # Booking clicks table - NEW
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS booking_clicks (
            id SERIAL PRIMARY KEY,
            session_id TEXT,
            flight_offer_id TEXT,
            origin TEXT,
            destination TEXT,
            departure_date TEXT,
            return_date TEXT,
            price DECIMAL(10,2),
            booking_site TEXT,
            user_ip TEXT NOT NULL,
            location TEXT,
            timestamp TEXT NOT NULL
        )
    ''')
    
    # Interested users table
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
    
    # Not interested users table
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

def create_price_alert(alert_data: Dict[str, Any]):
    """Create a price alert for a user"""
    init_analytics_db()
    cursor = storage_service.conn.cursor() # type: ignore
    
    cursor.execute('''
        INSERT INTO price_alerts (
            email, origin, destination, departure_date, return_date,
            passengers, travel_class, session_id, user_ip, location, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        alert_data['email'],
        alert_data['origin'],
        alert_data['destination'],
        alert_data['departure_date'],
        alert_data.get('return_date'),
        json.dumps(alert_data.get('passengers', {})),
        alert_data.get('travel_class', 'economy'),
        alert_data.get('session_id'),
        alert_data['user_ip'],
        json.dumps(alert_data.get('location', {})),
        datetime.utcnow().isoformat()
    ))
    
    storage_service.conn.commit() # type: ignore

def deactivate_price_alert(alert_id: int, user_ip: str):
    """Deactivate a price alert"""
    init_analytics_db()
    cursor = storage_service.conn.cursor() # type: ignore
    
    cursor.execute('''
        UPDATE price_alerts 
        SET is_active = FALSE 
        WHERE id = %s AND user_ip = %s
    ''', (alert_id, user_ip))
    
    storage_service.conn.commit() # type: ignore

def track_booking_click(click_data: Dict[str, Any]):
    """Track when a user clicks a booking button"""
    init_analytics_db()
    cursor = storage_service.conn.cursor() # type: ignore
    
    cursor.execute('''
        INSERT INTO booking_clicks (
            session_id, flight_offer_id, origin, destination,
            departure_date, return_date, price, booking_site,
            user_ip, location, timestamp
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        click_data.get('session_id'),
        click_data.get('flight_offer_id'),
        click_data['origin'],
        click_data['destination'],
        click_data['departure_date'],
        click_data.get('return_date'),
        click_data.get('price'),
        click_data.get('booking_site', 'skyscanner'),
        click_data['user_ip'],
        json.dumps(click_data.get('location', {})),
        datetime.utcnow().isoformat()
    ))
    
    storage_service.conn.commit() # type: ignore

def get_price_alerts(active_only: bool = True) -> List[Dict[str, Any]]:
    """Get all price alerts, optionally filtered by active status"""
    init_analytics_db()
    cursor = storage_service.conn.cursor() # type: ignore
    
    if active_only:
        cursor.execute('SELECT * FROM price_alerts WHERE is_active = TRUE ORDER BY created_at DESC')
    else:
        cursor.execute('SELECT * FROM price_alerts ORDER BY created_at DESC')
    
    columns = [desc[0] for desc in cursor.description] # type: ignore
    alerts = []
    for row in cursor.fetchall():
        alert = dict(zip(columns, row))
        alerts.append(alert)
    
    return alerts

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
    cursor.execute('SELECT COUNT(*) FROM searches WHERE timestamp > %s', (yesterday,))
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
    cursor.execute('SELECT location FROM searches WHERE location != \'null\'')
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
    
    # Price alerts count
    cursor.execute('SELECT COUNT(*) FROM price_alerts WHERE is_active = TRUE')
    active_alerts_count = cursor.fetchone()[0] # type: ignore
    
    # Booking clicks count
    cursor.execute('SELECT COUNT(*) FROM booking_clicks')
    booking_clicks_count = cursor.fetchone()[0] # type: ignore
    
    # Conversion rate
    conversion_rate = (interested_count / unique_users * 100) if unique_users > 0 else 0
    
    # Booking click rate
    booking_rate = (booking_clicks_count / unique_users * 100) if unique_users > 0 else 0
    
    return {
        'total_searches': total_searches,
        'unique_users': unique_users,
        'searches_last_24h': searches_24h,
        'interested_users': interested_count,
        'not_interested_users': not_interested_count,
        'active_price_alerts': active_alerts_count,
        'booking_clicks': booking_clicks_count,
        'conversion_rate': round(conversion_rate, 2),
        'booking_click_rate': round(booking_rate, 2),
        'top_routes': top_routes,
        'top_countries': [{'country': country, 'count': count} for country, count in country_counts],
    }
