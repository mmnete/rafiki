import re
from typing import Dict, Any


def parse_and_replace_display_functions(response_text: str) -> str:
    """Parse all display_ui function calls and replace with WhatsApp-friendly formatting"""
    
    # Process each type of display function
    response_text = _process_flight_displays(response_text)
    response_text = _process_comparison_sites(response_text)
    response_text = _process_booking_displays(response_text)
    response_text = _process_payment_displays(response_text)
    
    return response_text


def _process_flight_displays(text: str) -> str:
    """Process flight display functions"""
    # Pattern to match both display_main_flight and display_nearby_flight
    flight_pattern = r'<display_ui>(display_(?:main|nearby)_flight)\(([^)]+)\)</display_ui>'
    
    def replace_flight(match):
        function_name = match.group(1)
        params_str = match.group(2)
        params = _parse_parameters(params_str)
        
        if 'nearby' in function_name:
            return _format_nearby_flight(params)
        else:
            return _format_main_flight(params)
    
    return re.sub(flight_pattern, replace_flight, text)


def _process_comparison_sites(text: str) -> str:
    """Process comparison sites display"""
    comparison_pattern = r'<display_ui>display_comparison_sites\(([^)]+)\)</display_ui>'
    
    def replace_comparison(match):
        params_str = match.group(1)
        params = _parse_parameters(params_str)
        return _format_comparison_sites(params)
    
    return re.sub(comparison_pattern, replace_comparison, text)


def _process_booking_displays(text: str) -> str:
    """Process booking summary displays"""
    booking_pattern = r'<display_ui>display_booking_summary\(([^)]+)\)</display_ui>'
    
    def replace_booking(match):
        params_str = match.group(1)
        params = _parse_parameters(params_str)
        return _format_booking_summary(params)
    
    return re.sub(booking_pattern, replace_booking, text)


def _process_payment_displays(text: str) -> str:
    """Process payment link displays"""
    payment_pattern = r'<display_ui>display_payment_link\(([^)]+)\)</display_ui>'
    
    def replace_payment(match):
        params_str = match.group(1)
        params = _parse_parameters(params_str)
        return _format_payment_link(params)
    
    return re.sub(payment_pattern, replace_payment, text)


def _parse_parameters(params_str: str) -> Dict[str, str]:
    """Parse function parameters with robust handling of quotes"""
    params = {}
    
    # Handle both single and double quotes, with escaped quotes
    param_pattern = r'(\w+)=(["\'])([^"\']*?)\2'
    matches = re.findall(param_pattern, params_str)
    
    for key, quote_type, value in matches:
        params[key] = value.strip()
    
    return params


def _format_main_flight(params: Dict[str, str]) -> str:
    """Format main flight for WhatsApp display"""
    airline = params.get('airline', 'Unknown')
    price = params.get('price', '0')
    origin = params.get('origin_airport', '')
    destination = params.get('destination_airport', '')
    dep_date = params.get('departure_date', '')
    dep_time = params.get('departure_time', '')
    arr_date = params.get('arrival_date', '')
    arr_time = params.get('arrival_time', '')
    duration = params.get('duration', '')
    stops = params.get('stops', 'Unknown')
    connection_airport = params.get('connection_airport', '')
    connection_time = params.get('connection_time', '')
    
    # Format price
    price_formatted = f"${price}" if not price.startswith('$') else price
    
    # Build compact WhatsApp format
    display = f"✈️ *{airline}* - *{price_formatted}*\n"
    display += f"📍 {origin} → {destination}\n"
    
    # Handle timing
    if dep_date == arr_date:
        display += f"🕐 {dep_date}: {dep_time} → {arr_time}\n"
    else:
        display += f"🛫 {dep_date} {dep_time}\n"
        display += f"🛬 {arr_date} {arr_time}\n"
    
    # Handle connections
    if stops.lower() == 'direct':
        display += f"⏱️ {duration} • Direct flight"
    else:
        if connection_airport and connection_time:
            display += f"⏱️ {duration} • Via {connection_airport} ({connection_time})"
        else:
            display += f"⏱️ {duration} • {stops}"
    
    return display + "\n"


