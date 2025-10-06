// App.tsx
import { useState, useEffect, useRef } from "react";
import {
  Box,
  Container,
  CssBaseline,
  ThemeProvider,
  createTheme,
} from "@mui/material";
import { SearchForm } from "./components/SearchForm";
import { LoadingDisplay } from "./components/LoadingDisplay";
import { SearchRequest, SearchResponse } from "./types/flight";
import { FlightResults } from "./components/FlightResults";

const theme = createTheme({
  palette: {
    primary: {
      main: "#2563eb",
    },
    background: {
      default: "#f8fafc",
    },
  },
  typography: {
    fontFamily: [
      "Inter",
      "-apple-system",
      "BlinkMacSystemFont",
      '"Segoe UI"',
      "Roboto",
      "sans-serif",
    ].join(","),
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          borderRadius: 12,
          fontWeight: 600,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: "0 1px 3px 0 rgb(0 0 0 / 0.1)",
        },
      },
    },
  },
});

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";
const POLL_INTERVAL = 1500;
const PROGRESS_UPDATE_INTERVAL = 4000;
const MAX_POLL_DURATION = 120000;

const PROGRESS_STEPS = [
  {
    percentage: 10,
    message: "Connecting to flight databases...",
    duration: 3000,
  },
  {
    percentage: 15,
    message: "Thinking...",
    duration: 4000,
  },
  {
    percentage: 25,
    message: "Searching through 100+ airlines...",
    duration: 3000,
  },
  { percentage: 45, message: "Analyzing flight routes...", duration: 4000 },
  {
    percentage: 60,
    message: "Comparing prices and schedules...",
    duration: 2000,
  },
  { percentage: 75, message: "Finding the best deals...", duration: 2000 },
  { percentage: 85, message: "Gathering flight details...", duration: 4000 },
  { percentage: 95, message: "Finalizing results...", duration: 1000 },
];

// Feature highlights that rotate
const FEATURES = [
  "🔍 The search that takes you hours, done in minutes.",
  "🎯 Never wonder if you found the best price",
  "💰 All fees visible upfront",
  "🗺️ Routes others miss, our cheapest is the ACTUAL CHEAPEST",
  "📋 Clear cancellation rules",
  "🔔 Price drop alerts",
  "⚡ Faster than checking 5 sites",
];

