from flask import Blueprint, jsonify, request, g
from pydantic import ValidationError
from datetime import datetime
import uuid
import threading
from app.models.web_search_strategy import validate_search_input, generate_search_strategies
from app.models.web_search_executer import execute_flight_searches
from app.models.analytics import track_search, track_interest, track_no_interest, get_analytics
from app.services.redis_storage_manager import implemented_redis_storage_manager as storage
# import geoip2.database
# import geoip2.errors
# import geoip2.webservice
# import os
import logging
import time

logger = logging.getLogger(__name__)

web_search_bp = Blueprint("web_app", __name__)

# def get_user_location(ip_address):
#     """Get user location from IP address using MaxMind Web Services"""
#     try:
#         account_id = os.getenv("MAXMIND_ACCOUNT_ID")
#         license_key = os.getenv("MAXMIND_LICENSE_KEY")
        
#         if account_id is None or license_key is None:
#             logger.warning("MaxMind credentials not configured (MAXMIND_ACCOUNT_ID or MAXMIND_LICENSE_KEY missing)")
#             return {}

#         with geoip2.webservice.Client(int(account_id), license_key) as client:
#             response = client.city(ip_address)

#             return {
#                 "country": response.country.name,
#                 "city": response.city.name,
#                 "latitude": float(response.location.latitude) if response.location.latitude else None,
#                 "longitude": float(response.location.longitude) if response.location.longitude else None
#             }
#     except geoip2.errors.AddressNotFoundError:
#         logger.warning(f"IP address not found in MaxMind database: {ip_address}")
#         return {"country": "Unknown", "city": "Unknown", "latitude": None, "longitude": None}
#     except geoip2.errors.AuthenticationError as e:
#         logger.error(f"MaxMind authentication failed: {str(e)}")
#         return {"country": "Unknown", "city": "Unknown", "latitude": None, "longitude": None}
#     except geoip2.errors.PermissionRequiredError as e:
#         logger.error(f"MaxMind permission error: {str(e)}")
#         return {"country": "Unknown", "city": "Unknown", "latitude": None, "longitude": None}
#     except ValueError as e:
#         logger.error(f"Invalid MaxMind account ID format (expected integer): {str(e)}")
#         return {"country": "Unknown", "city": "Unknown", "latitude": None, "longitude": None}
#     except Exception as e:
#         logger.error(f"Unexpected error getting location for IP {ip_address}: {type(e).__name__}: {str(e)}", exc_info=True)
#         return {"country": "Unknown", "city": "Unknown", "latitude": None, "longitude": None}

def get_or_create_session_id():
    """Generate or retrieve session ID for tracking"""
    session_id = request.headers.get('X-Session-ID') or request.cookies.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id

def background_search_task(task_id, search_request, search_data):
    """Execute flight search in background thread"""
    try:
        logger.info(f"Starting background search for task {task_id}")
        
        # Update status to processing
        storage.set_data(f"search_status:{task_id}", {
            "status": "processing",
            "started_at": datetime.utcnow().isoformat(),
            "progress": "Generating search strategies..."
        }, ttl=3600)  # 1 hour TTL
        
        # Generate strategies
        strategies = generate_search_strategies(search_request)
        
        storage.set_data(f"search_status:{task_id}", {
            "status": "processing",
            "started_at": datetime.utcnow().isoformat(),
            "progress": f"Searching {len(strategies)} flight options..."
        }, ttl=3600)
        
        # Execute searches
        results = execute_flight_searches(strategies, search_request)
        
        # Store completed results
        storage.set_data(f"search_results:{task_id}", results, ttl=3600)
        storage.set_data(f"search_status:{task_id}", {
            "status": "completed",
            "started_at": search_data.get('timestamp'),
            "completed_at": datetime.utcnow().isoformat(),
            "progress": "Search completed successfully"
        }, ttl=3600)
        
        logger.info(f"Search task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Search task {task_id} failed: {str(e)}", exc_info=True)
        
        # Store error status
        storage.set_data(f"search_status:{task_id}", {
            "status": "failed",
            "error": str(e),
            "started_at": search_data.get('timestamp'),
            "failed_at": datetime.utcnow().isoformat()
        }, ttl=3600)