def _format_nearby_flight(params: Dict[str, str]) -> str:
    """Format nearby airport flight for WhatsApp display"""
    airline = params.get('airline', 'Unknown')
    price = params.get('price', '0')
    origin = params.get('origin_airport', '')
    destination = params.get('destination_airport', '')
    dep_date = params.get('departure_date', '')
    dep_time = params.get('departure_time', '')
    arr_date = params.get('arrival_date', '')
    arr_time = params.get('arrival_time', '')
    duration = params.get('duration', '')
    stops = params.get('stops', 'Unknown')
    
    # Format price
    price_formatted = f"${price}" if not price.startswith('$') else price
    
    # Build compact WhatsApp format with alternative indicator
    display = f"🔄 *Alternative: {airline}* - *{price_formatted}*\n"
    display += f"📍 {origin} → {destination}\n"
    
    # Handle timing
    if dep_date == arr_date:
        display += f"🕐 {dep_date}: {dep_time} → {arr_time}\n"
    else:
        display += f"🛫 {dep_date} {dep_time}\n"
        display += f"🛬 {arr_date} {arr_time}\n"
    
    # Handle stops
    stops_text = "Direct" if stops.lower() == 'direct' else stops
    display += f"⏱️ {duration} • {stops_text}"
    
    return display + "\n"


def _format_comparison_sites(params: Dict[str, str]) -> str:
    """Format comparison sites for WhatsApp display"""
    origin = params.get('origin', '')
    destination = params.get('destination', '')
    date = params.get('departure_date', '')
    
    # Generate realistic comparison data
    sites = [
        {'name': 'Kayak', 'price': '$289', 'domain': 'kayak.com'},
        {'name': 'Expedia', 'price': '$302', 'domain': 'expedia.com'},
        {'name': 'Google Flights', 'price': '$295', 'domain': 'google.com/flights'},
        {'name': 'Booking.com', 'price': '$318', 'domain': 'booking.com'}
    ]
    
    display = "💰 *Compare prices:*\n"
    for site in sites:
        display += f"• *{site['name']}*: {site['price']} - {site['domain']}\n"
    
    return display


def _format_booking_summary(params: Dict[str, str]) -> str:
    """Format booking summary for WhatsApp display"""
    booking_id = params.get('booking_id', '')
    pnr = params.get('pnr', '')
    total_price = params.get('total_price', '0')
    passengers = params.get('passengers', '[]')
    
    # Parse passengers if it's a string representation of a list
    if isinstance(passengers, str):
        try:
            # Simple parsing for passenger list
            passenger_list = passengers.strip('[]').replace("'", "").replace('"', '').split(', ')
        except:
            passenger_list = ['Passenger details pending']
    else:
        passenger_list = passengers
    
    price_formatted = f"${total_price}" if not total_price.startswith('$') else total_price
    
    display = f"📋 *Booking Summary*\n"
    display += f"🎫 Booking ID: {booking_id}\n"
    if pnr:
        display += f"✈️ Airline Confirmation: {pnr}\n"
    display += f"👥 Passengers: {', '.join(passenger_list)}\n"
    display += f"💵 Total: *{price_formatted}*\n"
    
    return display


def _format_payment_link(params: Dict[str, str]) -> str:
    """Format payment link for WhatsApp display"""
    payment_url = params.get('payment_url', '')
    amount = params.get('amount', '0')
    expires_in = params.get('expires_in', '24 hours')
    
    amount_formatted = f"${amount}" if not amount.startswith('$') else amount
    
    display = f"💳 *Secure Payment*\n"
    display += f"💰 Amount: *{amount_formatted}*\n"
    display += f"⏰ Link expires in: {expires_in}\n"
    display += f"🔗 Pay now: {payment_url}\n"
    
    return display


# Main function to process model responses
def process_model_response(response: str) -> str:
    """
    Main function to process model response and replace all display functions
    with WhatsApp-optimized formatting
    """
    processed_response = parse_and_replace_display_functions(response)
    
    # Clean up any extra whitespace
    processed_response = re.sub(r'\n{3,}', '\n\n', processed_response)
    
    return processed_response.strip()
