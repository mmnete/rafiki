// types/flight.ts

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

// Response when initiating a search
export interface SearchInitResponse {
  search_id: string;
  status: 'initiated';
  message: string;
}

// Response when polling for status
export interface SearchStatusResponse {
  search_id: string;
  status: 'processing' | 'completed' | 'failed';
  progress: {
    percentage: number;
    message: string;
    current_step: string;
    results_found?: number;
  };
  results?: SearchResponse;
  error?: string;
}

export interface SearchResponse {
  direct_flights?: Flight[];
  nearby_airport_options?: Flight[];
  hub_connections?: Flight[];
  search_summary?: any;
  debug_info?: any;
}

export interface FlightGroup {
  group_name: string;
  description: string;
  flights: Flight[];
  ranking_score: number;
  recommendation_reason: string;
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