export interface SearchRequest {
  origin: string;
  destination: string;
  departure_date: string;
  return_date?: string;
  passengers: {
    adults: number;
    children: number;
    infants: number;
  };
  travel_class: 'economy' | 'premium_economy' | 'business' | 'first';
  special_needs?: string[];
}

export interface SearchResponse {
  search_summary: {
    origin: string;
    destination: string;
    departure_date: string;
    passengers: number;
    class: string;
    total_flights_found: number;
  };
  flights: Flight[];
}

export interface Flight {
  airline: {
    code: string;
    name: string;
  };
  price: {
    total: number;
    base: number;
    taxes: number;
    currency: string;
  };
  duration: {
    total_minutes: number;
    formatted: string;
  };
  departure: {
    airport: string;
    terminal: string | null;
    time: string;
    formatted: string;
  };
  arrival: {
    airport: string;
    terminal: string | null;
    time: string;
    formatted: string;
  };
  segments: FlightSegment[];
  stops: number;
  layover_time: string | null;
  baggage: {
    carry_on: {
      included: boolean;
      fee: number;
    };
    checked: {
      included: boolean;
      fee: number;
    };
  };
  amenities: {
    wifi: boolean;
    power: boolean;
    entertainment: boolean;
    meal: boolean;
  };
  fare_class: string;
  cabin_class: string;
  refundable: boolean;
  changeable: boolean;
}

export interface FlightSegment {
  flight_number: string;
  from: string;
  to: string;
  departure: string;
  arrival: string;
  duration_minutes: number;
  aircraft: string;
}