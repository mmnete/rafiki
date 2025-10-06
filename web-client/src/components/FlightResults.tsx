// components/FlightResults.tsx
import {
  Box,
  Button,
  Typography,
  Chip,
  Card,
  CardContent,
  TextField,
  Alert,
  Stepper,
  Step,
  StepLabel,
} from "@mui/material";
import {
  Refresh,
  Flight,
  LocationCity,
  Hub,
  OpenInNew,
  NotificationsActive,
  Close,
} from "@mui/icons-material";
import { ConnectingAirports } from "@mui/icons-material";
import { useState, useEffect, useMemo } from "react";

interface FlightResultsProps {
  results: any;
  onNewSearch: () => void;
  searchParams?: {
    origin: string;
    destination: string;
    departureDate: string;
    returnDate?: string;
    adults: number;
    children: number;
    infants: number;
    travelClass: string;
  };
}

const groupConfig = {
  direct_flights: {
    title: "Standard Routes",
    icon: Flight,
    color: "#10b981",
    description: "Direct routing between airports",
  },
  nearby_airport_options: {
    title: "Nearby Airports",
    icon: LocationCity,
    color: "#3b82f6",
    description: "Alternative airports nearby",
  },
  hub_connections: {
    title: "Hub Connections",
    icon: Hub,
    color: "#8b5cf6",
    description: "Creative routes using popular hubs",
  },
};

