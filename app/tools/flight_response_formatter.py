# flight_response_formatter.py
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import urllib.parse


@dataclass
class FlightInfo:
    # A single flight offer can have multiple legs, so we'll store all details
    # This stores the IATA code (e.g., 'SA') and the full name (e.g., 'SOUTH AFRICAN AIRWAYS')
    airline_code: str
    airline_name: str
    
    # Aircraft information
    aircraft: Optional[str]
    flight_number: Optional[str]
    
    # Times for the *entire* journey
    departure_time: str
    arrival_time: str
    
    # Pricing information
    price: float
    currency: str
    
    # Duration and stops for the *entire* journey
    duration: Optional[str]
    
    # Detailed baggage information
    checked_bags: Optional[str]
    cabin_bags: Optional[str]
    
    stops: int = 0
    # Booking information
    booking_class: str = "ECONOMY"

@dataclass
class FormattedFlightResponse:
    flights: List[FlightInfo]
    origin_code: str
    destination_code: str
    departure_date: str
    return_date: Optional[str]
    search_links: List[str]
    formatted_output: str

class FlightResponseFormatter:
    """
    Formats flight search results into consistent output with corroboration links
    """
    
    def __init__(self):
        # Booking site configurations for generating links
        self.booking_sites = {
            'kayak': {
                'name': 'Kayak',
                'base_url': 'https://www.kayak.com/flights',
                'url_builder': self._build_kayak_url
            },
            'skyscanner': {
                'name': 'Skyscanner',
                'base_url': 'https://www.skyscanner.com/transport/flights',
                'url_builder': self._build_skyscanner_url
            },
            'expedia': {
                'name': 'Expedia',
                'base_url': 'https://www.expedia.com/Flights',
                'url_builder': self._build_expedia_url
            },
            'google_flights': {
                'name': 'Google Flights',
                'base_url': 'https://www.google.com/travel/flights',
                'url_builder': self._build_google_flights_url
            }
        }
    
    def format_flight_response(self, 
                             flight_data: Dict[str, Any], 
                             search_params: Dict[str, Any]) -> FormattedFlightResponse:
        """
        Format flight search results into consistent output with corroboration links
        
        Args:
            flight_data: Raw flight data from API
            search_params: Original search parameters
            
        Returns:
            FormattedFlightResponse: Structured response with formatting and links
        """
        
        # Parse flight data into structured format
        flights = self._parse_flight_data(flight_data)
        
        # Generate corroboration links
        search_links = self._generate_search_links(search_params)
        
        # Create formatted output text
        formatted_output = self._create_formatted_output(flights, search_params, search_links)
        
        return FormattedFlightResponse(
            flights=flights,
            origin_code=search_params.get('origin', ''),
            destination_code=search_params.get('destination', ''),
            departure_date=search_params.get('departure_date', ''),
            return_date=search_params.get('return_date'),
            search_links=search_links,
            formatted_output=formatted_output
        )
    
    def _parse_flight_data(self, flight_data: Dict[str, Any]) -> List[FlightInfo]:
        flights = []
        flight_list = flight_data.get('flights', [])

        for flight in flight_list:
            try:
                # Correctly access the new and updated fields
                price_total = float(flight.get('price_total', 0))
                currency = flight.get('currency', 'USD')  # Default to USD
                
                # Using the new keys for airline information
                airline_code = flight.get('airline_code', 'Unknown')
                airline_name = flight.get('airline_name', 'Unknown Airline')
                aircraft_name = flight.get('aircraft_name', 'Unknown Aircraft')
                
                # Extracting departure and arrival times
                departure_time_str = flight.get('departure_time', '')
                arrival_time_str = flight.get('arrival_time', '')
                duration_str = flight.get('duration', None)

                # Get baggage information
                checked_bags_info = flight.get('included_checked_bags', {})
                cabin_bags_info = flight.get('included_cabin_bags', {})
                
                # Create a simplified string for baggage
                checked_bags = ""
                if 'quantity' in checked_bags_info:
                    checked_bags += f"{checked_bags_info['quantity']} checked bag(s)"
                if 'weight' in checked_bags_info:
                    if checked_bags:
                        checked_bags += " and "
                    checked_bags += f"{checked_bags_info['weight']}{checked_bags_info.get('weightUnit', 'KG')}"

                # Append the new FlightInfo object with more details
                flights.append(FlightInfo(
                    airline_code=airline_code,
                    airline_name=airline_name,
                    aircraft=aircraft_name,
                    flight_number=None,
                    departure_time=departure_time_str,
                    arrival_time=arrival_time_str,
                    price=price_total,
                    currency=currency,
                    duration=duration_str,
                    stops=flight.get('number_of_segments', 1) - 1,
                    checked_bags=checked_bags,
                    cabin_bags=f"{cabin_bags_info.get('quantity', 0)} cabin bag(s)" if 'quantity' in cabin_bags_info else "No cabin bags specified"
                ))
            except Exception as e:
                print(f"Error parsing flight data: {e}")
                continue

        flights.sort(key=lambda x: x.price)
        return flights

    
    def _create_formatted_output(self, 
                               flights: List[FlightInfo], 
                               search_params: Dict[str, Any], 
                               search_links: List[str]) -> str:
        """Create the formatted output string"""
        
        try:
            origin = search_params.get('origin', '')
            destination = search_params.get('destination', '')
            departure_date = search_params.get('departure_date', '')
            return_date = search_params.get('return_date')
            
            # Format header
            output = f"✈️ **Safari za Ndege: {origin} ➜ {destination}**\n"
            output += f"📅 **Tarehe ya Kuondoka:** {self._format_date(departure_date)}\n"
            
            if return_date:
                output += f"📅 **Tarehe ya Kurudi:** {self._format_date(return_date)}\n"
            
            output += "\n" + "="*50 + "\n\n"
            
            # Format flights
            if not flights:
                output += "❌ **Hakuna safari za ndege zilizopatikana kwa sasa.**\n\n"
            else:
                output += f"🎯 **Pata Safari {len(flights)} za Ndege:**\n\n"
                
                for i, flight in enumerate(flights[:5], 1):  # Show top 5 flights
                    output += f"**{i}. {flight.airline_name}**\n"
                    
                    if flight.flight_number:
                        output += f"   🔢 Namba ya Safari: {flight.flight_number}\n"
                    
                    # Format times
                    if flight.departure_time and flight.arrival_time:
                        output += f"   🕐 Muda: {flight.departure_time} - {flight.arrival_time}\n"
                    
                    if flight.duration:
                        output += f"   ⏱️ Muda wa Safari: {flight.duration}\n"
                    
                    # Format price with currency symbol
                    currency_symbol = self._get_currency_symbol(flight.currency)
                    formatted_price = f"{currency_symbol}{flight.price:,.0f}"
                    output += f"   💰 **Bei: {formatted_price}**\n"
                    
                    if flight.stops > 0:
                        output += f"   🔄 Kusimama: {flight.stops} {'mara' if flight.stops == 1 else 'mara'}\n"
                    
                    output += f"   🎫 Daraja: {self._translate_class(flight.booking_class)}\n\n"
            
            # Add corroboration links
            output += "🔗 **Thibitisha Bei na Hifadhi Safari:**\n"
            for link in search_links:
                site_name = link.split('|')[0] if '|' in link else "Link"
                site_url = link.split('|')[1] if '|' in link else link
                output += f"• [{site_name}]({site_url})\n"
            
            output += "\n💡 **Dokezo:** Bei zinaweza kubadilika. Thibitisha bei za sasa kwenye tovuti hizi kabla ya kuhifadhi.\n"
            
            return output
        except Exception as e:
            # This will catch ANY error that happens during the function call or assignment
            print(f"ERROR: An unhandled exception occurred in or after _create_formatted_output call: {e}")
            import traceback
            traceback.print_exc() # This will print the full error traceback
            formatted_output = "Samahani, kuna tatizo lililotokea katika kuunda ujumbe wa majibu. (Sorry, an issue occurred while creating the response message.)"
            # You might want to return an error message to the user here.
            return ""
    
    def _generate_search_links(self, search_params: Dict[str, Any]) -> List[str]:
        """Generate corroboration links for major booking sites"""
        links = []
        
        for site_key, site_config in self.booking_sites.items():
            try:
                url = site_config['url_builder'](search_params)
                if url:
                    links.append(f"{site_config['name']}|{url}")
            except Exception as e:
                print(f"Error generating {site_key} link: {e}")
                continue
        
        return links
    
    def _build_kayak_url(self, params: Dict[str, Any]) -> str:
        """Build Kayak search URL"""
        origin = params.get('origin', '')
        destination = params.get('destination', '')
        departure_date = params.get('departure_date', '').replace('-', '')
        return_date = params.get('return_date', '')
        adults = params.get('adults', 1)
        
        if return_date:
            return_date = return_date.replace('-', '')
            trip_type = 'roundtrip'
            url = f"https://www.kayak.com/flights/{origin}-{destination}/{departure_date}/{return_date}/{adults}adults"
        else:
            url = f"https://www.kayak.com/flights/{origin}-{destination}/{departure_date}/{adults}adults"
        
        return url
    
    def _build_skyscanner_url(self, params: Dict[str, Any]) -> str:
        """Build Skyscanner search URL"""
        origin = params.get('origin', '')
        destination = params.get('destination', '')
        departure_date = params.get('departure_date', '').replace('-', '')
        return_date = params.get('return_date', '')
        adults = params.get('adults', 1)
        
        if return_date:
            return_date = return_date.replace('-', '')
            url = f"https://www.skyscanner.com/transport/flights/{origin}/{destination}/{departure_date}/{return_date}/"
        else:
            url = f"https://www.skyscanner.com/transport/flights/{origin}/{destination}/{departure_date}/"
        
        return url + f"?adults={adults}"
    
    def _build_expedia_url(self, params: Dict[str, Any]) -> str:
        """Build Expedia search URL"""
        origin = params.get('origin', '')
        destination = params.get('destination', '')
        departure_date = params.get('departure_date', '')
        return_date = params.get('return_date', '')
        adults = params.get('adults', 1)
        
        url_params = {
            'flight-type': 'roundtrip' if return_date else 'oneway',
            'starDate': departure_date,
            'mode': 's',
            'trip': 'flight',
            'leg1': f'from:{origin},to:{destination},departure:{departure_date}TANYT',
            'passengers': f'adults:{adults},children:0,seniors:0,infantinlap:Y'
        }
        
        if return_date:
            url_params['endDate'] = return_date
            url_params['leg2'] = f'from:{destination},to:{origin},departure:{return_date}TANYT'
        
        query_string = urllib.parse.urlencode(url_params)
        return f"https://www.expedia.com/Flights-Search?{query_string}"
    
    def _build_google_flights_url(self, params: Dict[str, Any]) -> str:
        """Build Google Flights search URL"""
        origin = params.get('origin', '')
        destination = params.get('destination', '')
        departure_date = params.get('departure_date', '')
        return_date = params.get('return_date', '')
        adults = params.get('adults', 1)
        
        if return_date:
            url = f"https://www.google.com/travel/flights?q=Flights%20to%20{destination}%20from%20{origin}%20on%20{departure_date}%20through%20{return_date}%20for%20{adults}%20adults"
        else:
            url = f"https://www.google.com/travel/flights?q=Flights%20to%20{destination}%20from%20{origin}%20on%20{departure_date}%20for%20{adults}%20adults"
        
        return url
    
    def _format_date(self, date_str: str) -> str:
        """Format date string to readable format"""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.strftime('%d %B %Y')
        except:
            return date_str
    
    def _get_currency_symbol(self, currency: str) -> str:
        """Get currency symbol"""
        symbols = {
            'TZS': 'TSh ',
            'USD': '$',
            'EUR': '€',
            'KES': 'KSh ',
            'UGX': 'USh ',
            'RWF': 'RF ',
        }
        return symbols.get(currency.upper(), f'{currency} ')
    
    def _translate_class(self, booking_class: str) -> str:
        """Translate booking class to Swahili"""
        translations = {
            'ECONOMY': 'Kawaida',
            'PREMIUM_ECONOMY': 'Kawaida Premium',
            'BUSINESS': 'Biashara',
            'FIRST': 'Daraja la Kwanza'
        }
        return translations.get(booking_class.upper(), booking_class)