function App() {
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState({
    percentage: 0,
    message: "Initializing search...",
    currentStep: "init",
    resultsFound: 0,
  });
  const [currentFeature, setCurrentFeature] = useState(0);

  const [hasSearched, setHasSearched] = useState(false);
  const searchIdRef = useRef<string | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const searchStartTimeRef = useRef<number>(0);
  const currentStepRef = useRef(0);
  const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [lastSearchParams, setLastSearchParams] =
    useState<SearchRequest | null>(null);

  // Rotate features every 3 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentFeature((prev) => (prev + 1) % FEATURES.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const simulateProgress = () => {
    const elapsed = Date.now() - searchStartTimeRef.current;
    const currentStepIndex = currentStepRef.current;

    if (currentStepIndex < PROGRESS_STEPS.length) {
      const currentStep = PROGRESS_STEPS[currentStepIndex];
      const nextStep = PROGRESS_STEPS[currentStepIndex + 1];

      const stepDuration = PROGRESS_STEPS.slice(0, currentStepIndex + 1).reduce(
        (sum, step) => sum + step.duration,
        0
      );

      if (elapsed >= stepDuration && nextStep) {
        currentStepRef.current++;
        setProgress({
          percentage: nextStep.percentage,
          message: nextStep.message,
          currentStep: "searching",
          resultsFound: 0,
        });
      } else {
        const stepStart = PROGRESS_STEPS.slice(0, currentStepIndex).reduce(
          (sum, step) => sum + step.duration,
          0
        );
        const stepElapsed = elapsed - stepStart;
        const stepProgress = Math.min(stepElapsed / currentStep.duration, 1);

        const startPercentage =
          currentStepIndex > 0
            ? PROGRESS_STEPS[currentStepIndex - 1].percentage
            : 0;
        const targetPercentage = currentStep.percentage;
        const interpolatedPercentage =
          startPercentage + (targetPercentage - startPercentage) * stepProgress;

        setProgress({
          percentage: Math.min(interpolatedPercentage, 95),
          message: currentStep.message,
          currentStep: "searching",
          resultsFound: 0,
        });
      }
    }
  };

  const pollSearchStatus = async (searchId: string) => {
    try {
      const elapsed = Date.now() - searchStartTimeRef.current;
      if (elapsed > MAX_POLL_DURATION) {
        setError("Search is taking longer than expected. Please try again.");
        setLoading(false);

        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
        }
        if (progressIntervalRef.current) {
          clearInterval(progressIntervalRef.current);
        }
        if (pollTimeoutRef.current) {
          clearTimeout(pollTimeoutRef.current);
        }
        return;
      }

      const response = await fetch(`${API_URL}/search/status/${searchId}`);

      if (!response.ok) {
        throw new Error("Failed to fetch search status");
      }

      const data = await response.json();

      if (data.results) {
        const directFlights = data.results.results?.direct_flights || [];
        const nearbyAirports =
          data.results.results?.nearby_airport_options || [];
        const hubConnections = data.results.results?.hub_connections || [];
        const totalFlights =
          directFlights.length + nearbyAirports.length + hubConnections.length;

        setProgress({
          percentage: 100,
          message: "Search complete!",
          currentStep: "completed",
          resultsFound: totalFlights,
        });

        setTimeout(() => {
          const sortedResults: SearchResponse = sortFlightGroups(
            data.results.results
          );
          setSearchResults(sortedResults);
          setLoading(false);
        }, 500);

        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
        }
        if (progressIntervalRef.current) {
          clearInterval(progressIntervalRef.current);
        }
        if (pollTimeoutRef.current) {
          clearTimeout(pollTimeoutRef.current);
        }
      } else if (data.status === "failed" || data.status === "error") {
        setError(
          data.error || data.message || "Search failed. Please try again."
        );
        setLoading(false);

        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
        }
        if (progressIntervalRef.current) {
          clearInterval(progressIntervalRef.current);
        }
        if (pollTimeoutRef.current) {
          clearTimeout(pollTimeoutRef.current);
        }
      }
    } catch (err) {
      console.error("Polling error:", err);
    }
  };

  const sortFlightGroups = (results: any) => {
    const sortByPrice = (flights: any[]) => {
      return [...flights].sort((a, b) => {
        const priceA = parseFloat(a.pricing?.price_total || a.total_price || 0);
        const priceB = parseFloat(b.pricing?.price_total || b.total_price || 0);
        return priceA - priceB;
      });
    };

    return {
      direct_flights: sortByPrice(results.direct_flights || []),
      nearby_airport_options: sortByPrice(results.nearby_airport_options || []),
      hub_connections: sortByPrice(results.hub_connections || []),
      budget_airline_alternatives: results.budget_airline_alternatives,
      search_summary: results.search_summary,
      debug_info: results.debug_info,
    };
  };

  const handleSearch = async (searchData: SearchRequest) => {
    try {
      setLoading(true);
      setError(null);
      setSearchResults(null);
      setLastSearchParams(searchData);
      setHasSearched(true);
      setProgress({
        percentage: 0,
        message: "Initializing search...",
        currentStep: "init",
        resultsFound: 0,
      });

      searchStartTimeRef.current = Date.now();
      currentStepRef.current = 0;

      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }

      const response = await fetch(`${API_URL}/search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(searchData),
      });

      if (!response.ok) {
        throw new Error("Failed to initiate search");
      }

      const initData = await response.json();
      searchIdRef.current = initData.task_id;

      pollTimeoutRef.current = setTimeout(() => {
        if (loading) {
          setError("Search is taking longer than expected. Please try again.");
          setLoading(false);

          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
          }
          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current);
          }
        }
      }, MAX_POLL_DURATION);

      progressIntervalRef.current = setInterval(
        simulateProgress,
        PROGRESS_UPDATE_INTERVAL
      );

      pollIntervalRef.current = setInterval(() => {
        if (searchIdRef.current) {
          pollSearchStatus(searchIdRef.current);
        }
      }, POLL_INTERVAL);

      pollSearchStatus(initData.task_id);
    } catch (err) {
      console.error("Search error:", err);
      setError(
        "Failed to initiate search. Please check your connection and try again."
      );
      setLoading(false);

      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
    }
  };

  const handleNewSearch = () => {
    setSearchResults(null);
    setError(null);
    setLoading(false);

    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
    }
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current);
    }
  };

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
    };
  }, []);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box
        sx={{
          minHeight: "100vh",
          background: "linear-gradient(to bottom, #f0f9ff 0%, #f8fafc 100%)",
          pb: 10,
        }}
      >
        <Container maxWidth="lg">
          <Box sx={{ pt: { xs: 3, md: 6 }, pb: { xs: 2, md: 4 } }}>
            {/* Logo/Header */}
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                mb: { xs: 4, md: 6 },
              }}
            >
              <Box sx={{ textAlign: "center" }}>
                <Box
                  component="h1"
                  sx={{
                    fontSize: { xs: "2rem", sm: "2.5rem", md: "3.5rem" },
                    fontWeight: 700,
                    background:
                      "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
                    backgroundClip: "text",
                    WebkitBackgroundClip: "text",
                    color: "transparent",
                    mb: 1,
                    letterSpacing: "-0.02em",
                    marginTop: "0"
                  }}
                >
                  Rafiki AI
                </Box>
                <Box
                  sx={{
                    fontSize: { xs: "0.875rem", md: "1rem" },
                    color: "text.secondary",
                    fontWeight: 500,
                    mb: 2,
                  }}
                >
                  A smarter way to search for flights.
                </Box>

                {/* Rotating Feature Highlight */}
                {!searchResults && (<Box
                  sx={{
                    minHeight: "32px",
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                  }}
                >
                  <Box
                    sx={{
                      display: "inline-flex",
                      alignItems: "center",
                      px: 3, // Changed from 2 (more horizontal padding)
                      py: 1.5, // Changed from 1 (more vertical padding)
                      borderRadius: 2,
                      backgroundColor: "rgba(37, 99, 235, 0.08)",
                      border: "1px solid rgba(37, 99, 235, 0.2)",
                      animation: "fadeIn 0.5s ease-in-out",
                      "@keyframes fadeIn": {
                        from: { opacity: 0, transform: "translateY(-4px)" },
                        to: { opacity: 1, transform: "translateY(0)" },
                      },
                    }}
                    key={currentFeature}
                  >
                    <Box
                      sx={{
                        fontSize: "1.1rem", // Larger
                        color: "#2563eb",
                        fontWeight: 600,
                      }}
                    >
                      {FEATURES[currentFeature]}
                    </Box>
                  </Box>
                </Box>)}
              </Box>
            </Box>

            {/* Search Form */}
            {!loading && !searchResults && (
              <SearchForm onSearch={handleSearch} />
            )}

            {/* Loading Display */}
            {loading && (
              <LoadingDisplay
                progress={progress.percentage}
                message={progress.message}
                currentStep={progress.currentStep}
                resultsFound={progress.resultsFound}
              />
            )}

            {/* Error Display */}
            {error && (
              <Box
                sx={{
                  mt: 4,
                  p: 3,
                  borderRadius: 3,
                  bgcolor: "#fef2f2",
                  border: "1px solid #fecaca",
                  color: "#dc2626",
                  textAlign: "center",
                  maxWidth: 600,
                  mx: "auto",
                }}
              >
                <Box sx={{ fontWeight: 600, mb: 1 }}>Search Failed</Box>
                <Box sx={{ fontSize: "0.9rem" }}>{error}</Box>
              </Box>
            )}

            {/* Results */}
            {searchResults && !loading && (
              <FlightResults
                results={searchResults}
                onNewSearch={handleNewSearch}
                searchParams={
                  lastSearchParams
                    ? {
                        origin: lastSearchParams.origin,
                        destination: lastSearchParams.destination,
                        departureDate: lastSearchParams.departure_date,
                        returnDate: lastSearchParams.return_date || undefined,
                        adults: lastSearchParams.passengers.adults,
                        children: lastSearchParams.passengers.children,
                        infants: lastSearchParams.passengers.infants,
                        travelClass: lastSearchParams.travel_class,
                      }
                    : undefined
                }
              />
            )}
          </Box>
        </Container>

        {/* Fixed Feedback Button */}
        {hasSearched && (
          <Box
            sx={{
              position: "fixed",
              bottom: 20,
              left: "50%",
              transform: "translateX(-50%)",
              zIndex: 1000,
              width: "300px"
            }}
          >
            <a
              href="https://docs.google.com/forms/d/e/1FAIpQLSfBEX8al_vlEGRITko1x6GFh-6-4aUXcdTva5YzMuOwK9bvWQ/viewform?usp=dialog"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                padding: "10px 20px",
                borderRadius: "12px",
                backgroundColor: "#2563eb",
                border: "none",
                color: "#ffffff",
                textDecoration: "none",
                fontSize: "0.8rem",
                fontWeight: 600,
                transition: "all 0.2s",
                boxShadow: "0 4px 12px rgba(37, 99, 235, 0.3)",
                cursor: "pointer",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = "#1d4ed8";
                e.currentTarget.style.boxShadow =
                  "0 6px 16px rgba(37, 99, 235, 0.4)";
                e.currentTarget.style.transform = "translateY(-2px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = "#2563eb";
                e.currentTarget.style.boxShadow =
                  "0 4px 12px rgba(37, 99, 235, 0.3)";
                e.currentTarget.style.transform = "translateY(0)";
              }}
            >
              <span>🙏</span>
              <span>Experimental - Please share feedback</span>
            </a>
          </Box>
        )}
      </Box>
    </ThemeProvider>
  );
}

export default App;
