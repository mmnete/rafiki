// components/LoadingDisplay.tsx
import { Box, Paper, Typography, LinearProgress } from '@mui/material';
import {
  Psychology,
  Search,
  Route,
  CompareArrows,
  CheckCircle
} from '@mui/icons-material';

interface LoadingDisplayProps {
  progress: number;
  message: string;
  currentStep: string;
  resultsFound: number;
}

const stepIcons: { [key: string]: any } = {
  init: Psychology,
  searching: Search,
  routes: Route,
  comparing: CompareArrows,
  finalizing: CheckCircle,
};

export const LoadingDisplay: React.FC<LoadingDisplayProps> = ({
  progress,
  message,
  currentStep,
  resultsFound
}) => {
  const StepIcon = stepIcons[currentStep] || Psychology;

  return (
    <Box sx={{ 
      maxWidth: 700, 
      mx: 'auto',
      mt: 8
    }}>
      <Paper
        elevation={0}
        sx={{
          p: 5,
          borderRadius: 4,
          bgcolor: 'white',
          border: '1px solid',
          borderColor: 'grey.200',
          textAlign: 'center'
        }}
      >
        {/* Animated Icon */}
        <Box
          sx={{
            mb: 4,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center'
          }}
        >
          <Box
            sx={{
              width: 80,
              height: 80,
              borderRadius: '50%',
              bgcolor: '#dbeafe',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
              '@keyframes pulse': {
                '0%, 100%': {
                  opacity: 1,
                  transform: 'scale(1)',
                },
                '50%': {
                  opacity: 0.8,
                  transform: 'scale(1.05)',
                },
              },
            }}
          >
            <StepIcon 
              sx={{ 
                fontSize: 40,
                color: 'primary.main',
                animation: currentStep === 'searching' ? 'rotate 3s linear infinite' : 'none',
                '@keyframes rotate': {
                  '0%': {
                    transform: 'rotate(0deg)',
                  },
                  '100%': {
                    transform: 'rotate(360deg)',
                  },
                },
              }} 
            />
          </Box>
        </Box>

        {/* Main Message */}
        <Typography 
          variant="h5" 
          sx={{ 
            fontWeight: 600,
            color: 'grey.900',
            mb: 2
          }}
        >
          {message}
        </Typography>

        {/* Results Counter */}
        {resultsFound > 0 && (
          <Typography 
            variant="body1" 
            sx={{ 
              color: 'text.secondary',
              mb: 3,
              fontWeight: 500
            }}
          >
            Found {resultsFound} options so far...
          </Typography>
        )}

        {/* Progress Bar */}
        <Box sx={{ mb: 2 }}>
          <LinearProgress 
            variant="determinate" 
            value={progress}
            sx={{
              height: 8,
              borderRadius: 4,
              bgcolor: 'grey.200',
              '& .MuiLinearProgress-bar': {
                borderRadius: 4,
                background: 'linear-gradient(90deg, #2563eb 0%, #3b82f6 100%)',
              }
            }}
          />
        </Box>
        
        <Typography 
          variant="body2" 
          sx={{ 
            color: 'text.secondary',
            fontWeight: 500
          }}
        >
          {progress}% complete
        </Typography>

        {/* Status Messages */}
        <Box
          sx={{
            mt: 4,
            p: 3,
            borderRadius: 2,
            bgcolor: 'grey.50',
            border: '1px solid',
            borderColor: 'grey.200'
          }}
        >
          <Typography 
            variant="body2"
            sx={{ 
              color: 'text.secondary',
              lineHeight: 1.8,
            }}
          >
            {currentStep === 'init' && '🚀 Initializing AI search agent...'}
            {currentStep === 'searching' && '🔍 Searching through 120+ flight databases...'}
            {currentStep === 'routes' && '🗺️ Exploring alternative routes and connections...'}
            {currentStep === 'comparing' && '⚖️ Comparing prices, schedules, and amenities...'}
            {currentStep === 'finalizing' && '✨ Preparing your personalized results...'}
          </Typography>
        </Box>

        {/* Fun Loading Message */}
        <Box sx={{ mt: 3 }}>
          <Typography 
            variant="caption" 
            sx={{ 
              color: 'text.disabled',
              fontStyle: 'italic'
            }}
          >
            Our AI is working hard to find you the best deals ✈️
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
};
