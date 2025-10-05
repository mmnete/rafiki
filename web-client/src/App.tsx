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
import {
  SearchRequest,
  SearchStatusResponse,
  SearchResponse,
} from "./types/flight";
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
const POLL_INTERVAL = 1500; // Poll every 1.5 seconds
const PROGRESS_UPDATE_INTERVAL = 4000; // Update progress animation every 4 seconds
const MAX_POLL_DURATION = 120000; // Stop polling after 2 minutes (120 seconds)

// Simulated progress steps for better UX
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

  const [hasSearched, setHasSearched] = useState(false);
  const searchIdRef = useRef<string | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const searchStartTimeRef = useRef<number>(0);
  const currentStepRef = useRef(0);
  const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [lastSearchParams, setLastSearchParams] = useState<SearchRequest | null>(null);

  // Simulate progress updates for better UX
  const simulateProgress = () => {
    const elapsed = Date.now() - searchStartTimeRef.current;
    const currentStepIndex = currentStepRef.current;

    if (currentStepIndex < PROGRESS_STEPS.length) {
      const currentStep = PROGRESS_STEPS[currentStepIndex];
      const nextStep = PROGRESS_STEPS[currentStepIndex + 1];

      // Check if we should move to next step
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
        // Smoothly interpolate within current step
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
          percentage: Math.min(interpolatedPercentage, 95), // Cap at 95% until real results
          message: currentStep.message,
          currentStep: "searching",
          resultsFound: 0,
        });
      }
    }
  };

  const pollSearchStatus = async (searchId: string) => {
    try {
      // Check if we've exceeded max poll duration
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

      // Check if search is completed (backend returns 'results' key when done)
      if (data.results) {
        // Calculate total flights from all three groups
        const directFlights = data.results.results?.direct_flights || [];
        const nearbyAirports =
          data.results.results?.nearby_airport_options || [];
        const hubConnections = data.results.results?.hub_connections || [];
        const totalFlights =
          directFlights.length + nearbyAirports.length + hubConnections.length;

        // Jump to 100% and show completion
        setProgress({
          percentage: 100,
          message: "Search complete!",
          currentStep: "completed",
          resultsFound: totalFlights,
        });

        // Small delay to show 100% before showing results
        setTimeout(() => {
          // Sort and prepare results for display
          const sortedResults = sortFlightGroups(data.results.results);
          setSearchResults(sortedResults);
          setLoading(false);
        }, 500);

        // Clear all intervals and timeout
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
      // If status is 'processing', continue polling and simulating progress
    } catch (err) {
      console.error("Polling error:", err);
      // Continue polling on errors (network might be temporarily down)
    }
  };

  // Sort flight groups: Direct first, then Nearby Airports, then Hub Connections
  // Within each group, sort by price (lowest first)
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
      debug_info: results.debug_info,
    };
  };

  const handleSearch = async (searchData: SearchRequest) => {
    try {
      setLoading(true);
      setError(null);
      setSearchResults(null);
      setLastSearchParams(searchData); // Store search params
      setHasSearched(true); // Mark that user has performed a search
      setProgress({
        percentage: 0,
        message: "Initializing search...",
        currentStep: "init",
        resultsFound: 0,
      });

      // Reset progress tracking
      searchStartTimeRef.current = Date.now();
      currentStepRef.current = 0;

      // Clear any existing intervals
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }

      // Initiate search
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

      // Set a maximum timeout for polling
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

      // Start simulating progress updates
      progressIntervalRef.current = setInterval(
        simulateProgress,
        PROGRESS_UPDATE_INTERVAL
      );

      // Start polling for actual status updates
      pollIntervalRef.current = setInterval(() => {
        if (searchIdRef.current) {
          pollSearchStatus(searchIdRef.current);
        }
      }, POLL_INTERVAL);

      // Poll immediately as well
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

  // Cleanup polling on unmount
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
                justifyContent: "center",
                alignItems: "center",
                mb: { xs: 4, md: 6 },
              }}
            >
              {/* Logo/Title - centered */}
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
                  }}
                >
                  Rafiki
                </Box>
                <Box
                  sx={{
                    fontSize: { xs: "0.875rem", md: "1rem" },
                    color: "text.secondary",
                    fontWeight: 500,
                  }}
                >
                  AI-Powered Flight Search
                </Box>
              </Box>
            </Box>

            {/* Search Form - Only show when not loading and no results */}
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
                searchParams={lastSearchParams ? {
                  origin: lastSearchParams.origin,
                  destination: lastSearchParams.destination,
                  departureDate: lastSearchParams.departure_date,
                  returnDate: lastSearchParams.return_date || undefined,
                  adults: lastSearchParams.adults,
                  children: lastSearchParams.children,
                  infants: lastSearchParams.infants,
                  travelClass: lastSearchParams.travel_class
                } : undefined}
              />
            )}
          </Box>
        </Container>

        {/* Fixed Feedback Button at Bottom Center - Only show after first search */}
        {hasSearched && (
          <Box
            sx={{
              position: "fixed",
              bottom: 0,
              left: 0,
              right: 0,
              display: "flex",
              justifyContent: "center",
              p: 2,
              backgroundColor: "rgba(248, 250, 252, 0.95)",
              backdropFilter: "blur(8px)",
              borderTop: "1px solid rgba(203, 213, 225, 0.3)",
              zIndex: 1000,
            }}
          >
            <a
              href="YOUR_GOOGLE_FORM_URL_HERE"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                padding: "12px 24px",
                borderRadius: "12px",
                backgroundColor: "#2563eb",
                border: "none",
                color: "#ffffff",
                textDecoration: "none",
                fontSize: "0.875rem",
                fontWeight: 600,
                transition: "all 0.2s",
                boxShadow: "0 4px 12px rgba(37, 99, 235, 0.3)",
                cursor: "pointer",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = "#1d4ed8";
                e.currentTarget.style.boxShadow = "0 6px 16px rgba(37, 99, 235, 0.4)";
                e.currentTarget.style.transform = "translateY(-2px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = "#2563eb";
                e.currentTarget.style.boxShadow = "0 4px 12px rgba(37, 99, 235, 0.3)";
                e.currentTarget.style.transform = "translateY(0)";
              }}
            >
              <span style={{ fontSize: "1.2rem" }}>😊</span>
              <span>Rafiki is a Trial Product - Please Share Feedback</span>
            </a>
          </Box>
        )}
      </Box>
    </ThemeProvider>
  );
}

export default App;