import React, { useState, useEffect } from 'react';
import { View, StyleSheet, Text, TouchableOpacity } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';
import apiService from '../services/apiService';

const LightSchedulePanel = ({ status = false }) => {
  const [lightHours, setLightHours] = useState(0);
  const [startHour, setStartHour] = useState(0);
  const [startMinute, setStartMinute] = useState(0);
  const [endHour, setEndHour] = useState(0);
  const [endMinute, setEndMinute] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Pobierz harmonogram światła z backendu na starcie
  useEffect(() => {
    const fetchLightSchedule = async () => {
      try {
        const data = await apiService.getLightSchedule();
        setLightHours(data.light_hours || 0);
        setStartHour(data.start_hour || 0);
        setStartMinute(data.start_minute || 0);
        setEndHour(data.end_hour || 0);
        setEndMinute(data.end_minute || 0);
        setIsLoading(false);
      } catch (error) {
        console.error('Failed to fetch light schedule:', error);
        setIsLoading(false);
      }
    };

    fetchLightSchedule();
    // Odśwież co 10 minut
    const interval = setInterval(fetchLightSchedule, 10 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (hour, minute) => 
    `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;

  return (
    <TouchableOpacity 
      style={styles.container}
      activeOpacity={0.9}
    >
      <Text style={styles.title}>Light</Text>

      <View style={styles.content}>
        <Svg width="40" height="40" viewBox="0 0 60 60">
          <Circle
            cx="30"
            cy="30"
            r="28"
            fill="none"
            stroke={status ? '#FFD700' : '#FFB347'}
            strokeWidth="2"
          />
          {/* Light bulb */}
          <Path
            d="M 30 10 C 24 10 20 14 20 20 C 20 25 22 28 22 32 C 22 34 26 36 30 36 C 34 36 38 34 38 32 C 38 28 40 25 40 20 C 40 14 36 10 30 10 Z M 26 38 L 34 38 M 28 40 L 32 40"
            stroke={status ? '#FFD700' : '#FFB347'}
            strokeWidth="1.5"
            fill="none"
            strokeLinecap="round"
          />
        </Svg>

        <View style={styles.info}>
          <Text style={styles.hoursLabel}>
            {isLoading ? 'Loading...' : `${lightHours.toFixed(1)}h/day`}
          </Text>
          <Text style={styles.timeRange}>
            {isLoading ? '--:-- to --:--' : `${formatTime(startHour, startMinute)} to ${formatTime(endHour, endMinute)}`}
          </Text>
          <View style={styles.statusRow}>
            <Text style={styles.statusLabel}>
              {isLoading ? 'Loading...' : (status ? 'ON' : 'OFF')}
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
  info: {
    alignItems: 'center',
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  hoursLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFD700',
    marginBottom: 2,
    letterSpacing: 0.3,
  },
  timeRange: {
    fontSize: 12,
    color: '#FFB347',
    marginBottom: 2,
    letterSpacing: 0.2,
  },
  statusLabel: {
    fontSize: 12,
    color: '#888888',
  },
});

export default LightSchedulePanel;
