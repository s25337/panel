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

  // Pobierz watering days i oblicz czas do następnego podlewania
  useEffect(() => {
    const calculateTimeToNextWatering = async () => {
      try {
        const settings = await apiService.getSettings();
        const watering_days = settings.watering_days;
        const watering_time = settings.watering_time || '12:00';

        if (!watering_days || watering_days.length === 0) {
          setIsLoading(false);
          return;
        }

        // Parse watering_time (format: "HH:MM")
        const [targetHour, targetMinute] = watering_time.split(':').map(Number);

        // Oblicz czas do następnego podlewania
        const now = new Date();
        const currentDayOfWeek = now.getDay(); // 0 = niedziela, 6 = sobota
        
        let daysUntil = null;
        
        // Szukaj następnego dnia z listy watering_days
        for (let i = 0; i < 7; i++) {
          const checkDay = (currentDayOfWeek + i) % 7;
          if (watering_days.includes(checkDay)) {
            daysUntil = i;
            break;
          }
        }

        if (daysUntil === null) {
          setIsLoading(false);
          return;
        }

        // Jeśli to dziś i godzina już minęła, to będzie dopiero jutro
        if (daysUntil === 0) {
          const targetTime = new Date();
          targetTime.setHours(targetHour, targetMinute, 0, 0);
          
          if (now > targetTime) {
            // Godzina minęła, następne podlewanie za 7 dni
            daysUntil = 7;
          }
        }

        // Oblicz dokładny czas do następnego podlewania
        const nextWateringDate = new Date();
        nextWateringDate.setDate(nextWateringDate.getDate() + daysUntil);
        nextWateringDate.setHours(targetHour, targetMinute, 0, 0);

        // Różnica w sekundach
        const secondsLeft = Math.floor((nextWateringDate - now) / 1000);
        
        if (secondsLeft > 0) {
          const days = Math.floor(secondsLeft / 86400);
          const hours = Math.floor((secondsLeft % 86400) / 3600);
          const minutes = Math.floor((secondsLeft % 3600) / 60);
          const seconds = secondsLeft % 60;

          setTimeLeft({ days, hours, minutes, seconds });
        }

        setIsLoading(false);
      } catch (error) {
        console.error('Failed to fetch watering data:', error);
        setIsLoading(false);
      }
    };

    calculateTimeToNextWatering();
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
      // Włącz podlewanie (pompa się wyłączy automatycznie po water_seconds)
      await apiService.watering();
      
      // Reset slidera
      setSliderValue(0);
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
