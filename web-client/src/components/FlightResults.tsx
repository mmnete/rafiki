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
import { useState } from "react";

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
    title: 'Standard Routes',
    icon: Flight,
    color: '#10b981',
    description: 'Direct routing between airports'
  },
  nearby_airport_options: {
    title: 'Nearby Airports',
    icon: LocationCity,
    color: '#3b82f6',
    description: 'Alternative airports nearby'
  },
  hub_connections: {
    title: 'Hub Connections',
    icon: Hub,
    color: '#8b5cf6',
    description: 'Popular connecting routes'
  }
};

export const FlightResults: React.FC<FlightResultsProps> = ({
  results,
  onNewSearch,
  searchParams,
}) => {
  const [expandedFlight, setExpandedFlight] = useState<string | null>(null);
  const [showPriceAlertExpanded, setShowPriceAlertExpanded] = useState(false);
  const [alertEmail, setAlertEmail] = useState("");
  const [alertStatus, setAlertStatus] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle");
  const [alertMessage, setAlertMessage] = useState("");
  const [expandedPolicies, setExpandedPolicies] = useState<{
    [key: string]: boolean;
  }>({});

  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

  // Load saved email from localStorage on mount
  useState(() => {
    const savedEmail = localStorage.getItem("priceAlertEmail");
    if (savedEmail) {
      setAlertEmail(savedEmail);
    }
  });

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

  const getFullPolicyDetails = (flight: any) => {
    const outbound = flight.outbound_flight || flight;

    return {
      baggage: {
        carryOn: outbound.baggage?.carry_on_included
          ? "Included"
          : "Not included (fee applies)",
        checked:
          outbound.baggage?.checked_bags_included > 0
            ? `${outbound.baggage.checked_bags_included} bag(s) included`
            : "Not included (fee applies)",
        policy: outbound.baggage_policy?.all_fares || null,
      },
      cancellation: {
        refundable: outbound.fare_details?.refundable || false,
        policy: outbound.cancellation_policy?.all_fares || "Non-refundable",
        changeable: outbound.fare_details?.changeable || false,
      },
      seats: {
        selectionAvailable:
          outbound.ancillary_services?.seat_selection_available || false,
        feeRange: outbound.ancillary_services?.seat_selection_fee_range || null,
        types: outbound.ancillary_services?.seat_types_available || [],
      },
      meals: {
        included: outbound.segments?.[0]?.meal_service || "Not specified",
        options: outbound.segments?.[0]?.meal_options || [],
        upgradeAvailable:
          outbound.ancillary_services?.meal_upgrade_available || false,
      },
      extras: {
        wifi: outbound.ancillary_services?.wifi_cost,
        loungeAccess: outbound.ancillary_services?.lounge_access || false,
        priorityBoarding:
          outbound.ancillary_services?.priority_boarding_available || false,
      },
      fareClass: outbound.fare_details?.fare_class || "Economy",
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

  const renderFlight = (flight: any, index: number) => {
    const isRoundtrip = flight.outbound_flight && flight.return_flight;
    const outbound = isRoundtrip ? flight.outbound_flight : flight;
    const returnFlight = isRoundtrip ? flight.return_flight : null;

    const flightId = flight.id || flight.offer_id || `${index}`;
    const isExpanded = expandedFlight === flightId;

    const totalPrice = isRoundtrip
      ? parseFloat(flight.pricing?.price_total || flight.total_price || 0)
      : parseFloat(outbound.pricing?.price_total || outbound.total_price || 0);

    const isHubConnection =
      flight.is_hub_roundtrip || outbound.is_hub_connection;
    const hubAirport = isHubConnection
      ? outbound.hub_airport || flight.routing_used?.[1]
      : null;

    const policyHighlights = getPolicyHighlights(flight);
    const policyDetails = getFullPolicyDetails(flight);
    const showPolicies = expandedPolicies[flightId] || false;

    return (
      <Card
        key={flightId}
        sx={{
          mb: 2,
          border: "1px solid",
          borderColor: "grey.200",
          borderRadius: 3,
          overflow: "hidden",
          transition: "all 0.2s",
          "&:hover": {
            borderColor: "primary.main",
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
                      {hubAirport && (
                        <Chip
                          label={`via ${hubAirport}`}
                          size="small"
                          color="primary"
                          variant="outlined"
                          sx={{ height: 20, fontSize: "0.7rem" }}
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
                    <Typography
                      variant="subtitle2"
                      sx={{ fontWeight: 600, mb: 2, color: "#1e293b" }}
                    >
                      Flight Policies & Amenities
                    </Typography>

                    <Box
                      sx={{
                        display: "grid",
                        gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                        gap: 2,
                      }}
                    >
                      <Box>
                        <Typography
                          variant="caption"
                          sx={{
                            fontWeight: 600,
                            color: "#64748b",
                            textTransform: "uppercase",
                            fontSize: "0.65rem",
                          }}
                        >
                          Baggage
                        </Typography>
                        <Box sx={{ mt: 0.5 }}>
                          <Typography
                            variant="body2"
                            sx={{ fontSize: "0.8rem", mb: 0.5 }}
                          >
                            <span
                              style={{
                                color: policyDetails.baggage.carryOn.includes(
                                  "Included"
                                )
                                  ? "#10b981"
                                  : "#ef4444",
                              }}
                            >
                              {policyDetails.baggage.carryOn.includes(
                                "Included"
                              )
                                ? "✓"
                                : "✗"}
                            </span>{" "}
                            Carry-on: {policyDetails.baggage.carryOn}
                          </Typography>
                          <Typography
                            variant="body2"
                            sx={{ fontSize: "0.8rem" }}
                          >
                            <span
                              style={{
                                color: policyDetails.baggage.checked.includes(
                                  "included"
                                )
                                  ? "#10b981"
                                  : "#ef4444",
                              }}
                            >
                              {policyDetails.baggage.checked.includes(
                                "included"
                              )
                                ? "✓"
                                : "✗"}
                            </span>{" "}
                            Checked: {policyDetails.baggage.checked}
                          </Typography>
                          {policyDetails.baggage.policy && (
                            <Typography
                              variant="caption"
                              sx={{
                                color: "#64748b",
                                fontSize: "0.7rem",
                                display: "block",
                                mt: 0.5,
                              }}
                            >
                              Fees: $
                              {policyDetails.baggage.policy.checked_1 || "N/A"}{" "}
                              (1st bag), $
                              {policyDetails.baggage.policy.checked_2 || "N/A"}{" "}
                              (2nd bag)
                            </Typography>
                          )}
                        </Box>
                      </Box>

                      <Box>
                        <Typography
                          variant="caption"
                          sx={{
                            fontWeight: 600,
                            color: "#64748b",
                            textTransform: "uppercase",
                            fontSize: "0.65rem",
                          }}
                        >
                          Cancellation & Changes
                        </Typography>
                        <Box sx={{ mt: 0.5 }}>
                          <Typography
                            variant="body2"
                            sx={{ fontSize: "0.8rem", mb: 0.5 }}
                          >
                            <span
                              style={{
                                color: policyDetails.cancellation.refundable
                                  ? "#10b981"
                                  : "#ef4444",
                              }}
                            >
                              {policyDetails.cancellation.refundable
                                ? "✓"
                                : "✗"}
                            </span>{" "}
                            {policyDetails.cancellation.refundable
                              ? "Refundable"
                              : "Non-refundable"}
                          </Typography>
                          <Typography
                            variant="body2"
                            sx={{ fontSize: "0.8rem" }}
                          >
                            <span
                              style={{
                                color: policyDetails.cancellation.changeable
                                  ? "#10b981"
                                  : "#ef4444",
                              }}
                            >
                              {policyDetails.cancellation.changeable
                                ? "✓"
                                : "✗"}
                            </span>{" "}
                            {policyDetails.cancellation.changeable
                              ? "Changes allowed"
                              : "No changes"}
                          </Typography>
                          {typeof policyDetails.cancellation.policy ===
                            "string" &&
                            policyDetails.cancellation.policy.includes(
                              "24h"
                            ) && (
                              <Typography
                                variant="caption"
                                sx={{
                                  color: "#f59e0b",
                                  fontSize: "0.7rem",
                                  display: "block",
                                  mt: 0.5,
                                }}
                              >
                                ⓘ Free cancellation within 24 hours
                              </Typography>
                            )}
                        </Box>
                      </Box>

                      <Box>
                        <Typography
                          variant="caption"
                          sx={{
                            fontWeight: 600,
                            color: "#64748b",
                            textTransform: "uppercase",
                            fontSize: "0.65rem",
                          }}
                        >
                          Seat Selection
                        </Typography>
                        <Box sx={{ mt: 0.5 }}>
                          <Typography
                            variant="body2"
                            sx={{ fontSize: "0.8rem", mb: 0.5 }}
                          >
                            <span
                              style={{
                                color: policyDetails.seats.selectionAvailable
                                  ? "#10b981"
                                  : "#ef4444",
                              }}
                            >
                              {policyDetails.seats.selectionAvailable
                                ? "✓"
                                : "✗"}
                            </span>{" "}
                            {policyDetails.seats.selectionAvailable
                              ? "Available"
                              : "Not available"}
                          </Typography>
                          {policyDetails.seats.types.length > 0 && (
                            <Typography
                              variant="caption"
                              sx={{
                                color: "#64748b",
                                fontSize: "0.7rem",
                                display: "block",
                              }}
                            >
                              Options: {policyDetails.seats.types.join(", ")}
                            </Typography>
                          )}
                        </Box>
                      </Box>

                      <Box>
                        <Typography
                          variant="caption"
                          sx={{
                            fontWeight: 600,
                            color: "#64748b",
                            textTransform: "uppercase",
                            fontSize: "0.65rem",
                          }}
                        >
                          Meals & Snacks
                        </Typography>
                        <Box sx={{ mt: 0.5 }}>
                          {policyDetails.meals.options.length > 0 ? (
                            <Typography
                              variant="body2"
                              sx={{ fontSize: "0.8rem", color: "#10b981" }}
                            >
                              ✓ {policyDetails.meals.options.join(", ")}
                            </Typography>
                          ) : (
                            <Typography
                              variant="body2"
                              sx={{ fontSize: "0.8rem", color: "#64748b" }}
                            >
                              {policyDetails.meals.included !== "Not specified"
                                ? policyDetails.meals.included
                                : "Not included"}
                            </Typography>
                          )}
                          {policyDetails.meals.upgradeAvailable && (
                            <Typography
                              variant="caption"
                              sx={{
                                color: "#64748b",
                                fontSize: "0.7rem",
                                display: "block",
                                mt: 0.5,
                              }}
                            >
                              ⓘ Meal upgrades available
                            </Typography>
                          )}
                        </Box>
                      </Box>

                      <Box sx={{ gridColumn: { xs: "1", sm: "1 / -1" } }}>
                        <Typography
                          variant="caption"
                          sx={{
                            fontWeight: 600,
                            color: "#64748b",
                            textTransform: "uppercase",
                            fontSize: "0.65rem",
                          }}
                        >
                          Additional Amenities
                        </Typography>
                        <Box
                          sx={{
                            mt: 0.5,
                            display: "flex",
                            gap: 2,
                            flexWrap: "wrap",
                          }}
                        >
                          {policyDetails.extras.wifi !== null && (
                            <Typography
                              variant="body2"
                              sx={{ fontSize: "0.8rem" }}
                            >
                              📶 WiFi:{" "}
                              {policyDetails.extras.wifi === 0
                                ? "Free"
                                : `$${policyDetails.extras.wifi}`}
                            </Typography>
                          )}
                          {policyDetails.extras.priorityBoarding && (
                            <Typography
                              variant="body2"
                              sx={{ fontSize: "0.8rem" }}
                            >
                              🎫 Priority boarding available
                            </Typography>
                          )}
                          {policyDetails.extras.loungeAccess && (
                            <Typography
                              variant="body2"
                              sx={{ fontSize: "0.8rem" }}
                            >
                              ✨ Lounge access included
                            </Typography>
                          )}
                          <Typography
                            variant="body2"
                            sx={{ fontSize: "0.8rem", color: "#64748b" }}
                          >
                            Fare: {policyDetails.fareClass}
                          </Typography>
                        </Box>
                      </Box>
                    </Box>
                  </Box>
                )}

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
                    <>
                      <Button
                        variant="contained"
                        size="medium"
                        endIcon={<OpenInNew sx={{ fontSize: 16 }} />}
                        onClick={() => {
                          trackBookingClick(
                            flightId,
                            outbound.origin,
                            outbound.destination,
                            outbound.departure_time,
                            null,
                            parseFloat(
                              outbound.pricing?.price_total ||
                                outbound.total_price ||
                                0
                            )
                          );
                          window.open(
                            buildSkyscannerUrl(
                              outbound.origin,
                              outbound.destination,
                              outbound.departure_time
                            ),
                            "_blank",
                            "noopener,noreferrer"
                          );
                        }}
                        sx={{ textTransform: "none" }}
                        fullWidth
                      >
                        Book Outbound
                      </Button>
                      {returnFlight && (
                        <Button
                          variant="contained"
                          size="medium"
                          endIcon={<OpenInNew sx={{ fontSize: 16 }} />}
                          onClick={() => {
                            trackBookingClick(
                              flightId,
                              returnFlight.origin,
                              returnFlight.destination,
                              returnFlight.departure_time,
                              null,
                              parseFloat(
                                returnFlight.pricing?.price_total ||
                                  returnFlight.total_price ||
                                  0
                              )
                            );
                            window.open(
                              buildSkyscannerUrl(
                                returnFlight.origin,
                                returnFlight.destination,
                                returnFlight.departure_time
                              ),
                              "_blank",
                              "noopener,noreferrer"
                            );
                          }}
                          sx={{ textTransform: "none" }}
                          fullWidth
                        >
                          Book Return
                        </Button>
                      )}
                    </>
                  ) : (
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
                          buildSkyscannerUrl(
                            outbound.origin,
                            outbound.destination,
                            outbound.departure_time,
                            returnFlight?.departure_time
                          ),
                          "_blank",
                          "noopener,noreferrer"
                        );
                      }}
                      sx={{ textTransform: "none", fontWeight: 600 }}
                      fullWidth
                    >
                      Book on Skyscanner
                    </Button>
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
                minWidth: 180,
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
                  <>
                    <Button
                      variant="contained"
                      size="small"
                      endIcon={<OpenInNew sx={{ fontSize: 16 }} />}
                      onClick={() => {
                        trackBookingClick(
                          flightId,
                          outbound.origin,
                          outbound.destination,
                          outbound.departure_time,
                          null,
                          parseFloat(
                            outbound.pricing?.price_total ||
                              outbound.total_price ||
                              0
                          )
                        );
                        window.open(
                          buildSkyscannerUrl(
                            outbound.origin,
                            outbound.destination,
                            outbound.departure_time
                          ),
                          "_blank",
                          "noopener,noreferrer"
                        );
                      }}
                      sx={{
                        textTransform: "none",
                        fontSize: "0.75rem",
                        py: 0.5,
                      }}
                    >
                      Book Outbound
                    </Button>
                    {returnFlight && (
                      <Button
                        variant="contained"
                        size="small"
                        endIcon={<OpenInNew sx={{ fontSize: 16 }} />}
                        onClick={() => {
                          trackBookingClick(
                            flightId,
                            returnFlight.origin,
                            returnFlight.destination,
                            returnFlight.departure_time,
                            null,
                            parseFloat(
                              returnFlight.pricing?.price_total ||
                                returnFlight.total_price ||
                                0
                            )
                          );
                          window.open(
                            buildSkyscannerUrl(
                              returnFlight.origin,
                              returnFlight.destination,
                              returnFlight.departure_time
                            ),
                            "_blank",
                            "noopener,noreferrer"
                          );
                        }}
                        sx={{
                          textTransform: "none",
                          fontSize: "0.75rem",
                          py: 0.5,
                        }}
                      >
                        Book Return
                      </Button>
                    )}
                  </>
                ) : (
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
                        buildSkyscannerUrl(
                          outbound.origin,
                          outbound.destination,
                          outbound.departure_time,
                          returnFlight?.departure_time
                        ),
                        "_blank",
                        "noopener,noreferrer"
                      );
                    }}
                    sx={{ textTransform: "none", fontWeight: 600 }}
                  >
                    Book on Skyscanner
                  </Button>
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
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Your Flights
          </Typography>
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            {results.search_summary?.total_flights_found} options found
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={onNewSearch}
          sx={{ borderRadius: 2, textTransform: "none" }}
        >
          New Search
        </Button>
      </Box>
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