@web_search_bp.route("/search", methods=["POST"])
def web_search_flights():
    """Initiate async flight search and return task ID for polling"""
    try:
        # Get session and location info
        session_id = get_or_create_session_id()
        user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
        user_agent = request.headers.get('User-Agent', '')
        location = ""
        
        # Validate and parse input
        search_request = validate_search_input(request.json)
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Track the search
        search_data = {
            'task_id': task_id,
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
        
        # Store initial status
        storage.set_data(f"search_status:{task_id}", {
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }, ttl=3600)
        
        # Start background search in a separate thread
        thread = threading.Thread(
            target=background_search_task,
            args=(task_id, search_request, search_data),
            daemon=True
        )
        thread.start()
        
        logger.info(f"Created search task {task_id} for {search_request.origin} -> {search_request.destination}")
        
        # Return task ID for polling
        response = jsonify({
            'task_id': task_id,
            'status': 'pending',
            'message': 'Search initiated. Poll /search/status/<task_id> for results.',
            'poll_url': f'/search/status/{task_id}',
            'session_id': session_id
        })
        response.set_cookie('session_id', session_id, max_age=30*24*3600)
        
        return response, 202  # 202 Accepted
        
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error initiating search: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to initiate search"}), 500

@web_search_bp.route("/search/status/<task_id>", methods=["GET"])
def get_search_status(task_id):
    """Poll endpoint to check search status and retrieve results"""
    try:
        # Get current status
        status_data = storage.get_data(f"search_status:{task_id}")
        
        max_retries = 5
        
        while (not status_data) and max_retries > 0:
            status_data = storage.get_data(f"search_status:{task_id}")
            time.sleep(0.05) # sleep for 50ms before retrying
            max_retries -= 1
        
        if not status_data:
            return jsonify({
                "error": "Task not found or expired",
                "task_id": task_id
            }), 404
        
        status = status_data.get("status")
        
        # If completed, include results
        if status == "completed":
            results = storage.get_data(f"search_results:{task_id}")
            
            if results:
                return jsonify({
                    "task_id": task_id,
                    "status": "completed",
                    "started_at": status_data.get("started_at"),
                    "completed_at": status_data.get("completed_at"),
                    "results": results
                })
            else:
                return jsonify({
                    "task_id": task_id,
                    "status": "completed",
                    "error": "Results not found"
                }), 500
        
        # If still processing or pending, return status
        elif status in ["pending", "processing"]:
            return jsonify({
                "task_id": task_id,
                "status": status,
                "progress": status_data.get("progress", "Processing..."),
                "started_at": status_data.get("started_at"),
                "message": "Search in progress. Poll again in a few seconds."
            }), 202  # 202 Accepted (still processing)
        
        # If failed, return error
        elif status == "failed":
            return jsonify({
                "task_id": task_id,
                "status": "failed",
                "error": status_data.get("error", "Unknown error"),
                "started_at": status_data.get("started_at"),
                "failed_at": status_data.get("failed_at")
            }), 500
        
        else:
            return jsonify({
                "task_id": task_id,
                "status": "unknown",
                "error": "Invalid status"
            }), 500
            
    except Exception as e:
        logger.error(f"Error checking status for task {task_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to check status"}), 500

@web_search_bp.route("/interested", methods=["POST"])
def track_user_interest():
    """Track users interested in booking directly on platform"""
    try:
        data = request.get_json(silent=True) or {}
        session_id = get_or_create_session_id()
        user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
        location = ""

        interest_data = {
            'session_id': session_id,
            'email': data.get('email', ''),
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
        location = ""

        no_interest_data = {
            'session_id': session_id,
            'reason': data.get('reason', ''),
            'feedback': data.get('feedback', ''),
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
        analytics_data = get_analytics()
        return jsonify(analytics_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_search_bp.route("/price-alert", methods=["POST"])
def create_price_alert():
    """Create a price alert for a route"""
    try:
        data = request.get_json(silent=True) or {}
        session_id = get_or_create_session_id()
        user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
        location = ""

        # Validate required fields
        if not data.get('email'):
            return jsonify({'error': 'Email is required'}), 400
        if not data.get('origin') or not data.get('destination'):
            return jsonify({'error': 'Origin and destination are required'}), 400
        if not data.get('departure_date'):
            return jsonify({'error': 'Departure date is required'}), 400

        from app.models.analytics import create_price_alert

        alert_data = {
            'email': data['email'],
            'origin': data['origin'],
            'destination': data['destination'],
            'departure_date': data['departure_date'],
            'return_date': data.get('return_date'),
            'passengers': data.get('passengers', {
                'adults': 1,
                'children': 0,
                'infants': 0
            }),
            'travel_class': data.get('travel_class', 'economy'),
            'session_id': session_id,
            'user_ip': user_ip,
            'location': location
        }

        create_price_alert(alert_data)

        logger.info(f"Price alert created for {data['email']}: {data['origin']} -> {data['destination']}")

        return jsonify({
            'success': True,
            'message': 'Price alert created! We\'ll notify you when prices drop.'
        })

    except Exception as e:
        logger.error(f"Error creating price alert: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to create price alert'}), 500


@web_search_bp.route("/price-alert/<alert_id>", methods=["DELETE"])
def delete_price_alert(alert_id):
    """Delete/deactivate a price alert"""
    try:
        user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
        
        from app.models.analytics import deactivate_price_alert
        
        deactivate_price_alert(alert_id, user_ip)
        
        return jsonify({
            'success': True,
            'message': 'Price alert cancelled'
        })
    except Exception as e:
        logger.error(f"Error deleting price alert: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to cancel price alert'}), 500

@web_search_bp.route("/booking-click", methods=["POST"])
def track_booking_click():
    """Track when a user clicks a booking button"""
    try:
        data = request.get_json(silent=True) or {}
        session_id = get_or_create_session_id()
        user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
        location = ""

        # Validate required fields
        if not data.get('origin') or not data.get('destination'):
            return jsonify({'error': 'Origin and destination are required'}), 400

        from app.models.analytics import track_booking_click as track_click

        click_data = {
            'session_id': session_id,
            'flight_offer_id': data.get('flight_offer_id'),
            'origin': data['origin'],
            'destination': data['destination'],
            'departure_date': data.get('departure_date'),  # Now optional
            'return_date': data.get('return_date'),
            'price': data.get('price'),
            'booking_site': data.get('booking_site', 'skyscanner'),
            'user_ip': user_ip,
            'location': location
        }

        track_click(click_data)

        logger.info(f"Booking click tracked: {user_ip} -> {data['origin']} to {data['destination']}")

        return jsonify({
            'success': True,
            'message': 'Booking click tracked'
        })

    except Exception as e:
        logger.error(f"Error tracking booking click: {str(e)}", exc_info=True)
        # Don't fail the request if tracking fails - just log it
        return jsonify({'success': False, 'error': str(e)}), 200
