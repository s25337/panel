import React, { useState, useEffect } from 'react';
import { View, StyleSheet, Text, TouchableOpacity } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';
import apiService from '../services/apiService';

const WateringPanel = () => {
  const [timeLeft, setTimeLeft] = useState(null);
  const [intervalSeconds, setIntervalSeconds] = useState(0);
  const [waterTimesPerWeek, setWaterTimesPerWeek] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

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
        setIntervalSeconds(data.interval_seconds);
        setWaterTimesPerWeek(data.water_times_per_week || 0);
        setIsLoading(false);
      } catch (error) {
        console.error('Failed to fetch watering timer:', error);
        setIsLoading(false);
      }
    };
    
    fetchWateringTimer();
  }, []);

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

  const handlePress = async () => {
    // Pobierz świeże dane z backendu (może ustawienia się zmieniły)
    const data = await apiService.getWateringTimer();
    
    // Reset timer na pełny interwał z backendu
    setTimeLeft({
      days: data.days,
      hours: data.hours,
      minutes: data.minutes,
      seconds: data.seconds,
    });
    setIntervalSeconds(data.interval_seconds);
    
    // Pobierz settings aby dowiedzieć się ile sekund włączyć pompę
    const settings = await apiService.getSettings();
    const waterSeconds = settings.water_seconds || 1;
    
    // Włącz pompę
    await apiService.toggleDevice('pump', 'on');
    
    // Czekaj określony czas
    await new Promise(resolve => setTimeout(resolve, waterSeconds * 1000));
    
    // Wyłącz pompę
    await apiService.toggleDevice('pump', 'off');
    
    onToggle();
  };

  const formatTime = (val) => String(val).padStart(2, '0');

  return (
    <TouchableOpacity 
      style={styles.container}
      onPress={handlePress}
      activeOpacity={0.9}
    >
      <Text style={styles.title}>Watering</Text>

      <View style={styles.content}>
        <Svg width="40" height="40" viewBox="0 0 60 60">
          <Circle
            cx="30"
            cy="30"
            r="28"
            fill="none"
            stroke={status ? '#00FF00' : '#5DADE2'}
            strokeWidth="2"
          />
          {/* Water drop */}
          <Path
            d="M 30 12 C 24 18 20 25 20 32 C 20 41 24 48 30 48 C 36 48 40 41 40 32 C 40 25 36 18 30 12 Z"
            fill={status ? '#00FF00' : '#5DADE2'}
          />
        </Svg>

        <View style={styles.info}>
          <Text style={styles.timeLabel}>Next in:</Text>
          <Text style={styles.timer}>
            {isLoading || !timeLeft ? '--:--:--:--' : `${formatTime(timeLeft.days)}:${formatTime(timeLeft.hours)}:${formatTime(timeLeft.minutes)}:${formatTime(timeLeft.seconds)}`}
          </Text>
          <View style={styles.scheduleRow}>
            <Text style={styles.scheduleInfo}>
              {isLoading || !waterTimesPerWeek ? 'Loading...' : `${waterTimesPerWeek}x/week`}
            </Text>
          </View>
        </View>
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    borderRadius: 0,
    padding: 0,
    justifyContent: 'center',
    alignItems: 'center',
    cursor: 'pointer',
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    color: '#aaaaaa',
    letterSpacing: 0.5,
    marginBottom: 12,
    textAlign: 'center',
    width: '100%',
  },
  content: {
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
    gap: 8,
  },
  iconContainer: {
    marginBottom: 0,
  },
  info: {
    alignItems: 'center',
  },
  scheduleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  timeLabel: {
    fontSize: 12,
    color: '#888888',
    marginBottom: 2,
  },
  timer: {
    fontSize: 13,
    color: '#4ECDC4',
    marginBottom: 2,
    letterSpacing: 0.3,
    fontWeight: '600',
  },
  scheduleInfo: {
    fontSize: 12,
    color: '#666666',
  },
});

export default WateringPanel;
