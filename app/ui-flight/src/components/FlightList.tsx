import React from 'react';
import { Box, Card, CardContent, Chip, Grid as MuiGrid, Typography } from '@mui/material';
import { Flight } from '../types/flight';
import FlightTakeoffIcon from '@mui/icons-material/FlightTakeoff';
import WifiIcon from '@mui/icons-material/Wifi';
import PowerIcon from '@mui/icons-material/Power';
import RestaurantIcon from '@mui/icons-material/Restaurant';
import TheatersIcon from '@mui/icons-material/Theaters';

interface FlightListProps {
  flights: Flight[];
}

export const FlightList: React.FC<FlightListProps> = ({ flights }) => {
  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h5" gutterBottom sx={{ mb: 3, color: '#1976d2', fontWeight: 500 }}>
        Available Flights ({flights.length})
      </Typography>
      {flights.map((flight) => (
        <Card 
          key={`${flight.departure.airport}-${flight.arrival.airport}-${flight.departure.time}`} 
          sx={{ 
            mb: 3,
            borderRadius: 2,
            transition: 'all 0.3s ease-in-out',
            '&:hover': {
              transform: 'translateY(-2px)',
              boxShadow: 6,
            }
          }}
        >
          <CardContent sx={{ p: 3 }}>
            <MuiGrid container spacing={3}>
              <MuiGrid item xs={12}>
                <Box sx={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  mb: 2 
                }}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <FlightTakeoffIcon sx={{ mr: 1, color: 'primary.main' }} />
                    <Typography variant="h6" sx={{ fontWeight: 500 }}>
                      {flight.airline.name} ({flight.airline.code})
                    </Typography>
                  </Box>
                  <Box sx={{ textAlign: 'right' }}>
                    <Typography variant="h5" color="primary" sx={{ fontWeight: 'bold' }}>
                      ${flight.price.total}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Total Price
                    </Typography>
                  </Box>
                </Box>
              </MuiGrid>

              <MuiGrid item xs={12}>
                <Box sx={{ 
                  p: 2, 
                  bgcolor: 'grey.50', 
                  borderRadius: 2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body1" sx={{ fontWeight: 500 }}>
                      {flight.departure.airport}
                      <Typography component="span" color="text.secondary">
                        {flight.departure.terminal && ` (Terminal ${flight.departure.terminal})`}
                      </Typography>
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {flight.departure.formatted}
                    </Typography>
                  </Box>
                  
                  <Box sx={{ 
                    flex: 1, 
                    textAlign: 'center',
                    borderLeft: '1px dashed',
                    borderRight: '1px dashed',
                    borderColor: 'grey.300',
                    px: 2
                  }}>
                    <Typography variant="caption" color="text.secondary">
                      {flight.duration.formatted}
                    </Typography>
                    <Box sx={{ 
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      my: 0.5
                    }}>
                      <Box sx={{ 
                        flex: 1, 
                        height: 1, 
                        borderBottom: '2px dashed',
                        borderColor: 'primary.main'
                      }} />
                      <FlightTakeoffIcon 
                        sx={{ 
                          mx: 1, 
                          color: 'primary.main',
                          transform: 'rotate(45deg)'
                        }} 
                      />
                      <Box sx={{ 
                        flex: 1, 
                        height: 1, 
                        borderBottom: '2px dashed',
                        borderColor: 'primary.main'
                      }} />
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {flight.stops} {flight.stops === 1 ? 'stop' : 'stops'}
                    </Typography>
                  </Box>

                  <Box sx={{ flex: 1, textAlign: 'right' }}>
                    <Typography variant="body1" sx={{ fontWeight: 500 }}>
                      {flight.arrival.airport}
                      <Typography component="span" color="text.secondary">
                        {flight.arrival.terminal && ` (Terminal ${flight.arrival.terminal})`}
                      </Typography>
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {flight.arrival.formatted}
                    </Typography>
                  </Box>
                </Box>
              </MuiGrid>

              <MuiGrid item xs={12}>
                <Box sx={{ 
                  display: 'flex', 
                  flexWrap: 'wrap',
                  gap: 1,
                  mb: 2
                }}>
                  {[
                    { icon: WifiIcon, label: 'WiFi', enabled: flight.amenities.wifi },
                    { icon: PowerIcon, label: 'Power', enabled: flight.amenities.power },
                    { icon: TheatersIcon, label: 'Entertainment', enabled: flight.amenities.entertainment },
                    { icon: RestaurantIcon, label: 'Meal', enabled: flight.amenities.meal }
                  ].map(({ icon: Icon, label, enabled }) => (
                    <Chip
                      key={label}
                      icon={<Icon />}
                      label={label}
                      variant={enabled ? 'filled' : 'outlined'}
                      color={enabled ? 'primary' : 'default'}
                      size="small"
                      sx={{ opacity: enabled ? 1 : 0.5 }}
                    />
                  ))}
                </Box>

                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                  <Chip 
                    label={`${flight.cabin_class} - ${flight.fare_class}`}
                    color="primary"
                    variant="outlined"
                  />
                  <Chip
                    label={`Carry-on ${flight.baggage.carry_on.included ? 'Included' : '$' + flight.baggage.carry_on.fee}`}
                    color={flight.baggage.carry_on.included ? 'success' : 'default'}
                    variant="outlined"
                  />
                  <Chip
                    label={`Checked bag ${flight.baggage.checked.included ? 'Included' : '$' + flight.baggage.checked.fee}`}
                    color={flight.baggage.checked.included ? 'success' : 'default'}
                    variant="outlined"
                  />
                  {flight.refundable && (
                    <Chip label="Refundable" color="success" variant="outlined" />
                  )}
                  {flight.changeable && (
                    <Chip label="Changeable" color="info" variant="outlined" />
                  )}
                </Box>
              </MuiGrid>

              {flight.segments.length > 1 && (
                <MuiGrid item xs={12}>
                  <Box sx={{ 
                    mt: 2,
                    p: 2,
                    bgcolor: 'grey.50',
                    borderRadius: 2
                  }}>
                    <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
                      Flight Segments
                    </Typography>
                    {flight.segments.map((segment, index) => (
                      <Box 
                        key={index}
                        sx={{
                          display: 'flex',
                          alignItems: 'center',
                          mb: index < flight.segments.length - 1 ? 1 : 0,
                          gap: 1
                        }}
                      >
                        <FlightTakeoffIcon 
                          sx={{ 
                            color: 'primary.main',
                            fontSize: '1rem'
                          }} 
                        />
                        <Typography variant="body2">
                          {segment.flight_number}: {segment.from} → {segment.to}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          ({new Date(segment.departure).toLocaleTimeString()} - {new Date(segment.arrival).toLocaleTimeString()})
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </MuiGrid>
              )}
            </MuiGrid>
          </CardContent>
        </Card>
      ))}
    </Box>
  );
};