import React, { useState, useEffect } from 'react';
import { View, StyleSheet, Text } from 'react-native';
import { FontFamily, ResponsiveSizes } from '../GlobalStyles';
import apiService from '../services/apiService';

const WateringPanel = ({ onSliderStart, onSliderEnd }) => {
  const [timeLeft, setTimeLeft] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sliderValue, setSliderValue] = useState(0);
  const [hasTriggeredWater, setHasTriggeredWater] = useState(false);
  const [trackWidth, setTrackWidth] = useState(null);

  // Pobierz czas podlewania z backendu na starcie
  useEffect(() => {
    const fetchWateringTimer = async () => {
      try {
        const data = await apiService.getWateringTimer();
        setTimeLeft({
          days: data.days,
          hours: data.hours,
          minutes: data.minutes,
          seconds: data.seconds,
        });
        setIsLoading(false);
      } catch (error) {
        console.error('Failed to fetch watering timer:', error);
        setIsLoading(false);
      }
    };
    
    fetchWateringTimer();
  }, []);

  // Odliczanie czasu
  useEffect(() => {
    if (!timeLeft) return;

    const timer = setInterval(() => {
      setTimeLeft(prev => {
        let { days, hours, minutes, seconds } = prev;
        
        seconds -= 1;
        if (seconds < 0) {
          seconds = 59;
          minutes -= 1;
          if (minutes < 0) {
            minutes = 59;
            hours -= 1;
            if (hours < 0) {
              hours = 23;
              days -= 1;
            }
          }
        }
        
        return { days, hours, minutes, seconds };
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft]);

  // Kiedy slider przesunięty > 80, podlej
  useEffect(() => {
    if (sliderValue > 80 && !hasTriggeredWater) {
      handleWaterTrigger();
    } else if (sliderValue < 60) {
      setHasTriggeredWater(false);
    }
  }, [sliderValue, hasTriggeredWater]);

  const handleSliderMove = (e) => {
    if (!trackWidth) return;
    const x = e.nativeEvent.locationX;
    const percentage = Math.max(0, Math.min(100, (x / trackWidth) * 100));
    setSliderValue(percentage);
  };

  const handleResponderGrant = (e) => {
    onSliderStart?.();
    handleSliderMove(e);
  };

  const handleResponderRelease = () => {
    onSliderEnd?.();
  };

  const handleWaterTrigger = async () => {
    setHasTriggeredWater(true);
    
    try {
      const settings = await apiService.getSettings();
      const waterSeconds = settings.water_seconds || 1;
      
      // Włącz podlewanie przez /api/watering
      try {
        await apiService.watering();
      } catch (err) {
        console.error('Error triggering watering:', err);
      }
      
      // Czekaj określony czas
      await new Promise(resolve => setTimeout(resolve, waterSeconds * 1000));
      
      // Odśwież timer
      try {
        const data = await apiService.getWateringTimer();
        setTimeLeft({
          days: data.days,
          hours: data.hours,
          minutes: data.minutes,
          seconds: data.seconds,
        });
      } catch (err) {
        console.error('Error refreshing timer:', err);
      }
      
      // Reset slidera
      setSliderValue(0);
      setHasTriggeredWater(false);
    } catch (error) {
      console.error('Failed to water:', error);
      setSliderValue(0);
      setHasTriggeredWater(false);
    }
  };

  const formatTime = (val) => String(val).padStart(2, '0');

  const timeString = !isLoading && timeLeft 
    ? `${formatTime(timeLeft.days)}d ${formatTime(timeLeft.hours)}h ${formatTime(timeLeft.minutes)}m`
    : '--:--:--';

  return (
    <View style={styles.container}>
      <Text style={styles.timeLabel}>Next watering in:</Text>
      <Text style={styles.timeDisplay}>{timeString}</Text>
      
      {/* Slider - taki sam jak Light */}
      <View style={styles.sliderWrapper}>
        <View
          style={styles.sliderTrack}
          onLayout={(e) => setTrackWidth(e.nativeEvent.layout.width)}
          onStartShouldSetResponder={() => true}
          onMoveShouldSetResponder={() => true}
          onResponderGrant={handleResponderGrant}
          onResponderMove={handleSliderMove}
          onResponderRelease={handleResponderRelease}
        >
          {/* Filled portion */}
          <View
            style={[
              styles.sliderFill,
              {
                width: `${sliderValue}%`,
                backgroundColor: '#4ECDC4',
              }
            ]}
            pointerEvents="none"
          />
          {/* Label na środku slidera */}
          <Text style={styles.sliderLabel} pointerEvents="none">
            {sliderValue > 80 ? 'Watering' : 'Slide to water'}
          </Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    width: '100%',
  },
  timeDisplay: {
    fontSize: 12,
    fontFamily: FontFamily.workSansMedium,
    color: '#e0e0e0',
    letterSpacing: 0.5,
    marginBottom: 8,
    textAlign: 'center',
  },
  timeLabel: {
    fontSize: 12,
    fontFamily: FontFamily.workSansRegular,
    color: '#888888',
    letterSpacing: 0.3,
    marginBottom: 2,
    textAlign: 'center',
  },
  sliderWrapper: {
    width: '100%',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  sliderTrack: {
    width: ResponsiveSizes.sliderWidth,
    height: ResponsiveSizes.sliderHeight,
    borderRadius: ResponsiveSizes.sliderBorderRadius,
    backgroundColor: '#3a3a3a',
    overflow: 'hidden',
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  sliderFill: {
    position: 'absolute',
    left: 0,
    top: 0,
    height: '100%',
    borderRadius: ResponsiveSizes.sliderBorderRadius,
  },
  sliderLabel: {
    fontSize: ResponsiveSizes.sliderFontSize,
    fontFamily: FontFamily.workSansMedium,
    color: '#888888',
    letterSpacing: 0.5,
    position: 'absolute',
    zIndex: 10,
  },
});

export default WateringPanel;
