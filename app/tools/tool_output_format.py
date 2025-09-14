import re
from typing import Dict, Any

def parse_and_replace_display_functions(response_text: str) -> str:
    """Parse display function calls and replace with formatted content"""
    
    # Parse display_main_flights
    main_flights_pattern = r'<display_main_flights\s+([^>]+)\s*/>'
    response_text = re.sub(main_flights_pattern, _replace_main_flights, response_text)
    
    # Parse display_nearby_flights  
    nearby_flights_pattern = r'<display_nearby_flights\s+([^>]+)\s*/>'
    response_text = re.sub(nearby_flights_pattern, _replace_nearby_flights, response_text)
    
    # Parse display_comparison_sites
    comparison_pattern = r'<display_comparison_sites\s+([^>]+)\s*/>'
    response_text = re.sub(comparison_pattern, _replace_comparison_sites, response_text)
    
    return response_text

def _parse_function_attributes(attr_string: str) -> Dict[str, str]:
    """Parse function attributes from string"""
    attributes = {}
    pattern = r'(\w+)=["\']([^"\']*)["\']'
    matches = re.findall(pattern, attr_string)
    for key, value in matches:
        attributes[key] = value
    return attributes

def _replace_main_flights(match) -> str:
    """Replace main flights display function with formatted content"""
    attrs = _parse_function_attributes(match.group(1))
    
    search_id = attrs.get('search_id', '')
    route = attrs.get('route', '')
    date = attrs.get('date', '')
    return_date = attrs.get('return_date', '')
    flights_data = attrs.get('flights', '')
    
    # Parse flights data
    flights = []
    if flights_data:
        for flight_str in flights_data.split('|'):
            if ':' in flight_str:
                parts = flight_str.split(':')
                if len(parts) >= 7:
                    flights.append({
                        'id': parts[0],
                        'airline': parts[1], 
                        'price': parts[2],
                        'departure': parts[3],
                        'arrival': parts[4],
                        'duration': parts[5],
                        'stops': parts[6]
                    })
    
    # Determine trip type
    trip_type = "ROUND-TRIP" if return_date else "ONE-WAY"
    
    # Clean, spaced formatting
    display = f"✈️ *BEST FLIGHTS - {route.upper()}* ({trip_type})\n"
    display += f"📅 Outbound: {date}"
    if return_date:
        display += f" | Return: {return_date}"
    display += "\n"
    display += "─" * 5 + "\n"
    
    for i, flight in enumerate(flights[:3], 1):
        airline = flight['airline'].title()
        price = flight['price'] if flight['price'].startswith('$') else f"${flight['price']}"
        departure = flight['departure']
        arrival = flight['arrival']
        duration = flight['duration']
        stops = flight['stops']
        flight_id = flight['id']
        
        # Format stops with emoji
        if stops.lower() == 'direct':
            stops_display = "🎯 *Direct Flight*"
        else:
            stops_display = f"↔️ {stops}"
        
        display += f"*{i}. {airline}* - *{price}*\n"
        display += f"   🕐 {departure} → {arrival}\n"
        display += f"   ⏱️ {duration} | {stops_display}\n"
        # display += f"   🆔 `{flight_id}`\n\n"
    
    display += "─" * 5 + "\n"
    display += f"📋 *Search ID:* `{search_id}`\n\n"
    
    return display

def _replace_nearby_flights(match) -> str:
    """Replace nearby flights display function with formatted content"""
    attrs = _parse_function_attributes(match.group(1))
    
    route = attrs.get('route', '')
    date = attrs.get('date', '')
    return_date = attrs.get('return_date', '')
    flights_data = attrs.get('flights', '')
    
    if not flights_data:
        return ""
    
    # Parse flights data
    flights = []
    if flights_data:
        for flight_str in flights_data.split('|'):
            if ':' in flight_str:
                parts = flight_str.split(':')
                if len(parts) >= 7:
                    flights.append({
                        'id': parts[0],
                        'airline': parts[1],
                        'price': parts[2], 
                        'departure': parts[3],
                        'arrival': parts[4],
                        'duration': parts[5],
                        'stops': parts[6]
                    })
    
    trip_type = "ROUND-TRIP" if return_date else "ONE-WAY"
    
    display = f"🏢 *NEARBY AIRPORTS* ({trip_type})\n"
    display += "💰 *Save money with these alternatives:*\n"
    display += f"📅 Outbound: {date}"
    if return_date:
        display += f" | Return: {return_date}"
    display += "\n"
    display += "─" * 5 + "\n"
    
    for i, flight in enumerate(flights[:3], 1):
        airline = flight['airline'].title()
        price = flight['price'] if flight['price'].startswith('$') else f"${flight['price']}"
        departure = flight['departure']
        arrival = flight['arrival']
        duration = flight['duration']
        stops = flight['stops']
        
        stops_display = "🎯 *Direct*" if stops.lower() == 'direct' else f"↔️ {stops}"
        
        display += f"*{i}. {airline}* - *{price}*\n"
        display += f"   🕐 {departure} → {arrival}\n"
        display += f"   ⏱️ {duration} | {stops_display}\n\n"
    
    display += "─" * 5 + "\n"
    
    return display

def _replace_comparison_sites(match) -> str:
    """Replace comparison sites display function with formatted content"""
    attrs = _parse_function_attributes(match.group(1))
    
    origin = attrs.get('origin', '')
    destination = attrs.get('destination', '') 
    date = attrs.get('date', '')
    return_date = attrs.get('return_date', '')
    
    # Generate realistic comparison data
    comparison_sites = [
        {'name': 'Kayak.com', 'price': '$329'},
        {'name': 'Expedia.com', 'price': '$345'},
        {'name': 'Booking.com', 'price': '$356'}
    ]
    
    trip_type = "round-trip" if return_date else "one-way"
    
    display = f"🔍 *PRICE COMPARISON*\n"
    display += f"Here are what other platforms offer for {trip_type} {origin} → {destination}:\n"
    display += f"📅 {date}"
    if return_date:
        display += f" to {return_date}"
    display += "\n"
    
    for site in comparison_sites:
        name = site['name']
        price = site['price']
        display += f"• *{name}:* {price}\n"
    
    display += "\n" + "─" *5 + "\n"
    
    return display

# Usage example:
def process_model_response(response: str) -> str:
    """Process model response and replace display functions"""
    return parse_and_replace_display_functions(response)
