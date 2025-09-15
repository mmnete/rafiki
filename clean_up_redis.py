import redis # type: ignore

# Connect to your local Redis instance
try:
    r = redis.Redis(host='localhost', port=6379)
    # Ping the server to check the connection
    r.ping()
    print("Connected to Redis server.")

    # Execute FLUSHALL
    r.flushall()
    print("All Redis databases have been cleared.")

except redis.exceptions.ConnectionError as e:
    print(f"Could not connect to Redis: {e}")