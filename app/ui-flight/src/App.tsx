import { useState } from 'react';
import { Box, Container, CssBaseline, ThemeProvider, Typography, createTheme } from '@mui/material';
import { ErrorOutline } from '@mui/icons-material';
import { SearchForm } from './components/SearchForm';
import { FlightList } from './components/FlightList';
import { SearchRequest, SearchResponse } from './types/flight';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 8,
          },
        },
      },
    },
  },
});

const MOCK_RESPONSE: SearchResponse = {
  search_summary: {
    origin: "SFO",
    destination: "JFK",
    departure_date: "2025-10-03",
    passengers: 1,
    class: "economy",
    total_flights_found: 1
  },
  flights: [
    {
      airline: {
        code: "RA",
        name: "Rafiki Airways"
      },
      departure: {
        airport: "SFO",
        terminal: "2",
        time: "2025-10-03T10:00:00",
        formatted: "10:00 AM"
      },
      arrival: {
        airport: "JFK",
        terminal: "4",
        time: "2025-10-03T18:30:00",
        formatted: "6:30 PM"
      },
      duration: {
        total_minutes: 510,
        formatted: "8h 30m"
      },
      stops: 0,
      price: {
        total: 299.99,
        base: 250.00,
        taxes: 49.99,
        currency: "USD"
      },
      cabin_class: "Economy",
      fare_class: "Basic",
      baggage: {
        carry_on: { included: true, fee: 0 },
        checked: { included: false, fee: 30 }
      },
      amenities: {
        wifi: true,
        power: true,
        entertainment: true,
        meal: false
      },
      segments: [
        {
          flight_number: "RA101",
          from: "SFO",
          to: "JFK",
          departure: "2025-10-03T10:00:00",
          arrival: "2025-10-03T18:30:00",
          duration_minutes: 510,
          aircraft: "Boeing 777-300ER"
        }
      ],
      refundable: true,
      changeable: true,
      layover_time: "3 hours"
    }
  ]
};

function App() {
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string>('');
  const [progressPercentage, setProgressPercentage] = useState(0);

  const handleSearch = async (searchData: SearchRequest) => {
    try {
      setLoading(true);
      setError(null);
      setSearchResults(null);
      setProgress('Initiating search...');
      setProgressPercentage(0);

      // Simulate a loading sequence
      const steps = [
        { message: 'Connecting to flight providers...', percentage: 20 },
        { message: 'Searching available flights...', percentage: 40 },
        { message: 'Finding best options...', percentage: 60 },
        { message: 'Checking prices...', percentage: 80 },
        { message: 'Preparing results...', percentage: 90 }
      ];

      let currentStep = 0;
      const showProgress = () => {
        if (currentStep < steps.length) {
          setProgress(steps[currentStep].message);
          setProgressPercentage(steps[currentStep].percentage);
          currentStep++;
          setTimeout(showProgress, 800);
        } else {
          // Show mock results after progress completes
          setTimeout(() => {
            setSearchResults(MOCK_RESPONSE);
            setLoading(false);
            setProgress('');
            setProgressPercentage(100);
          }, 500);
        }
      };

      // Make the actual API call but don't wait for it
      fetch('https://rafiki-ai-982000624478.herokuapp.com/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          origin: "SFO",
          destination: "JFK",
          departure_date: "2025-10-03",
          return_date: "2025-10-17",
          passengers: {
            adults: 1,
            children: 0,
            infants: 0
          },
          travel_class: "economy",
          special_needs: []
        }),
      })
        .then(response => response.json())
        .then(data => {
          console.log('API Response:', data);
        })
        .catch(error => {
          console.error('API Error:', error);
        });

      // Start the progress simulation
      showProgress();
    } catch (err) {
      console.error('Search error:', err);
      setError('Failed to initiate search. Please try again.');
      setLoading(false);
      setProgressPercentage(0);
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ 
        minHeight: '100vh',
        background: 'linear-gradient(to bottom, #e3f2fd 0%, #f5f5f5 100%)',
        pb: 8 
      }}>
        <Container maxWidth="lg">
          <Box sx={{ pt: 4, pb: 2, textAlign: 'center' }}>
            <Box 
              component="h1" 
              sx={{ 
                fontSize: '2.5rem', 
                fontWeight: 'bold',
                color: 'primary.main',
                mb: 4,
                letterSpacing: '0.02em'
              }}
            >
              Rafiki
            </Box>
            <SearchForm onSearch={handleSearch} loading={loading} />
            {loading && progress && (
              <Box
                sx={{
                  mt: 2,
                  p: 3,
                  borderRadius: 2,
                  bgcolor: '#e3f2fd',
                  color: 'primary.main',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 2
                }}
              >
                <Box sx={{ width: '100%', maxWidth: 400 }}>
                  <Box sx={{ 
                    width: '100%',
                    height: 4,
                    bgcolor: 'rgba(25, 118, 210, 0.1)',
                    borderRadius: 2,
                    overflow: 'hidden',
                    position: 'relative'
                  }}>
                    <Box
                      sx={{
                        width: `${progressPercentage}%`,
                        height: '100%',
                        bgcolor: 'primary.main',
                        position: 'absolute',
                        left: 0,
                        top: 0,
                        transition: 'width 0.5s ease-in-out',
                      }}
                    />
                  </Box>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Box
                    sx={{
                      display: 'inline-block',
                      width: 20,
                      height: 20,
                      borderRadius: '50%',
                      border: '2px solid currentColor',
                      borderTopColor: 'transparent',
                      animation: 'spin 1s linear infinite',
                      '@keyframes spin': {
                        '0%': {
                          transform: 'rotate(0deg)',
                        },
                        '100%': {
                          transform: 'rotate(360deg)',
                        },
                      },
                    }}
                  />
                  <Typography variant="body1" sx={{ fontWeight: 500 }}>
                    {progress}
                  </Typography>
                </Box>
              </Box>
            )}
            {error && (
              <Box
                sx={{
                  mt: 2,
                  p: 2,
                  borderRadius: 2,
                  bgcolor: '#ffebee',
                  color: '#c62828',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1
                }}
              >
                <ErrorOutline fontSize="small" />
                {error}
              </Box>
            )}
            {searchResults && !error && (
              <Box sx={{ mt: 4 }}>
                <FlightList flights={searchResults.flights} />
              </Box>
            )}
          </Box>
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;