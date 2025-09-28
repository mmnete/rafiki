from flask import Blueprint, jsonify, request
from pydantic import ValidationError
from app.models.web_search_strategy import validate_search_input, generate_search_strategies
from app.models.web_search_executer import execute_flight_searches

# {
#   "origin": "SFO",
#   "destination": "BKK", 
#   "departure_date": "2024-03-15",
#   "return_date": "2024-03-22",        // Could be null for one-way
#   "passengers": {
#     "adults": 2,
#     "children": 1,                    // Ages 2-11  
#     "infants": 0                      // Under 2
#   },
#   "travel_class": "economy",          // economy, premium_economy, business, first
#   "special_needs": ["vegetarian_meal", "wheelchair_assistance"]
# }

web_search_bp = Blueprint("web_app", __name__)

@web_search_bp.route("/search", methods=["POST"])
def web_search_flights():
    try:
        # Validate and parse input
        search_request = validate_search_input(request.json)
        
        # Generate strategies for this specific request
        strategies = generate_search_strategies(search_request)
        
        # Execute searches
        results = execute_flight_searches(strategies, search_request)
        
        return jsonify(results)
        
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400