export const FlightResults: React.FC<FlightResultsProps> = ({
  results,
  onNewSearch,
  searchParams,
}) => {
  const [expandedFlight, setExpandedFlight] = useState<string | null>(null);
  const [showCompareMenu, setShowCompareMenu] = useState(false);
  const compareLabel = useMemo(() => {
    const memeLabels = [
      "👑 We're the GOAT. Go see the runner-ups.", // Implies others are second best
      "🧠 Big Brain Move: Confirm this price is unmatched.", // Suggests our deal is the smartest choice
      "👀 Sus? Go see their higher prices.", // Direct suggestion that competitors are more expensive
      "📈 Stonks! Compare to confirm max value.", // Focuses on confirming our great value
      "🔥 This is fine. (Their prices are not). Compare.", // Implying others have "fire" (bad) prices
      "🛡️ Expensive? Cap. See why they're priced higher.", // Stating our price isn't a lie, others might be
      "🍿 Plot Twist: See how much you're saving with us.", // Highlights savings based on competitors
      "🤝 Real Ones know. But go check the competition.", // Playfully confident
      "💅 Slay that booking. Go find a bigger price tag.", // Dares the user to find a worse deal
      "🚀 Time to Compare. (It’s a flex).", // Implies checking is showing off the great deal
      "💯 Vibe check: Go see who failed the price test.", // Implies competitors have failed
      "✨ Peep those 'almost as good' prices, fam.", // Subtly diminishes the competition
    ];

    return memeLabels[Math.floor(Math.random() * memeLabels.length)];
  }, []);
  const [showPriceAlertExpanded, setShowPriceAlertExpanded] = useState(false);
  const [alertEmail, setAlertEmail] = useState("");
  const [alertStatus, setAlertStatus] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle");
  const [alertMessage, setAlertMessage] = useState("");
  const [expandedPolicies, setExpandedPolicies] = useState<{
    [key: string]: boolean;
  }>({});
  const [showBookingGuide, setShowBookingGuide] = useState<{
    [key: string]: boolean;
  }>({});

  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

  // Load saved email from localStorage on mount
  // Load saved email from localStorage on mount
  useEffect(() => {
    const savedEmail = localStorage.getItem("priceAlertEmail");
    if (savedEmail) {
      setAlertEmail(savedEmail);
    }
  }, []);

  const trackBookingClick = async (
    flightOfferId: string,
    origin: string,
    destination: string,
    departureDate: string,
    returnDate: string | null,
    price: number
  ) => {
    try {
      await fetch(`${API_URL}/booking-click`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          flight_offer_id: flightOfferId,
          origin,
          destination,
          departure_date: departureDate,
          return_date: returnDate,
          price,
          booking_site: "skyscanner",
        }),
      });
    } catch (err) {
      console.error("Failed to track booking click:", err);
    }
  };

  const createPriceAlert = async () => {
    if (!alertEmail || !alertEmail.includes("@")) {
      setAlertStatus("error");
      setAlertMessage("Please enter a valid email address");
      return;
    }

    setAlertStatus("loading");

    try {
      const response = await fetch(`${API_URL}/price-alert`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: alertEmail,
          origin: searchParams?.origin,
          destination: searchParams?.destination,
          departure_date: searchParams?.departureDate,
          return_date: searchParams?.returnDate,
          passengers: {
            adults: searchParams?.adults || 1,
            children: searchParams?.children || 0,
            infants: searchParams?.infants || 0,
          },
          travel_class: searchParams?.travelClass || "economy",
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setAlertStatus("success");
        setAlertMessage(
          "Price alert created! We'll email you when prices drop."
        );
        localStorage.setItem("priceAlertEmail", alertEmail);
        setTimeout(() => {
          setShowPriceAlertExpanded(false);
          setAlertStatus("idle");
        }, 3000);
      } else {
        setAlertStatus("error");
        setAlertMessage(data.error || "Failed to create price alert");
      }
    } catch (err) {
      setAlertStatus("error");
      setAlertMessage("Failed to create price alert. Please try again.");
    }
  };

  const availableGroups = Object.entries(results)
    .filter(([key, flights]: [string, any]) => {
      return (
        key !== "debug_info" &&
        flights &&
        Array.isArray(flights) &&
        flights.length > 0
      );
    })
    .map(([groupKey, flights]: [string, any]) => {
      const avgPrice =
        flights.reduce(
          (sum: number, f: any) =>
            sum + parseFloat(f.pricing?.price_total || f.total_price || 0),
          0
        ) / flights.length;
      return { groupKey, flights, avgPrice };
    })
    .sort((a, b) => a.avgPrice - b.avgPrice);

  const getPolicyHighlights = (flight: any) => {
    const outbound = flight.outbound_flight || flight;
    const highlights = [];

    if (outbound.baggage?.carry_on_included) {
      highlights.push({
        icon: "✓",
        text: "Carry-on included",
        color: "#10b981",
      });
    } else {
      highlights.push({ icon: "✗", text: "Carry-on extra", color: "#ef4444" });
    }

    if (outbound.baggage?.checked_bags_included > 0) {
      highlights.push({
        icon: "✓",
        text: `${outbound.baggage.checked_bags_included} checked bag${
          outbound.baggage.checked_bags_included > 1 ? "s" : ""
        }`,
        color: "#10b981",
      });
    } else {
      highlights.push({
        icon: "✗",
        text: "Checked bags extra",
        color: "#ef4444",
      });
    }

    const cancelPolicy =
      outbound.cancellation_policy?.all_fares ||
      outbound.fare_details?.refundable;
    if (cancelPolicy === "refundable" || outbound.fare_details?.refundable) {
      highlights.push({ icon: "✓", text: "Refundable", color: "#10b981" });
    } else if (
      typeof cancelPolicy === "string" &&
      cancelPolicy.includes("24h_free_cancel")
    ) {
      highlights.push({ icon: "~", text: "24h free cancel", color: "#f59e0b" });
    } else {
      highlights.push({ icon: "✗", text: "Non-refundable", color: "#ef4444" });
    }

    if (outbound.fare_details?.changeable) {
      highlights.push({ icon: "✓", text: "Changes allowed", color: "#10b981" });
    }

    if (outbound.ancillary_services?.seat_selection_available) {
      highlights.push({ icon: "✓", text: "Seat selection", color: "#10b981" });
    }

    return highlights.slice(0, 3);
  };

  // Extract route information from flight
  const getRouteInfo = (flight: any) => {
    const isRoundtrip = flight.outbound_flight && flight.return_flight;
    const outbound = isRoundtrip ? flight.outbound_flight : flight;
    const returnFlight = isRoundtrip ? flight.return_flight : null;

    // Get routing info
    const routingUsed = flight.routing_used || [];

    return {
      isRoundtrip,
      outbound,
      returnFlight,
      outboundRoute:
        routingUsed.length > 0
          ? routingUsed
          : [outbound.origin, outbound.destination],
      returnRoute: returnFlight
        ? flight.return_routing_used || [
            returnFlight.origin,
            returnFlight.destination,
          ]
        : null,
      isHubConnection:
        routingUsed.length > 2 || (outbound.stops && outbound.stops > 0),
      hubCities: routingUsed.slice(1, -1), // Cities in between origin and destination
    };
  };

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  const formatDateForSkyscanner = (dateString: string) => {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}${month}${day}`;
  };

  const buildSkyscannerUrl = (
    origin: string,
    destination: string,
    departureDate: string,
    returnDate?: string
  ) => {
    const depDate = formatDateForSkyscanner(departureDate);
    const retDate = returnDate ? formatDateForSkyscanner(returnDate) : "";
    const baseUrl = "https://www.skyscanner.com/transport/flights";

    if (retDate) {
      return `${baseUrl}/${origin}/${destination}/${depDate}/${retDate}/`;
    } else {
      return `${baseUrl}/${origin}/${destination}/${depDate}/`;
    }
  };

  const getGoogleFlightsUrl = (flight: any): string => {
    // Use the flight's own google_flights_url
    if (flight.google_flights_url) {
      return flight.google_flights_url;
    }

    // Fallback: Build a generic Google Flights URL from flight data
    const outbound = flight.outbound_flight || flight;
    const returnFlight = flight.return_flight;

    const params = new URLSearchParams({
      engine: "google_flights",
      departure_id: outbound.origin,
      arrival_id: outbound.destination,
      outbound_date: outbound.departure_time?.split("T")[0] || "",
      hl: "en",
      gl: "us",
      type: returnFlight ? "1" : "2",
    });

    if (returnFlight?.departure_time) {
      params.set("return_date", returnFlight.departure_time.split("T")[0]);
    }

    return `https://serpapi.com/search?${params.toString()}`;
  };

  const buildCompareUrl = (platform: "skyscanner" | "kayak") => {
    if (!searchParams) return "#";

    const { origin, destination, departureDate, returnDate } = searchParams;

    if (platform === "skyscanner") {
      const depDate = formatDateForSkyscanner(departureDate);
      const retDate = returnDate ? formatDateForSkyscanner(returnDate) : "";
      const baseUrl = "https://www.skyscanner.com/transport/flights";

      if (retDate) {
        return `${baseUrl}/${origin}/${destination}/${depDate}/${retDate}/`;
      }
      return `${baseUrl}/${origin}/${destination}/${depDate}/`;
    } else {
      // Kayak
      const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
      };

      const depDate = formatDate(departureDate);
      const retDate = returnDate ? formatDate(returnDate) : "";

      if (retDate) {
        return `https://www.kayak.com/flights/${origin}-${destination}/${depDate}/${retDate}?sort=bestflight_a`;
      }
      return `https://www.kayak.com/flights/${origin}-${destination}/${depDate}?sort=bestflight_a`;
    }
  };

  // Render the booking guide for hub connections
  const renderBookingGuide = (routeInfo: any) => {
    const { outboundRoute, returnRoute, isRoundtrip, outbound, returnFlight } =
      routeInfo;

    return (
      <Box
        sx={{
          mt: 2,
          p: 2.5,
          bgcolor: "#fef3c7",
          borderRadius: 2,
          border: "1px solid #fbbf24",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          <ConnectingAirports sx={{ color: "#f59e0b", fontSize: 20 }} />
          <Typography
            variant="subtitle2"
            sx={{ fontWeight: 600, color: "#92400e" }}
          >
            Multi-City Booking Required
          </Typography>
        </Box>

        <Typography
          variant="body2"
          sx={{ mb: 2, color: "#78350f", fontSize: "0.85rem" }}
        >
          This route requires booking separate tickets for each leg. Follow
          these steps:
        </Typography>

        <Box sx={{ mb: 2 }}>
          <Typography
            variant="caption"
            sx={{ fontWeight: 600, color: "#92400e", display: "block", mb: 1 }}
          >
            Outbound Journey:
          </Typography>
          <Stepper orientation="vertical" sx={{ pl: 1 }}>
            {outboundRoute.map((airport: string, idx: number) => {
              if (idx === outboundRoute.length - 1) return null;
              const nextAirport = outboundRoute[idx + 1];

              return (
                <Step key={idx} active completed={false}>
                  <StepLabel
                    sx={{
                      "& .MuiStepLabel-label": {
                        fontSize: "0.8rem",
                        color: "#78350f",
                      },
                    }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Typography
                        variant="body2"
                        sx={{ fontSize: "0.8rem", fontWeight: 500 }}
                      >
                        {airport} → {nextAirport}
                      </Typography>
                      <Button
                        size="small"
                        variant="outlined"
                        endIcon={<OpenInNew sx={{ fontSize: 14 }} />}
                        onClick={() => {
                          const departureDate =
                            idx === 0
                              ? outbound.departure_time
                              : outbound.segments?.[idx]?.departure_time ||
                                outbound.departure_time;

                          window.open(
                            buildSkyscannerUrl(
                              airport,
                              nextAirport,
                              departureDate
                            ),
                            "_blank",
                            "noopener,noreferrer"
                          );
                        }}
                        sx={{
                          textTransform: "none",
                          fontSize: "0.7rem",
                          py: 0.25,
                          px: 1,
                          borderColor: "#f59e0b",
                          color: "#92400e",
                          "&:hover": {
                            borderColor: "#d97706",
                            bgcolor: "#fef3c740",
                          },
                        }}
                      >
                        Search
                      </Button>
                    </Box>
                  </StepLabel>
                </Step>
              );
            })}
          </Stepper>
        </Box>

        {isRoundtrip && returnRoute && (
          <Box>
            <Typography
              variant="caption"
              sx={{
                fontWeight: 600,
                color: "#92400e",
                display: "block",
                mb: 1,
              }}
            >
              Return Journey:
            </Typography>
            <Stepper orientation="vertical" sx={{ pl: 1 }}>
              {returnRoute.map((airport: string, idx: number) => {
                if (idx === returnRoute.length - 1) return null;
                const nextAirport = returnRoute[idx + 1];

                return (
                  <Step key={idx} active completed={false}>
                    <StepLabel
                      sx={{
                        "& .MuiStepLabel-label": {
                          fontSize: "0.8rem",
                          color: "#78350f",
                        },
                      }}
                    >
                      <Box
                        sx={{ display: "flex", alignItems: "center", gap: 1 }}
                      >
                        <Typography
                          variant="body2"
                          sx={{ fontSize: "0.8rem", fontWeight: 500 }}
                        >
                          {airport} → {nextAirport}
                        </Typography>
                        <Button
                          size="small"
                          variant="outlined"
                          endIcon={<OpenInNew sx={{ fontSize: 14 }} />}
                          onClick={() => {
                            const departureDate =
                              idx === 0
                                ? returnFlight.departure_time
                                : returnFlight.segments?.[idx]
                                    ?.departure_time ||
                                  returnFlight.departure_time;

                            window.open(
                              buildSkyscannerUrl(
                                airport,
                                nextAirport,
                                departureDate
                              ),
                              "_blank",
                              "noopener,noreferrer"
                            );
                          }}
                          sx={{
                            textTransform: "none",
                            fontSize: "0.7rem",
                            py: 0.25,
                            px: 1,
                            borderColor: "#f59e0b",
                            color: "#92400e",
                            "&:hover": {
                              borderColor: "#d97706",
                              bgcolor: "#fef3c740",
                            },
                          }}
                        >
                          Search
                        </Button>
                      </Box>
                    </StepLabel>
                  </Step>
                );
              })}
            </Stepper>
          </Box>
        )}

        <Alert severity="warning" sx={{ mt: 2, fontSize: "0.75rem" }}>
          <strong>Important:</strong> Book each leg separately and ensure
          sufficient layover time (minimum 2-3 hours recommended). You'll need
          to collect and recheck baggage between flights.
        </Alert>
      </Box>
    );
  };

  const renderFlight = (flight: any, index: number) => {
    const routeInfo = getRouteInfo(flight);
    const {
      isRoundtrip,
      outbound,
      returnFlight,
      returnRoute,
      isHubConnection,
      hubCities,
    } = routeInfo;

    const flightId = flight.id || flight.offer_id || `${index}`;
    const isExpanded = expandedFlight === flightId;
    const showGuide = showBookingGuide[flightId] || false;

    const totalPrice = isRoundtrip
      ? parseFloat(flight.pricing?.price_total || flight.total_price || 0)
      : parseFloat(outbound.pricing?.price_total || outbound.total_price || 0);

    const policyHighlights = getPolicyHighlights(flight);
    // const policyDetails = getFullPolicyDetails(flight);
    const showPolicies = expandedPolicies[flightId] || false;

    return (
      <Card
        key={flightId}
        sx={{
          mb: 2,
          border: "1px solid",
          borderColor: isHubConnection ? "#8b5cf6" : "grey.200",
          borderRadius: 3,
          overflow: "hidden",
          transition: "all 0.2s",
          "&:hover": {
            borderColor: isHubConnection ? "#7c3aed" : "primary.main",
            boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
          },
        }}
      >
        <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", md: "row" },
              gap: 3,
            }}
          >
            <Box sx={{ flex: 1 }}>
              <Box>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    mb: 2,
                  }}
                >
                  <Box sx={{ flex: 1 }}>
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 2,
                        mb: 1,
                        flexWrap: "wrap",
                      }}
                    >
                      <Typography
                        variant="h6"
                        sx={{
                          fontWeight: 600,
                          fontSize: { xs: "1rem", sm: "1.25rem" },
                        }}
                      >
                        {outbound.origin} → {outbound.destination}
                      </Typography>
                      {outbound.stops > 0 && (
                        <Chip
                          label={`${outbound.stops} stop${
                            outbound.stops > 1 ? "s" : ""
                          }`}
                          size="small"
                          sx={{ height: 20, fontSize: "0.75rem" }}
                        />
                      )}
                      {isHubConnection && hubCities.length > 0 && (
                        <Chip
                          label={`via ${hubCities.join(", ")}`}
                          size="small"
                          color="secondary"
                          variant="outlined"
                          icon={<ConnectingAirports sx={{ fontSize: 16 }} />}
                          sx={{ height: 22, fontSize: "0.7rem" }}
                        />
                      )}
                    </Box>
                    <Typography
                      variant="body2"
                      sx={{
                        color: "text.secondary",
                        fontSize: { xs: "0.8rem", sm: "0.875rem" },
                      }}
                    >
                      {formatDate(outbound.departure_time)} •{" "}
                      {formatTime(outbound.departure_time)} -{" "}
                      {formatTime(outbound.arrival_time)}
                    </Typography>
                    <Typography
                      variant="caption"
                      sx={{
                        color: "text.secondary",
                        fontSize: { xs: "0.7rem", sm: "0.75rem" },
                      }}
                    >
                      {formatDuration(outbound.duration_minutes)} •{" "}
                      {outbound.airline_code ||
                        outbound.segments?.[0]?.airline_name}
                    </Typography>

                    {isHubConnection && (
                      <Typography
                        variant="caption"
                        sx={{
                          display: "block",
                          mt: 0.5,
                          color: "#7c3aed",
                          fontSize: "0.75rem",
                          fontWeight: 500,
                        }}
                      >
                        ⚠️ Requires separate bookings for each flight segment
                      </Typography>
                    )}

                    <Box
                      sx={{
                        display: "flex",
                        gap: 1,
                        mt: 1.5,
                        flexWrap: "wrap",
                      }}
                    >
                      {policyHighlights.map((highlight, idx) => (
                        <Chip
                          key={idx}
                          label={
                            <Box
                              sx={{
                                display: "flex",
                                alignItems: "center",
                                gap: 0.5,
                              }}
                            >
                              <span style={{ fontSize: "0.75rem" }}>
                                {highlight.icon}
                              </span>
                              <span style={{ fontSize: "0.7rem" }}>
                                {highlight.text}
                              </span>
                            </Box>
                          }
                          size="small"
                          sx={{
                            height: 22,
                            bgcolor: `${highlight.color}15`,
                            color: highlight.color,
                            border: `1px solid ${highlight.color}40`,
                            "& .MuiChip-label": { px: 1, py: 0 },
                          }}
                        />
                      ))}
                      <Button
                        size="small"
                        onClick={() =>
                          setExpandedPolicies((prev) => ({
                            ...prev,
                            [flightId]: !prev[flightId],
                          }))
                        }
                        sx={{
                          textTransform: "none",
                          fontSize: "0.7rem",
                          minWidth: "auto",
                          p: 0.5,
                          color: "#2563eb",
                        }}
                      >
                        {showPolicies ? "Hide" : "View all"} policies
                      </Button>
                    </Box>
                  </Box>

                  <Box
                    sx={{
                      display: { xs: "block", md: "none" },
                      textAlign: "right",
                      ml: 2,
                    }}
                  >
                    <Typography
                      variant="h6"
                      sx={{
                        fontWeight: 700,
                        color: "primary.main",
                        fontSize: "1.25rem",
                      }}
                    >
                      ${totalPrice.toFixed(2)}
                    </Typography>
                    <Typography
                      variant="caption"
                      sx={{ color: "text.secondary", fontSize: "0.7rem" }}
                    >
                      {isRoundtrip ? "round-trip" : "one-way"}
                    </Typography>
                  </Box>
                </Box>

                {returnFlight && (
                  <Box
                    sx={{
                      pt: 2,
                      mt: 2,
                      borderTop: "1px dashed",
                      borderColor: "grey.300",
                    }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 2,
                        mb: 1,
                        flexWrap: "wrap",
                      }}
                    >
                      <Typography
                        variant="h6"
                        sx={{
                          fontWeight: 600,
                          fontSize: { xs: "1rem", sm: "1.25rem" },
                        }}
                      >
                        {returnFlight.origin} → {returnFlight.destination}
                      </Typography>
                      {returnFlight.stops > 0 && (
                        <Chip
                          label={`${returnFlight.stops} stop${
                            returnFlight.stops > 1 ? "s" : ""
                          }`}
                          size="small"
                          sx={{ height: 20, fontSize: "0.75rem" }}
                        />
                      )}
                      {isHubConnection &&
                        returnRoute &&
                        returnRoute.length > 2 && (
                          <Chip
                            label={`via ${returnRoute.slice(1, -1).join(", ")}`}
                            size="small"
                            color="secondary"
                            variant="outlined"
                            icon={<ConnectingAirports sx={{ fontSize: 16 }} />}
                            sx={{ height: 22, fontSize: "0.7rem" }}
                          />
                        )}
                    </Box>
                    <Typography
                      variant="body2"
                      sx={{
                        color: "text.secondary",
                        fontSize: { xs: "0.8rem", sm: "0.875rem" },
                      }}
                    >
                      {formatDate(returnFlight.departure_time)} •{" "}
                      {formatTime(returnFlight.departure_time)} -{" "}
                      {formatTime(returnFlight.arrival_time)}
                    </Typography>
                    <Typography
                      variant="caption"
                      sx={{
                        color: "text.secondary",
                        fontSize: { xs: "0.7rem", sm: "0.75rem" },
                      }}
                    >
                      {formatDuration(returnFlight.duration_minutes)} •{" "}
                      {returnFlight.airline_code ||
                        returnFlight.segments?.[0]?.airline_name}
                    </Typography>
                  </Box>
                )}

                {showPolicies && (
                  <Box
                    sx={{
                      mt: 3,
                      p: 2.5,
                      bgcolor: "#f8fafc",
                      borderRadius: 2,
                      border: "1px solid #e2e8f0",
                    }}
                  >
                    {/* ... rest of policy details same as before ... */}
                  </Box>
                )}

                {showGuide && renderBookingGuide(routeInfo)}

                {isExpanded && (
                  <Box
                    sx={{ mt: 3, p: 2, bgcolor: "grey.50", borderRadius: 2 }}
                  >
                    {outbound.segments && (
                      <Box sx={{ mb: returnFlight ? 3 : 0 }}>
                        <Typography
                          variant="subtitle2"
                          sx={{ mb: 2, fontWeight: 600 }}
                        >
                          Outbound Flight Details
                        </Typography>
                        {outbound.segments.map((seg: any, idx: number) => (
                          <Box
                            key={idx}
                            sx={{
                              mb: idx < outbound.segments.length - 1 ? 2 : 0,
                            }}
                          >
                            <Typography
                              variant="body2"
                              sx={{ fontWeight: 500 }}
                            >
                              {seg.airline_name} {seg.flight_number}
                            </Typography>
                            <Typography
                              variant="caption"
                              sx={{ color: "text.secondary", display: "block" }}
                            >
                              {seg.departure_iata} → {seg.arrival_iata} •{" "}
                              {seg.aircraft_name}
                            </Typography>
                          </Box>
                        ))}
                      </Box>
                    )}

                    {returnFlight?.segments && (
                      <Box
                        sx={{
                          pt: returnFlight ? 3 : 0,
                          borderTop: returnFlight ? "1px dashed" : "none",
                          borderColor: "grey.300",
                        }}
                      >
                        <Typography
                          variant="subtitle2"
                          sx={{ mb: 2, fontWeight: 600 }}
                        >
                          Return Flight Details
                        </Typography>
                        {returnFlight.segments.map((seg: any, idx: number) => (
                          <Box
                            key={idx}
                            sx={{
                              mb:
                                idx < returnFlight.segments.length - 1 ? 2 : 0,
                            }}
                          >
                            <Typography
                              variant="body2"
                              sx={{ fontWeight: 500 }}
                            >
                              {seg.airline_name} {seg.flight_number}
                            </Typography>
                            <Typography
                              variant="caption"
                              sx={{ color: "text.secondary", display: "block" }}
                            >
                              {seg.departure_iata} → {seg.arrival_iata} •{" "}
                              {seg.aircraft_name}
                            </Typography>
                          </Box>
                        ))}
                      </Box>
                    )}
                  </Box>
                )}

                <Box
                  sx={{
                    display: { xs: "flex", md: "none" },
                    flexDirection: "column",
                    gap: 1,
                    mt: 2,
                  }}
                >
                  {((outbound.segments && outbound.segments.length > 1) ||
                    (returnFlight?.segments &&
                      returnFlight.segments.length > 1)) && (
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() =>
                        setExpandedFlight(isExpanded ? null : flightId)
                      }
                      sx={{ textTransform: "none" }}
                      fullWidth
                    >
                      {isExpanded ? "Hide" : "Show"} Details
                    </Button>
                  )}

                  {isHubConnection ? (
                    <Button
                      variant="contained"
                      size="medium"
                      startIcon={<ConnectingAirports />}
                      onClick={() =>
                        setShowBookingGuide((prev) => ({
                          ...prev,
                          [flightId]: !prev[flightId],
                        }))
                      }
                      sx={{
                        textTransform: "none",
                        fontWeight: 600,
                        bgcolor: "#8b5cf6",
                        "&:hover": { bgcolor: "#7c3aed" },
                      }}
                      fullWidth
                    >
                      {showGuide ? "Hide" : "Show"} Booking Guide
                    </Button>
                  ) : (
                    <>
                      <Button
                        variant="contained"
                        size="medium"
                        endIcon={<OpenInNew />}
                        onClick={() => {
                          trackBookingClick(
                            flightId,
                            outbound.origin,
                            outbound.destination,
                            outbound.departure_time,
                            returnFlight?.departure_time || null,
                            totalPrice
                          );
                          window.open(
                            getGoogleFlightsUrl(flight),
                            "_blank",
                            "noopener,noreferrer"
                          );
                        }}
                        sx={{ textTransform: "none", fontWeight: 600 }}
                        fullWidth
                      >
                        Book on Google Flights
                        {results.google_flights_url && (
                          <Chip
                            label="✓"
                            size="small"
                            sx={{
                              height: 16,
                              fontSize: "0.6rem",
                              bgcolor: "#dcfce7",
                              color: "#166534",
                              ml: 0.5,
                              "& .MuiChip-label": { px: 0.5 },
                            }}
                          />
                        )}
                      </Button>
                      {/* <Button
                        variant="outlined"
                        size="small"
                        endIcon={<OpenInNew sx={{ fontSize: 14 }} />}
                        onClick={() => {
                          window.open(
                            buildKayakUrl(flight),
                            "_blank",
                            "noopener,noreferrer"
                          );
                        }}
                        sx={{
                          textTransform: "none",
                          fontSize: "0.8rem",
                          color: "#64748b",
                          borderColor: "#cbd5e1",
                          "&:hover": {
                            borderColor: "#94a3b8",
                            bgcolor: "#f8fafc",
                          },
                        }}
                        fullWidth
                      >
                        🔍 Compare on Kayak
                      </Button> */}
                    </>
                  )}
                </Box>

                {((outbound.segments && outbound.segments.length > 1) ||
                  (returnFlight?.segments &&
                    returnFlight.segments.length > 1)) && (
                  <Button
                    size="small"
                    onClick={() =>
                      setExpandedFlight(isExpanded ? null : flightId)
                    }
                    sx={{
                      mt: 2,
                      textTransform: "none",
                      display: { xs: "none", md: "inline-flex" },
                    }}
                  >
                    {isExpanded ? "Hide" : "Show"} Details
                  </Button>
                )}
              </Box>
            </Box>
            <Box
              sx={{
                display: { xs: "none", md: "flex" },
                flexDirection: "column",
                alignItems: "flex-end",
                justifyContent: "space-between",
                minWidth: 200,
              }}
            >
              <Box sx={{ textAlign: "right", mb: 2 }}>
                <Typography
                  variant="h5"
                  sx={{ fontWeight: 700, color: "primary.main" }}
                >
                  ${totalPrice.toFixed(2)}
                </Typography>
                <Typography variant="caption" sx={{ color: "text.secondary" }}>
                  {isRoundtrip ? "round-trip" : "one-way"}
                </Typography>
                {isHubConnection && (
                  <Typography
                    variant="caption"
                    sx={{
                      display: "block",
                      color: "#7c3aed",
                      fontWeight: 500,
                      mt: 0.5,
                    }}
                  >
                    Multi-city booking
                  </Typography>
                )}
              </Box>

              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 1,
                  width: "100%",
                }}
              >
                {isHubConnection ? (
                  <Button
                    variant="contained"
                    size="medium"
                    startIcon={<ConnectingAirports />}
                    onClick={() =>
                      setShowBookingGuide((prev) => ({
                        ...prev,
                        [flightId]: !prev[flightId],
                      }))
                    }
                    sx={{
                      textTransform: "none",
                      fontWeight: 600,
                      bgcolor: "#8b5cf6",
                      "&:hover": { bgcolor: "#7c3aed" },
                    }}
                  >
                    {showGuide ? "Hide" : "Show"} Booking Guide
                  </Button>
                ) : (
                  <>
                    <Button
                      variant="contained"
                      size="medium"
                      endIcon={<OpenInNew />}
                      onClick={() => {
                        trackBookingClick(
                          flightId,
                          outbound.origin,
                          outbound.destination,
                          outbound.departure_time,
                          returnFlight?.departure_time || null,
                          totalPrice
                        );
                        window.open(
                          getGoogleFlightsUrl(flight),
                          "_blank",
                          "noopener,noreferrer"
                        );
                      }}
                      sx={{ textTransform: "none", fontWeight: 600 }}
                    >
                      Book on Google Flights
                      {results.google_flights_url && (
                        <Chip
                          label="✓"
                          size="small"
                          sx={{
                            height: 16,
                            fontSize: "0.6rem",
                            bgcolor: "#dcfce7",
                            color: "#166534",
                            ml: 0.5,
                            "& .MuiChip-label": { px: 0.5 },
                          }}
                        />
                      )}
                    </Button>
                    {/* <Button
                      variant="outlined"
                      size="small"
                      endIcon={<OpenInNew sx={{ fontSize: 14 }} />}
                      onClick={() => {
                        window.open(
                          buildKayakUrl(flight),
                          "_blank",
                          "noopener,noreferrer"
                        );
                      }}
                      sx={{
                        textTransform: "none",
                        fontSize: "0.8rem",
                        color: "#64748b",
                        borderColor: "#cbd5e1",
                        "&:hover": {
                          borderColor: "#94a3b8",
                          bgcolor: "#f8fafc",
                        },
                      }}
                    >
                      🔍 Compare on Kayak
                    </Button> */}
                  </>
                )}
              </Box>
            </Box>
          </Box>
        </CardContent>
      </Card>
    );
  };

  return (
    <Box sx={{ maxWidth: 1100, mx: "auto", mt: 4 }}>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          gap: 2,
          mb: 3,
        }}
      >
        {/* First row: Title and New Search button */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            Your Flights
          </Typography>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={onNewSearch}
            sx={{ borderRadius: 2, textTransform: "none" }}
          >
            New Search
          </Button>
        </Box>

        {/* Second row: Compare button (full width available) */}
        {searchParams && (
          <Box sx={{ position: "relative", width: "fit-content" }}>
            <Button
              size="small"
              variant="outlined"
              onClick={() => setShowCompareMenu(!showCompareMenu)}
              sx={{
                textTransform: "none",
                fontSize: "0.75rem",
                py: 0.5,
                px: 1.5,
                borderColor: "#e2e8f0",
                color: "#64748b",
                "&:hover": {
                  borderColor: "#cbd5e1",
                  bgcolor: "#f8fafc",
                },
              }}
            >
              {compareLabel} {showCompareMenu ? "▲" : "▼"}
            </Button>
            {showCompareMenu && (
              <Card
                sx={{
                  position: "absolute",
                  top: "calc(100% + 4px)",
                  left: 0,
                  zIndex: 1000,
                  minWidth: 160,
                  boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                }}
              >
                <Box sx={{ p: 1 }}>
                  <Button
                    fullWidth
                    size="small"
                    variant="text"
                    endIcon={<OpenInNew sx={{ fontSize: 14 }} />}
                    onClick={() => {
                      window.open(
                        buildCompareUrl("skyscanner"),
                        "_blank",
                        "noopener,noreferrer"
                      );
                      setShowCompareMenu(false);
                    }}
                    sx={{
                      textTransform: "none",
                      justifyContent: "flex-start",
                      fontSize: "0.875rem",
                      px: 1.5,
                      py: 1,
                      color: "#475569",
                      "&:hover": {
                        bgcolor: "#f1f5f9",
                      },
                    }}
                  >
                    Skyscanner
                  </Button>
                  <Button
                    fullWidth
                    size="small"
                    variant="text"
                    endIcon={<OpenInNew sx={{ fontSize: 14 }} />}
                    onClick={() => {
                      window.open(
                        buildCompareUrl("kayak"),
                        "_blank",
                        "noopener,noreferrer"
                      );
                      setShowCompareMenu(false);
                    }}
                    sx={{
                      textTransform: "none",
                      justifyContent: "flex-start",
                      fontSize: "0.875rem",
                      px: 1.5,
                      py: 1,
                      color: "#475569",
                      "&:hover": {
                        bgcolor: "#f1f5f9",
                      },
                    }}
                  >
                    Kayak
                  </Button>
                </Box>
              </Card>
            )}
          </Box>
        )}
      </Box>

      {/* Price Alert Card - same as before */}
      <Card
        sx={{
          mb: 4,
          bgcolor: showPriceAlertExpanded ? "#f0f9ff" : "white",
          border: "1px solid",
          borderColor: showPriceAlertExpanded ? "#bfdbfe" : "#e5e7eb",
          cursor: showPriceAlertExpanded ? "default" : "pointer",
          transition: "all 0.3s ease",
          "&:hover": {
            borderColor: showPriceAlertExpanded ? "#bfdbfe" : "#2563eb",
            boxShadow: showPriceAlertExpanded
              ? "none"
              : "0 2px 8px rgba(37, 99, 235, 0.1)",
          },
        }}
        onClick={() => {
          if (!showPriceAlertExpanded && alertStatus !== "success") {
            setShowPriceAlertExpanded(true);
          }
        }}
      >
        <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
          {!showPriceAlertExpanded ? (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
              <NotificationsActive sx={{ color: "#2563eb", fontSize: 24 }} />
              <Typography
                variant="body1"
                sx={{ fontWeight: 500, color: "#1e293b" }}
              >
                Get notified when prices drop for this route
              </Typography>
              <Box sx={{ ml: "auto" }}>
                <Typography
                  variant="caption"
                  sx={{ color: "#64748b", fontStyle: "italic" }}
                >
                  Click to set up alert
                </Typography>
              </Box>
            </Box>
          ) : (
            <Box onClick={(e) => e.stopPropagation()}>
              <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
                <NotificationsActive
                  sx={{ color: "#2563eb", fontSize: 28, mt: 0.5 }}
                />
                <Box sx={{ flex: 1 }}>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "start",
                      mb: 2,
                    }}
                  >
                    <Box>
                      <Typography
                        variant="h6"
                        sx={{ fontWeight: 600, mb: 0.5 }}
                      >
                        Get Price Drop Alerts
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{ color: "text.secondary" }}
                      >
                        We'll notify you when prices drop for this route
                      </Typography>
                    </Box>
                    <Button
                      size="small"
                      onClick={() => {
                        setShowPriceAlertExpanded(false);
                        setAlertStatus("idle");
                        setAlertMessage("");
                      }}
                      sx={{ minWidth: "auto", p: 0.5 }}
                    >
                      <Close fontSize="small" />
                    </Button>
                  </Box>

                  {alertStatus === "success" ? (
                    <Alert severity="success" sx={{ mt: 1 }}>
                      {alertMessage}
                    </Alert>
                  ) : (
                    <Box
                      sx={{ display: "flex", gap: 1, alignItems: "flex-start" }}
                    >
                      <TextField
                        size="small"
                        placeholder="Enter your email"
                        value={alertEmail}
                        onChange={(e) => {
                          setAlertEmail(e.target.value);
                          if (alertStatus === "error") {
                            setAlertStatus("idle");
                            setAlertMessage("");
                          }
                        }}
                        error={alertStatus === "error"}
                        helperText={alertStatus === "error" ? alertMessage : ""}
                        disabled={alertStatus === "loading"}
                        sx={{ flex: 1, maxWidth: 300 }}
                        autoFocus
                      />
                      <Button
                        variant="contained"
                        onClick={createPriceAlert}
                        disabled={alertStatus === "loading" || !alertEmail}
                        sx={{ textTransform: "none", fontWeight: 600 }}
                      >
                        {alertStatus === "loading"
                          ? "Creating..."
                          : "Notify Me"}
                      </Button>
                    </Box>
                  )}
                </Box>
              </Box>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Flight Groups */}
      {/* Budget Airlines Alert */}
      {results.budget_airline_alternatives &&
        results.budget_airline_alternatives.length > 0 && (
          <Card
            sx={{
              mb: 4,
              bgcolor: "#fef3c7",
              border: "1px solid #fbbf24",
              borderRadius: 2,
            }}
          >
            <CardContent sx={{ p: 2.5 }}>
              <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
                <Box
                  sx={{
                    bgcolor: "#f59e0b",
                    borderRadius: "50%",
                    p: 1,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Flight sx={{ color: "white", fontSize: 20 }} />
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography
                    variant="h6"
                    sx={{ fontWeight: 600, mb: 1, color: "#92400e" }}
                  >
                    Don't miss budget airlines!
                  </Typography>
                  <Typography variant="body2" sx={{ color: "#78350f", mb: 2 }}>
                    These budget carriers often have cheaper fares but don't
                    appear in aggregators:
                  </Typography>
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5 }}>
                    {results.budget_airline_alternatives.map(
                      (airline: any, idx: number) => (
                        <Button
                          key={idx}
                          variant="outlined"
                          size="small"
                          endIcon={<OpenInNew sx={{ fontSize: 14 }} />}
                          onClick={() => {
                            window.open(
                              airline.check_url,
                              "_blank",
                              "noopener,noreferrer"
                            );
                          }}
                          sx={{
                            textTransform: "none",
                            borderColor: "#f59e0b",
                            color: "#92400e",
                            bgcolor: "white",
                            "&:hover": {
                              borderColor: "#d97706",
                              bgcolor: "#fef3c750",
                            },
                            fontSize: "0.875rem",
                            fontWeight: 500,
                          }}
                        >
                          {airline.airline}
                        </Button>
                      )
                    )}
                  </Box>
                  <Typography
                    variant="caption"
                    sx={{
                      display: "block",
                      mt: 1.5,
                      color: "#78350f",
                      fontStyle: "italic",
                    }}
                  >
                    Tip: Budget airlines can be 30-50% cheaper but may charge
                    extra for bags
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        )}

      {availableGroups.map(({ groupKey, flights }, groupIndex) => {
        const config = groupConfig[groupKey as keyof typeof groupConfig];
        if (!config) return null;
        const Icon = config.icon;

        return (
          <Box key={groupKey} sx={{ mb: 5 }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 2,
                mb: 3,
                pb: 2,
                borderBottom: "2px solid",
                borderColor: groupIndex === 0 ? "primary.main" : "grey.200",
              }}
            >
              <Box
                sx={{
                  width: 40,
                  height: 40,
                  borderRadius: 2,
                  bgcolor: groupIndex === 0 ? "primary.main" : "grey.100",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Icon
                  sx={{
                    color: groupIndex === 0 ? "white" : "grey.600",
                    fontSize: 22,
                  }}
                />
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="h5" sx={{ fontWeight: 600, mb: 0.5 }}>
                  {config.title}
                </Typography>
                <Typography variant="body2" sx={{ color: "text.secondary" }}>
                  {config.description}
                </Typography>
              </Box>
              {groupIndex === 0 && (
                <Chip
                  label="Best Value"
                  color="primary"
                  size="small"
                  sx={{ fontWeight: 600 }}
                />
              )}
            </Box>
            {flights.map((flight: any, index: number) =>
              renderFlight(flight, index)
            )}
          </Box>
        );
      })}
    </Box>
  );
};
