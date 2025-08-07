def get_available_flights(origin, destination, date):
    # Fake API stub
    return {
        "flights": [
            {"flight_number": "RA101", "from": origin, "to": destination, "date": date, "price": "250,000 TZS"},
            {"flight_number": "RA102", "from": origin, "to": destination, "date": date, "price": "270,000 TZS"},
        ]
    }
