from flask import Blueprint, jsonify, request, g
from pydantic import ValidationError
from datetime import datetime
import uuid
from app.models.web_search_strategy import validate_search_input, generate_search_strategies
from app.models.web_search_executer import execute_flight_searches
from app.models.analytics import track_search, track_interest, track_no_interest, get_analytics
import geoip2.database
import geoip2.errors
import geoip2.webservice
import os

web_search_bp = Blueprint("web_app", __name__)

def get_user_location(ip_address):
    """Get user location from IP address using MaxMind Web Services"""
    try:
        # Replace with your real account details
        account_id = os.getenv("MAXMIND_ACCOUNT_ID")
        license_key = os.getenv("MAXMIND_LICENSE_KEY")

        with geoip2.webservice.Client(account_id, license_key) as client: # type: ignore
            response = client.city(ip_address)

            return {
                "country": response.country.name,
                "city": response.city.name,
                "latitude": float(response.location.latitude) if response.location.latitude else None,
                "longitude": float(response.location.longitude) if response.location.longitude else None
            }
    except geoip2.errors.AddressNotFoundError:
        return {"country": "Unknown", "city": "Unknown", "latitude": None, "longitude": None}
    except Exception:
        return {"country": "Unknown", "city": "Unknown", "latitude": None, "longitude": None}

def get_or_create_session_id():
    """Generate or retrieve session ID for tracking"""
    session_id = request.headers.get('X-Session-ID') or request.cookies.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id

@web_search_bp.route("/search", methods=["POST"])
def web_search_flights():
    try:
        # Get session and location info
        session_id = get_or_create_session_id()
        user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
        user_agent = request.headers.get('User-Agent', '')
        location = get_user_location(user_ip)
        
        # Validate and parse input
        search_request = validate_search_input(request.json)
        
        # Track the search
        search_data = {
            'session_id': session_id,
            'origin': search_request.origin,
            'destination': search_request.destination,
            'departure_date': search_request.departure_date,
            'return_date': search_request.return_date,
            'passengers': {
                'adults': search_request.adults,
                'children': search_request.children,
                'infants': search_request.infants
            },
            'travel_class': search_request.travel_class,
            'user_ip': user_ip,
            'user_agent': user_agent,
            'location': location,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        track_search(search_data)
        
        # Generate strategies for this specific request
        strategies = generate_search_strategies(search_request)
        
        # Execute searches
        results = execute_flight_searches(strategies, search_request)
        
        # Add session ID to response for frontend tracking
        response = jsonify({
            **results,
            'session_id': session_id
        })
        response.set_cookie('session_id', session_id, max_age=30*24*3600)  # 30 days
        
        return response
        
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400

@web_search_bp.route("/interested", methods=["POST"])
def track_user_interest():
    """Track users interested in booking directly on platform"""
    try:
        data = request.get_json(silent=True) or {}  # ensure dict, even if None
        session_id = get_or_create_session_id()
        user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
        location = get_user_location(user_ip)

        interest_data = {
            'session_id': session_id,
            'email': data.get('email', ''),  # safe defaults
            'name': data.get('name', ''),
            'flight_offer_id': data.get('flight_offer_id', ''),
            'user_ip': user_ip,
            'location': location,
            'timestamp': datetime.utcnow().isoformat()
        }

        track_interest(interest_data)

        return jsonify({
            'success': True,
            'message': 'Thank you for your interest! We will contact you soon.'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@web_search_bp.route("/not-interested", methods=["POST"])
def track_user_not_interested():
    """Track users who are not interested"""
    try:
        data = request.get_json(silent=True) or {}
        session_id = get_or_create_session_id()
        user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
        location = get_user_location(user_ip)

        no_interest_data = {
            'session_id': session_id,
            'reason': data.get('reason', ''),   # default empty string
            'feedback': data.get('feedback', ''),  # default empty string
            'user_ip': user_ip,
            'location': location,
            'timestamp': datetime.utcnow().isoformat()
        }

        track_no_interest(no_interest_data)

        return jsonify({
            'success': True,
            'message': 'Thank you for your feedback!'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@web_search_bp.route("/analytics", methods=["GET"])
def get_analytics_data():
    """Get analytics dashboard data"""
    try:
        # Add basic auth or admin check here
        analytics_data = get_analytics()
        return jsonify(analytics_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
