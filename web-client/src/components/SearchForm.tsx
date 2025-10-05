// components/SearchForm.tsx
import { useState } from "react";
import {
  Box,
  TextField,
  Button,
  Grid,
  MenuItem,
  Paper,
  Typography,
  Container,
  InputAdornment,
  Fade,
  Autocomplete,
  CircularProgress,
} from "@mui/material";
import {
  FlightTakeoff,
  FlightLand,
  Person,
  BusinessCenter,
  Search as SearchIcon,
  AirlineSeatReclineNormal,
  ChildCare,
} from "@mui/icons-material";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { LocalizationProvider, DatePicker } from "@mui/x-date-pickers";
import { SearchRequest } from "../types/flight";

interface Airport {
  code: string;
  name: string;
  city: string;
  country: string;
}

interface SearchFormProps {
  onSearch: (searchData: SearchRequest) => void;
}

export const SearchForm: React.FC<SearchFormProps> = ({ onSearch }) => {
  const [formData, setFormData] = useState<SearchRequest>({
    origin: "",
    destination: "",
    departure_date: "",
    passengers: {
      adults: 1,
      children: 0,
      infants: 0,
    },
    travel_class: "economy",
  });

  const [originOptions, setOriginOptions] = useState<Airport[]>([]);
  const [destinationOptions, setDestinationOptions] = useState<Airport[]>([]);
  const [originLoading, setOriginLoading] = useState(false);
  const [destinationLoading, setDestinationLoading] = useState(false);

  // Debounce helper
  const useDebounce = (callback: Function, delay: number) => {
    const timeoutRef = useState<NodeJS.Timeout | null>(null);
    return (...args: any[]) => {
      if (timeoutRef[0]) clearTimeout(timeoutRef[0]);
      timeoutRef[1](setTimeout(() => callback(...args), delay));
    };
  };

  // Function to search airports
  const searchAirports = async (query: string): Promise<Airport[]> => {
    if (query.length < 2) return [];

    try {
      // Replace with your actual API endpoint
      // Examples: RapidAPI Aviation Stack, AviationStack, or your own backend
      const response = await fetch(
        `https://your-api-endpoint.com/airports?search=${encodeURIComponent(
          query
        )}`
      );
      const data = await response.json();

      // Map the response to your Airport interface
      // Adjust based on your API's response structure
      return data.airports || [];
    } catch (error) {
      console.error("Error fetching airports:", error);
      return [];
    }
  };

  // Alternative: Use a static airport list (for demo/offline use)
  const searchAirportsStatic = (query: string): Airport[] => {
    const airports: Airport[] = [
      // USA
      {
        code: "JFK",
        name: "John F. Kennedy International Airport",
        city: "New York",
        country: "USA",
      },
      {
        code: "LAX",
        name: "Los Angeles International Airport",
        city: "Los Angeles",
        country: "USA",
      },
      {
        code: "SFO",
        name: "San Francisco International Airport",
        city: "San Francisco",
        country: "USA",
      },
      {
        code: "ORD",
        name: "O'Hare International Airport",
        city: "Chicago",
        country: "USA",
      },
      {
        code: "ATL",
        name: "Hartsfield-Jackson Atlanta International Airport",
        city: "Atlanta",
        country: "USA",
      },
      {
        code: "MIA",
        name: "Miami International Airport",
        city: "Miami",
        country: "USA",
      },
      {
        code: "DFW",
        name: "Dallas/Fort Worth International Airport",
        city: "Dallas",
        country: "USA",
      },
      {
        code: "DEN",
        name: "Denver International Airport",
        city: "Denver",
        country: "USA",
      },
      {
        code: "SEA",
        name: "Seattle-Tacoma International Airport",
        city: "Seattle",
        country: "USA",
      },
      {
        code: "LAS",
        name: "Harry Reid International Airport",
        city: "Las Vegas",
        country: "USA",
      },
      {
        code: "MCO",
        name: "Orlando International Airport",
        city: "Orlando",
        country: "USA",
      },
      {
        code: "PHX",
        name: "Phoenix Sky Harbor International Airport",
        city: "Phoenix",
        country: "USA",
      },
      {
        code: "IAH",
        name: "George Bush Intercontinental Airport",
        city: "Houston",
        country: "USA",
      },
      {
        code: "BOS",
        name: "Logan International Airport",
        city: "Boston",
        country: "USA",
      },
      {
        code: "EWR",
        name: "Newark Liberty International Airport",
        city: "Newark",
        country: "USA",
      },
      {
        code: "MSP",
        name: "Minneapolis-St Paul International Airport",
        city: "Minneapolis",
        country: "USA",
      },
      {
        code: "DTW",
        name: "Detroit Metropolitan Airport",
        city: "Detroit",
        country: "USA",
      },
      {
        code: "PHL",
        name: "Philadelphia International Airport",
        city: "Philadelphia",
        country: "USA",
      },
      {
        code: "LGA",
        name: "LaGuardia Airport",
        city: "New York",
        country: "USA",
      },
      {
        code: "BWI",
        name: "Baltimore/Washington International Airport",
        city: "Baltimore",
        country: "USA",
      },
      {
        code: "DCA",
        name: "Ronald Reagan Washington National Airport",
        city: "Washington DC",
        country: "USA",
      },
      {
        code: "IAD",
        name: "Washington Dulles International Airport",
        city: "Washington DC",
        country: "USA",
      },
      {
        code: "SAN",
        name: "San Diego International Airport",
        city: "San Diego",
        country: "USA",
      },
      {
        code: "PDX",
        name: "Portland International Airport",
        city: "Portland",
        country: "USA",
      },
      {
        code: "SLC",
        name: "Salt Lake City International Airport",
        city: "Salt Lake City",
        country: "USA",
      },
      {
        code: "TPA",
        name: "Tampa International Airport",
        city: "Tampa",
        country: "USA",
      },
      {
        code: "CLT",
        name: "Charlotte Douglas International Airport",
        city: "Charlotte",
        country: "USA",
      },
      {
        code: "HNL",
        name: "Daniel K. Inouye International Airport",
        city: "Honolulu",
        country: "USA",
      },
      {
        code: "AUS",
        name: "Austin-Bergstrom International Airport",
        city: "Austin",
        country: "USA",
      },
      {
        code: "BNA",
        name: "Nashville International Airport",
        city: "Nashville",
        country: "USA",
      },
      {
        code: "RDU",
        name: "Raleigh-Durham International Airport",
        city: "Raleigh/Durham",
        country: "USA",
      },
      {
        code: "STL",
        name: "St. Louis Lambert International Airport",
        city: "St. Louis",
        country: "USA",
      },
      {
        code: "MSY",
        name: "Louis Armstrong New Orleans International Airport",
        city: "New Orleans",
        country: "USA",
      },
      {
        code: "SAT",
        name: "San Antonio International Airport",
        city: "San Antonio",
        country: "USA",
      },
      {
        code: "SJC",
        name: "Norman Y. Mineta San Jose International Airport",
        city: "San Jose",
        country: "USA",
      },
      {
        code: "OAK",
        name: "Oakland International Airport",
        city: "Oakland",
        country: "USA",
      },
      {
        code: "SMF",
        name: "Sacramento International Airport",
        city: "Sacramento",
        country: "USA",
      },
      {
        code: "DAL",
        name: "Dallas Love Field",
        city: "Dallas",
        country: "USA",
      },
      {
        code: "HOU",
        name: "William P. Hobby Airport",
        city: "Houston",
        country: "USA",
      },
      {
        code: "MDW",
        name: "Chicago Midway International Airport",
        city: "Chicago",
        country: "USA",
      },
      {
        code: "IND",
        name: "Indianapolis International Airport",
        city: "Indianapolis",
        country: "USA",
      },
      {
        code: "CMH",
        name: "John Glenn Columbus International Airport",
        city: "Columbus",
        country: "USA",
      },
      {
        code: "CLE",
        name: "Cleveland Hopkins International Airport",
        city: "Cleveland",
        country: "USA",
      },
      {
        code: "PIT",
        name: "Pittsburgh International Airport",
        city: "Pittsburgh",
        country: "USA",
      },
      {
        code: "CVG",
        name: "Cincinnati/Northern Kentucky International Airport",
        city: "Cincinnati",
        country: "USA",
      },
      {
        code: "MCI",
        name: "Kansas City International Airport",
        city: "Kansas City",
        country: "USA",
      },
      {
        code: "RSW",
        name: "Southwest Florida International Airport",
        city: "Fort Myers",
        country: "USA",
      },
      {
        code: "FLL",
        name: "Fort Lauderdale-Hollywood International Airport",
        city: "Fort Lauderdale",
        country: "USA",
      },
      {
        code: "PBI",
        name: "Palm Beach International Airport",
        city: "West Palm Beach",
        country: "USA",
      },
      {
        code: "JAX",
        name: "Jacksonville International Airport",
        city: "Jacksonville",
        country: "USA",
      },
      {
        code: "MKE",
        name: "Milwaukee Mitchell International Airport",
        city: "Milwaukee",
        country: "USA",
      },
      {
        code: "OMA",
        name: "Eppley Airfield",
        city: "Omaha",
        country: "USA",
      },
      {
        code: "ABQ",
        name: "Albuquerque International Sunport",
        city: "Albuquerque",
        country: "USA",
      },
      {
        code: "BUF",
        name: "Buffalo Niagara International Airport",
        city: "Buffalo",
        country: "USA",
      },
      {
        code: "ONT",
        name: "Ontario International Airport",
        city: "Ontario",
        country: "USA",
      },
      {
        code: "BUR",
        name: "Hollywood Burbank Airport",
        city: "Burbank",
        country: "USA",
      },
      {
        code: "SNA",
        name: "John Wayne Airport",
        city: "Orange County",
        country: "USA",
      },
      {
        code: "ANC",
        name: "Ted Stevens Anchorage International Airport",
        city: "Anchorage",
        country: "USA",
      },

      // Canada
      {
        code: "YYZ",
        name: "Toronto Pearson International Airport",
        city: "Toronto",
        country: "Canada",
      },
      {
        code: "YVR",
        name: "Vancouver International Airport",
        city: "Vancouver",
        country: "Canada",
      },
      {
        code: "YUL",
        name: "Montréal-Pierre Elliott Trudeau International Airport",
        city: "Montreal",
        country: "Canada",
      },
      {
        code: "YYC",
        name: "Calgary International Airport",
        city: "Calgary",
        country: "Canada",
      },
      {
        code: "YEG",
        name: "Edmonton International Airport",
        city: "Edmonton",
        country: "Canada",
      },
      {
        code: "YOW",
        name: "Ottawa Macdonald-Cartier International Airport",
        city: "Ottawa",
        country: "Canada",
      },
      {
        code: "YWG",
        name: "Winnipeg Richardson International Airport",
        city: "Winnipeg",
        country: "Canada",
      },
      {
        code: "YHZ",
        name: "Halifax Stanfield International Airport",
        city: "Halifax",
        country: "Canada",
      },

      // Mexico
      {
        code: "MEX",
        name: "Mexico City International Airport",
        city: "Mexico City",
        country: "Mexico",
      },
      {
        code: "CUN",
        name: "Cancún International Airport",
        city: "Cancún",
        country: "Mexico",
      },
      {
        code: "GDL",
        name: "Guadalajara International Airport",
        city: "Guadalajara",
        country: "Mexico",
      },
      {
        code: "MTY",
        name: "Monterrey International Airport",
        city: "Monterrey",
        country: "Mexico",
      },
      {
        code: "TIJ",
        name: "Tijuana International Airport",
        city: "Tijuana",
        country: "Mexico",
      },
      {
        code: "PVR",
        name: "Puerto Vallarta International Airport",
        city: "Puerto Vallarta",
        country: "Mexico",
      },
      {
        code: "SJD",
        name: "Los Cabos International Airport",
        city: "San José del Cabo",
        country: "Mexico",
      },
      {
        code: "BJX",
        name: "Del Bajío International Airport",
        city: "León/Guanajuato",
        country: "Mexico",
      },

      // Europe - UK & Ireland
      {
        code: "LHR",
        name: "London Heathrow Airport",
        city: "London",
        country: "UK",
      },
      {
        code: "LGW",
        name: "London Gatwick Airport",
        city: "London",
        country: "UK",
      },
      {
        code: "STN",
        name: "London Stansted Airport",
        city: "London",
        country: "UK",
      },
      {
        code: "MAN",
        name: "Manchester Airport",
        city: "Manchester",
        country: "UK",
      },
      {
        code: "EDI",
        name: "Edinburgh Airport",
        city: "Edinburgh",
        country: "UK",
      },
      {
        code: "BHX",
        name: "Birmingham Airport",
        city: "Birmingham",
        country: "UK",
      },
      { code: "GLA", name: "Glasgow Airport", city: "Glasgow", country: "UK" },
      {
        code: "DUB",
        name: "Dublin Airport",
        city: "Dublin",
        country: "Ireland",
      },

      // Europe - France
      {
        code: "CDG",
        name: "Charles de Gaulle Airport",
        city: "Paris",
        country: "France",
      },
      {
        code: "ORY",
        name: "Paris Orly Airport",
        city: "Paris",
        country: "France",
      },
      {
        code: "NCE",
        name: "Nice Côte d'Azur Airport",
        city: "Nice",
        country: "France",
      },
      {
        code: "LYS",
        name: "Lyon-Saint Exupéry Airport",
        city: "Lyon",
        country: "France",
      },
      {
        code: "MRS",
        name: "Marseille Provence Airport",
        city: "Marseille",
        country: "France",
      },

      // Europe - Germany
      {
        code: "FRA",
        name: "Frankfurt Airport",
        city: "Frankfurt",
        country: "Germany",
      },
      {
        code: "MUC",
        name: "Munich Airport",
        city: "Munich",
        country: "Germany",
      },
      {
        code: "BER",
        name: "Berlin Brandenburg Airport",
        city: "Berlin",
        country: "Germany",
      },
      {
        code: "DUS",
        name: "Düsseldorf Airport",
        city: "Düsseldorf",
        country: "Germany",
      },
      {
        code: "HAM",
        name: "Hamburg Airport",
        city: "Hamburg",
        country: "Germany",
      },

      // Europe - Spain
      {
        code: "MAD",
        name: "Adolfo Suárez Madrid-Barajas Airport",
        city: "Madrid",
        country: "Spain",
      },
      {
        code: "BCN",
        name: "Barcelona-El Prat Airport",
        city: "Barcelona",
        country: "Spain",
      },
      {
        code: "AGP",
        name: "Málaga-Costa del Sol Airport",
        city: "Málaga",
        country: "Spain",
      },
      {
        code: "PMI",
        name: "Palma de Mallorca Airport",
        city: "Palma de Mallorca",
        country: "Spain",
      },
      {
        code: "SVQ",
        name: "Seville Airport",
        city: "Seville",
        country: "Spain",
      },

      // Europe - Italy
      {
        code: "FCO",
        name: "Leonardo da Vinci-Fiumicino Airport",
        city: "Rome",
        country: "Italy",
      },
      {
        code: "MXP",
        name: "Milan Malpensa Airport",
        city: "Milan",
        country: "Italy",
      },
      {
        code: "VCE",
        name: "Venice Marco Polo Airport",
        city: "Venice",
        country: "Italy",
      },
      {
        code: "NAP",
        name: "Naples International Airport",
        city: "Naples",
        country: "Italy",
      },
      {
        code: "BLQ",
        name: "Bologna Guglielmo Marconi Airport",
        city: "Bologna",
        country: "Italy",
      },

      // Europe - Netherlands
      {
        code: "AMS",
        name: "Amsterdam Airport Schiphol",
        city: "Amsterdam",
        country: "Netherlands",
      },

      // Europe - Switzerland
      {
        code: "ZRH",
        name: "Zurich Airport",
        city: "Zurich",
        country: "Switzerland",
      },
      {
        code: "GVA",
        name: "Geneva Airport",
        city: "Geneva",
        country: "Switzerland",
      },

      // Europe - Belgium
      {
        code: "BRU",
        name: "Brussels Airport",
        city: "Brussels",
        country: "Belgium",
      },

      // Europe - Austria
      {
        code: "VIE",
        name: "Vienna International Airport",
        city: "Vienna",
        country: "Austria",
      },

      // Europe - Scandinavia
      {
        code: "CPH",
        name: "Copenhagen Airport",
        city: "Copenhagen",
        country: "Denmark",
      },
      {
        code: "ARN",
        name: "Stockholm Arlanda Airport",
        city: "Stockholm",
        country: "Sweden",
      },
      { code: "OSL", name: "Oslo Airport", city: "Oslo", country: "Norway" },
      {
        code: "HEL",
        name: "Helsinki-Vantaa Airport",
        city: "Helsinki",
        country: "Finland",
      },

      // Europe - Portugal
      {
        code: "LIS",
        name: "Lisbon Portela Airport",
        city: "Lisbon",
        country: "Portugal",
      },
      {
        code: "OPO",
        name: "Porto Airport",
        city: "Porto",
        country: "Portugal",
      },

      // Europe - Greece
      {
        code: "ATH",
        name: "Athens International Airport",
        city: "Athens",
        country: "Greece",
      },

      // Europe - Turkey
      {
        code: "IST",
        name: "Istanbul Airport",
        city: "Istanbul",
        country: "Turkey",
      },
      {
        code: "SAW",
        name: "Sabiha Gökçen International Airport",
        city: "Istanbul",
        country: "Turkey",
      },

      // Europe - Poland
      {
        code: "WAW",
        name: "Warsaw Chopin Airport",
        city: "Warsaw",
        country: "Poland",
      },

      // Europe - Czech Republic
      {
        code: "PRG",
        name: "Václav Havel Airport Prague",
        city: "Prague",
        country: "Czech Republic",
      },

      // Asia - Japan
      {
        code: "NRT",
        name: "Narita International Airport",
        city: "Tokyo",
        country: "Japan",
      },
      {
        code: "HND",
        name: "Tokyo Haneda Airport",
        city: "Tokyo",
        country: "Japan",
      },
      {
        code: "KIX",
        name: "Kansai International Airport",
        city: "Osaka",
        country: "Japan",
      },
      {
        code: "NGO",
        name: "Chubu Centrair International Airport",
        city: "Nagoya",
        country: "Japan",
      },
      {
        code: "FUK",
        name: "Fukuoka Airport",
        city: "Fukuoka",
        country: "Japan",
      },

      // Asia - China
      {
        code: "PEK",
        name: "Beijing Capital International Airport",
        city: "Beijing",
        country: "China",
      },
      {
        code: "PVG",
        name: "Shanghai Pudong International Airport",
        city: "Shanghai",
        country: "China",
      },
      {
        code: "CAN",
        name: "Guangzhou Baiyun International Airport",
        city: "Guangzhou",
        country: "China",
      },
      {
        code: "CTU",
        name: "Chengdu Shuangliu International Airport",
        city: "Chengdu",
        country: "China",
      },
      {
        code: "SZX",
        name: "Shenzhen Bao'an International Airport",
        city: "Shenzhen",
        country: "China",
      },
      {
        code: "HKG",
        name: "Hong Kong International Airport",
        city: "Hong Kong",
        country: "Hong Kong",
      },

      // Asia - South Korea
      {
        code: "ICN",
        name: "Incheon International Airport",
        city: "Seoul",
        country: "South Korea",
      },
      {
        code: "GMP",
        name: "Gimpo International Airport",
        city: "Seoul",
        country: "South Korea",
      },

      // Asia - Southeast Asia
      {
        code: "SIN",
        name: "Singapore Changi Airport",
        city: "Singapore",
        country: "Singapore",
      },
      {
        code: "BKK",
        name: "Suvarnabhumi Airport",
        city: "Bangkok",
        country: "Thailand",
      },
      {
        code: "DMK",
        name: "Don Mueang International Airport",
        city: "Bangkok",
        country: "Thailand",
      },
      {
        code: "KUL",
        name: "Kuala Lumpur International Airport",
        city: "Kuala Lumpur",
        country: "Malaysia",
      },
      {
        code: "CGK",
        name: "Soekarno-Hatta International Airport",
        city: "Jakarta",
        country: "Indonesia",
      },
      {
        code: "DPS",
        name: "Ngurah Rai International Airport",
        city: "Bali",
        country: "Indonesia",
      },
      {
        code: "MNL",
        name: "Ninoy Aquino International Airport",
        city: "Manila",
        country: "Philippines",
      },
      {
        code: "HAN",
        name: "Noi Bai International Airport",
        city: "Hanoi",
        country: "Vietnam",
      },
      {
        code: "SGN",
        name: "Tan Son Nhat International Airport",
        city: "Ho Chi Minh City",
        country: "Vietnam",
      },

      // Asia - India
      {
        code: "DEL",
        name: "Indira Gandhi International Airport",
        city: "New Delhi",
        country: "India",
      },
      {
        code: "BOM",
        name: "Chhatrapati Shivaji Maharaj International Airport",
        city: "Mumbai",
        country: "India",
      },
      {
        code: "BLR",
        name: "Kempegowda International Airport",
        city: "Bangalore",
        country: "India",
      },
      {
        code: "MAA",
        name: "Chennai International Airport",
        city: "Chennai",
        country: "India",
      },
      {
        code: "HYD",
        name: "Rajiv Gandhi International Airport",
        city: "Hyderabad",
        country: "India",
      },

      // Middle East - UAE
      {
        code: "DXB",
        name: "Dubai International Airport",
        city: "Dubai",
        country: "UAE",
      },
      {
        code: "AUH",
        name: "Abu Dhabi International Airport",
        city: "Abu Dhabi",
        country: "UAE",
      },

      // Middle East - Qatar
      {
        code: "DOH",
        name: "Hamad International Airport",
        city: "Doha",
        country: "Qatar",
      },

      // Middle East - Saudi Arabia
      {
        code: "JED",
        name: "King Abdulaziz International Airport",
        city: "Jeddah",
        country: "Saudi Arabia",
      },
      {
        code: "RUH",
        name: "King Khalid International Airport",
        city: "Riyadh",
        country: "Saudi Arabia",
      },

      // Middle East - Israel
      {
        code: "TLV",
        name: "Ben Gurion Airport",
        city: "Tel Aviv",
        country: "Israel",
      },

      // Middle East - Other
      {
        code: "CAI",
        name: "Cairo International Airport",
        city: "Cairo",
        country: "Egypt",
      },
      {
        code: "AMM",
        name: "Queen Alia International Airport",
        city: "Amman",
        country: "Jordan",
      },
      {
        code: "BEY",
        name: "Rafic Hariri International Airport",
        city: "Beirut",
        country: "Lebanon",
      },
      {
        code: "KWI",
        name: "Kuwait International Airport",
        city: "Kuwait City",
        country: "Kuwait",
      },
      {
        code: "MCT",
        name: "Muscat International Airport",
        city: "Muscat",
        country: "Oman",
      },
      {
        code: "BAH",
        name: "Bahrain International Airport",
        city: "Manama",
        country: "Bahrain",
      },

      // Africa - Tanzania (as specifically requested)
      {
        code: "JRO",
        name: "Kilimanjaro International Airport",
        city: "Arusha",
        country: "Tanzania",
      },
      {
        code: "ZNZ",
        name: "Abeid Amani Karume International Airport",
        city: "Zanzibar",
        country: "Tanzania",
      },

      // Africa - South Africa
      {
        code: "JNB",
        name: "O.R. Tambo International Airport",
        city: "Johannesburg",
        country: "South Africa",
      },
      {
        code: "CPT",
        name: "Cape Town International Airport",
        city: "Cape Town",
        country: "South Africa",
      },
      {
        code: "DUR",
        name: "King Shaka International Airport",
        city: "Durban",
        country: "South Africa",
      },

      // Africa - Kenya
      {
        code: "NBO",
        name: "Jomo Kenyatta International Airport",
        city: "Nairobi",
        country: "Kenya",
      },

      // Africa - Ethiopia
      {
        code: "ADD",
        name: "Addis Ababa Bole International Airport",
        city: "Addis Ababa",
        country: "Ethiopia",
      },

      // Africa - Morocco
      {
        code: "CMN",
        name: "Mohammed V International Airport",
        city: "Casablanca",
        country: "Morocco",
      },
      {
        code: "RAK",
        name: "Marrakesh Menara Airport",
        city: "Marrakesh",
        country: "Morocco",
      },

      // Africa - Nigeria
      {
        code: "LOS",
        name: "Murtala Muhammed International Airport",
        city: "Lagos",
        country: "Nigeria",
      },
      {
        code: "ABV",
        name: "Nnamdi Azikiwe International Airport",
        city: "Abuja",
        country: "Nigeria",
      },

      // Africa - Other
      {
        code: "ALG",
        name: "Houari Boumediene Airport",
        city: "Algiers",
        country: "Algeria",
      },
      {
        code: "TUN",
        name: "Tunis-Carthage International Airport",
        city: "Tunis",
        country: "Tunisia",
      },
      {
        code: "ACC",
        name: "Kotoka International Airport",
        city: "Accra",
        country: "Ghana",
      },
      {
        code: "LUN",
        name: "Kenneth Kaunda International Airport",
        city: "Lusaka",
        country: "Zambia",
      },
      {
        code: "HRE",
        name: "Robert Gabriel Mugabe International Airport",
        city: "Harare",
        country: "Zimbabwe",
      },
      {
        code: "EBB",
        name: "Entebbe International Airport",
        city: "Entebbe",
        country: "Uganda",
      },

      // --- East Africa ---
      {
        code: "NBO",
        name: "Jomo Kenyatta International Airport",
        city: "Nairobi",
        country: "Kenya",
      },
      {
        code: "MBA",
        name: "Moi International Airport",
        city: "Mombasa",
        country: "Kenya",
      },
      {
        code: "DAR",
        name: "Julius Nyerere International Airport",
        city: "Dar es Salaam",
        country: "Tanzania",
      },
      {
        code: "ZNZ",
        name: "Abeid Amani Karume International Airport",
        city: "Zanzibar",
        country: "Tanzania",
      },
      {
        code: "JRO",
        name: "Kilimanjaro International Airport",
        city: "Arusha / Moshi",
        country: "Tanzania",
      },
      {
        code: "KGL",
        name: "Kigali International Airport",
        city: "Kigali",
        country: "Rwanda",
      },
      {
        code: "BJM",
        name: "Melchior Ndadaye International Airport",
        city: "Bujumbura",
        country: "Burundi",
      },
      {
        code: "MGQ",
        name: "Aden Adde International Airport",
        city: "Mogadishu",
        country: "Somalia",
      },
      {
        code: "HGA",
        name: "Egal International Airport",
        city: "Hargeisa",
        country: "Somaliland",
      },
      {
        code: "ADD",
        name: "Addis Ababa Bole International Airport",
        city: "Addis Ababa",
        country: "Ethiopia",
      },
      {
        code: "ASM",
        name: "Asmara International Airport",
        city: "Asmara",
        country: "Eritrea",
      },

      // --- Southern Africa ---
      {
        code: "JNB",
        name: "O. R. Tambo International Airport",
        city: "Johannesburg",
        country: "South Africa",
      },
      {
        code: "CPT",
        name: "Cape Town International Airport",
        city: "Cape Town",
        country: "South Africa",
      },
      {
        code: "DUR",
        name: "King Shaka International Airport",
        city: "Durban",
        country: "South Africa",
      },
      {
        code: "MPM",
        name: "Maputo International Airport",
        city: "Maputo",
        country: "Mozambique",
      },
      {
        code: "WDH",
        name: "Hosea Kutako International Airport",
        city: "Windhoek",
        country: "Namibia",
      },
      {
        code: "GBE",
        name: "Sir Seretse Khama International Airport",
        city: "Gaborone",
        country: "Botswana",
      },
      {
        code: "LAD",
        name: "Quatro de Fevereiro International Airport",
        city: "Luanda",
        country: "Angola",
      },

      // --- West Africa ---
      {
        code: "LOS",
        name: "Murtala Muhammed International Airport",
        city: "Lagos",
        country: "Nigeria",
      },
      {
        code: "ABV",
        name: "Nnamdi Azikiwe International Airport",
        city: "Abuja",
        country: "Nigeria",
      },
      {
        code: "DKR",
        name: "Blaise Diagne International Airport",
        city: "Dakar",
        country: "Senegal",
      },
      {
        code: "ROB",
        name: "Roberts International Airport",
        city: "Monrovia",
        country: "Liberia",
      },
      {
        code: "FNA",
        name: "Lungi International Airport",
        city: "Freetown",
        country: "Sierra Leone",
      },
      {
        code: "BJL",
        name: "Banjul International Airport",
        city: "Banjul",
        country: "Gambia",
      },
      {
        code: "COO",
        name: "Cadjehoun Airport",
        city: "Cotonou",
        country: "Benin",
      },

      // --- Central Africa ---
      {
        code: "FIH",
        name: "N'djili International Airport",
        city: "Kinshasa",
        country: "Democratic Republic of the Congo",
      },
      {
        code: "BZV",
        name: "Maya-Maya Airport",
        city: "Brazzaville",
        country: "Republic of the Congo",
      },
      {
        code: "DLA",
        name: "Douala International Airport",
        city: "Douala",
        country: "Cameroon",
      },
      {
        code: "NSI",
        name: "Yaoundé Nsimalen International Airport",
        city: "Yaoundé",
        country: "Cameroon",
      },
      {
        code: "LBV",
        name: "Léon-Mba International Airport",
        city: "Libreville",
        country: "Gabon",
      },
      {
        code: "NDJ",
        name: "N'Djamena International Airport",
        city: "N'Djamena",
        country: "Chad",
      },
      {
        code: "BGF",
        name: "Bangui M'Poko International Airport",
        city: "Bangui",
        country: "Central African Republic",
      },
    ];

    const lowerQuery = query.toLowerCase();
    return airports.filter(
      (airport) =>
        airport.code.toLowerCase().includes(lowerQuery) ||
        airport.name.toLowerCase().includes(lowerQuery) ||
        airport.city.toLowerCase().includes(lowerQuery)
    );
  };

  const handleOriginSearch = useDebounce(async (query: string) => {
    if (query.length < 2) {
      setOriginOptions([]);
      return;
    }
    setOriginLoading(true);

    // Use static list for demo, replace with searchAirports(query) for API
    const results = searchAirportsStatic(query);
    setOriginOptions(results);
    setOriginLoading(false);
  }, 300);

  const handleDestinationSearch = useDebounce(async (query: string) => {
    if (query.length < 2) {
      setDestinationOptions([]);
      return;
    }
    setDestinationLoading(true);

    // Use static list for demo, replace with searchAirports(query) for API
    const results = searchAirportsStatic(query);
    setDestinationOptions(results);
    setDestinationLoading(false);
  }, 300);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Submitting form data:", formData);
    onSearch(formData);
  };

  const formatDate = (date: Date | null): string => {
    if (!date) return "";
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  const handleChange = (field: string, value: any) => {
    if (field === "departure_date" || field === "return_date") {
      const formattedDate = value ? formatDate(value) : "";
      setFormData((prev) => ({
        ...prev,
        [field]: formattedDate,
      }));
    } else if (field.includes(".")) {
      const [parent, child] = field.split(".");
      setFormData((prev) => ({
        ...prev,
        [parent]: {
          ...(prev[parent as keyof SearchRequest] as any),
          [child]: Number(value),
        },
      }));
    } else {
      setFormData((prev) => ({
        ...prev,
        [field]: value,
      }));
    }
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Container maxWidth="md">
        <Fade in={true}>
          <Paper
            elevation={3}
            sx={{
              p: 4,
              borderRadius: 2,
              bgcolor: "white",
              transition: "transform 0.3s ease-in-out",
              "&:hover": {
                transform: "scale(1.01)",
              },
            }}
          >
            <Typography
              variant="h4"
              gutterBottom
              sx={{ color: "#1976d2", fontWeight: 500, mb: 4 }}
            >
              Find Your Flight
            </Typography>
            <Box component="form" onSubmit={handleSubmit}>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Autocomplete
                    freeSolo
                    options={originOptions}
                    loading={originLoading}
                    getOptionLabel={(option) =>
                      typeof option === "string"
                        ? option
                        : `${option.code} - ${option.name}, ${option.city}`
                    }
                    onInputChange={(event, value) => {
                      handleOriginSearch(value);
                    }}
                    onChange={(event, value) => {
                      if (value && typeof value !== "string") {
                        handleChange("origin", value.code);
                      }
                    }}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        required
                        label="From"
                        placeholder="Search city or airport code"
                        InputProps={{
                          ...params.InputProps,
                          startAdornment: (
                            <>
                              <InputAdornment position="start">
                                <FlightTakeoff color="primary" />
                              </InputAdornment>
                              {params.InputProps.startAdornment}
                            </>
                          ),
                          endAdornment: (
                            <>
                              {originLoading ? (
                                <CircularProgress color="inherit" size={20} />
                              ) : null}
                              {params.InputProps.endAdornment}
                            </>
                          ),
                        }}
                      />
                    )}
                    renderOption={(props, option) => {
                      const { key, ...otherProps } = props;
                      return (
                        <Box component="li" key={key} {...otherProps}>
                          <Box>
                            <Typography variant="body1" fontWeight={500}>
                              {option.code} - {option.city}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {option.name}
                            </Typography>
                          </Box>
                        </Box>
                      );
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <Autocomplete
                    freeSolo
                    options={destinationOptions}
                    loading={destinationLoading}
                    getOptionLabel={(option) =>
                      typeof option === "string"
                        ? option
                        : `${option.code} - ${option.name}, ${option.city}`
                    }
                    onInputChange={(event, value) => {
                      handleDestinationSearch(value);
                    }}
                    onChange={(event, value) => {
                      if (value && typeof value !== "string") {
                        handleChange("destination", value.code);
                      }
                    }}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        required
                        label="To"
                        placeholder="Search city or airport code"
                        InputProps={{
                          ...params.InputProps,
                          startAdornment: (
                            <>
                              <InputAdornment position="start">
                                <FlightLand color="primary" />
                              </InputAdornment>
                              {params.InputProps.startAdornment}
                            </>
                          ),
                          endAdornment: (
                            <>
                              {destinationLoading ? (
                                <CircularProgress color="inherit" size={20} />
                              ) : null}
                              {params.InputProps.endAdornment}
                            </>
                          ),
                        }}
                      />
                    )}
                    renderOption={(props, option) => {
                      const { key, ...otherProps } = props;
                      return (
                        <Box component="li" key={key} {...otherProps}>
                          <Box>
                            <Typography variant="body1" fontWeight={500}>
                              {option.code} - {option.city}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {option.name}
                            </Typography>
                          </Box>
                        </Box>
                      );
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <DatePicker
                    label="Departure Date"
                    value={
                      formData.departure_date
                        ? new Date(formData.departure_date)
                        : null
                    }
                    onChange={(date) => handleChange("departure_date", date)}
                    slotProps={{
                      textField: {
                        required: true,
                        fullWidth: true,
                      },
                    }}
                    disablePast
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <DatePicker
                    label="Return Date (Optional)"
                    value={
                      formData.return_date
                        ? new Date(formData.return_date)
                        : null
                    }
                    onChange={(date) => handleChange("return_date", date)}
                    slotProps={{
                      textField: {
                        fullWidth: true,
                      },
                    }}
                    disablePast
                    minDate={
                      formData.departure_date
                        ? new Date(formData.departure_date)
                        : undefined
                    }
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField
                    required
                    fullWidth
                    type="number"
                    label="Adults"
                    value={formData.passengers.adults}
                    onChange={(e) =>
                      handleChange(
                        "passengers.adults",
                        parseInt(e.target.value)
                      )
                    }
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">
                          <Person color="primary" />
                        </InputAdornment>
                      ),
                      inputProps: { min: 1, max: 9 },
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Children (2-11)"
                    value={formData.passengers.children}
                    onChange={(e) =>
                      handleChange(
                        "passengers.children",
                        parseInt(e.target.value)
                      )
                    }
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">
                          <AirlineSeatReclineNormal color="primary" />
                        </InputAdornment>
                      ),
                      inputProps: { min: 0, max: 9 },
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Infants (Under 2)"
                    value={formData.passengers.infants}
                    onChange={(e) =>
                      handleChange(
                        "passengers.infants",
                        parseInt(e.target.value)
                      )
                    }
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">
                          <ChildCare color="primary" />
                        </InputAdornment>
                      ),
                      inputProps: { min: 0, max: 9 },
                    }}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    required
                    fullWidth
                    select
                    label="Travel Class"
                    value={formData.travel_class}
                    onChange={(e) =>
                      handleChange("travel_class", e.target.value)
                    }
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">
                          <BusinessCenter color="primary" />
                        </InputAdornment>
                      ),
                    }}
                  >
                    <MenuItem value="economy">Economy</MenuItem>
                    <MenuItem value="premium_economy">Premium Economy</MenuItem>
                    <MenuItem value="business">Business</MenuItem>
                    <MenuItem value="first">First</MenuItem>
                  </TextField>
                </Grid>
              </Grid>
              <Box sx={{ mt: 4, display: "flex", justifyContent: "center" }}>
                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  sx={{
                    minWidth: 200,
                    height: 48,
                    borderRadius: 24,
                    textTransform: "none",
                    fontSize: "1.1rem",
                  }}
                  startIcon={<SearchIcon />}
                >
                  Search Flights
                </Button>
              </Box>
            </Box>
          </Paper>
        </Fade>
      </Container>
    </LocalizationProvider>
  );
};
