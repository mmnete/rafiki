import React, { useState } from 'react';
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
  CircularProgress,
  Fade
} from '@mui/material';
import {
  FlightTakeoff,
  FlightLand,
  Person,
  BusinessCenter,
  Search as SearchIcon,
  AirlineSeatReclineNormal,
  ChildCare
} from '@mui/icons-material';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { LocalizationProvider, DatePicker } from '@mui/x-date-pickers';
import { SearchRequest } from '../types/flight';

interface SearchFormProps {
  onSearch: (searchData: SearchRequest) => void;
  loading: boolean;
}

export const SearchForm: React.FC<SearchFormProps> = ({ onSearch, loading }) => {
  const [formData, setFormData] = useState<SearchRequest>({
    origin: '',
    destination: '',
    departure_date: '',
    passengers: {
      adults: 1,
      children: 0,
      infants: 0
    },
    travel_class: 'economy'
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Submitting form data:', formData);
    onSearch(formData);
  };

  const formatDate = (date: Date | null): string => {
    if (!date) return '';
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const handleChange = (field: string, value: any) => {
    if (field === 'departure_date' || field === 'return_date') {
      // Handle date fields
      const formattedDate = value ? formatDate(value) : '';
      setFormData(prev => ({
        ...prev,
        [field]: formattedDate
      }));
    } else if (field.includes('.')) {
      // Handle nested fields (passengers)
      const [parent, child] = field.split('.');
      setFormData(prev => ({
        ...prev,
        [parent]: {
          ...prev[parent as keyof SearchRequest],
          [child]: Number(value)
        }
      }));
    } else {
      // Handle other fields
      setFormData(prev => ({
        ...prev,
        [field]: value
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
              bgcolor: 'white',
              transition: 'transform 0.3s ease-in-out',
              '&:hover': {
                transform: 'scale(1.01)',
              }
            }}
          >
            <Typography variant="h4" gutterBottom sx={{ color: '#1976d2', fontWeight: 500, mb: 4 }}>
              Find Your Flight
            </Typography>
            <Box component="form" onSubmit={handleSubmit}>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <TextField
                    required
                    fullWidth
                    label="From"
                    value={formData.origin}
                    onChange={(e) => handleChange('origin', e.target.value)}
                    placeholder="SFO"
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">
                          <FlightTakeoff color="primary" />
                        </InputAdornment>
                      ),
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    required
                    fullWidth
                    label="To"
                    value={formData.destination}
                    onChange={(e) => handleChange('destination', e.target.value)}
                    placeholder="JFK"
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">
                          <FlightLand color="primary" />
                        </InputAdornment>
                      ),
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <DatePicker
                    label="Departure Date"
                    value={formData.departure_date ? new Date(formData.departure_date) : null}
                    onChange={(date) => handleChange('departure_date', date)}
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
                    value={formData.return_date ? new Date(formData.return_date) : null}
                    onChange={(date) => handleChange('return_date', date)}
                    slotProps={{
                      textField: {
                        fullWidth: true,
                      },
                    }}
                    disablePast
                    minDate={formData.departure_date ? new Date(formData.departure_date) : undefined}
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField
                    required
                    fullWidth
                    type="number"
                    label="Adults"
                    value={formData.passengers.adults}
                    onChange={(e) => handleChange('passengers.adults', parseInt(e.target.value))}
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">
                          <Person color="primary" />
                        </InputAdornment>
                      ),
                      inputProps: { min: 1, max: 9 }
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Children (2-11)"
                    value={formData.passengers.children}
                    onChange={(e) => handleChange('passengers.children', parseInt(e.target.value))}
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">
                          <AirlineSeatReclineNormal color="primary" />
                        </InputAdornment>
                      ),
                      inputProps: { min: 0, max: 9 }
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Infants (Under 2)"
                    value={formData.passengers.infants}
                    onChange={(e) => handleChange('passengers.infants', parseInt(e.target.value))}
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">
                          <ChildCare color="primary" />
                        </InputAdornment>
                      ),
                      inputProps: { min: 0, max: 9 }
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
                    onChange={(e) => handleChange('travel_class', e.target.value)}
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
              <Box sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  disabled={loading}
                  sx={{
                    minWidth: 200,
                    height: 48,
                    borderRadius: 24,
                    textTransform: 'none',
                    fontSize: '1.1rem',
                  }}
                  startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SearchIcon />}
                >
                  {loading ? 'Searching...' : 'Search Flights'}
                </Button>
              </Box>
            </Box>
          </Paper>
        </Fade>
      </Container>
    </LocalizationProvider>
  );
};