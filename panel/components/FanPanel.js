import React, { useState, useEffect } from 'react';
import { View, StyleSheet, Text, TouchableOpacity } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';
import apiService from '../services/apiService';

const FanPanel = ({ status = false }) => {
  const [humidity, setHumidity] = useState(null);
  const [targetHum, setTargetHum] = useState(60);
  const [humidityStatus, setHumidityStatus] = useState('loading');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const sensors = await apiService.getSensors();
        const settings = await apiService.getSettings();
        
        setHumidity(sensors.humidity);
        setTargetHum(settings.target_hum || 60);

        // Sprawdź status wilgotności
        if (sensors.humidity < settings.target_hum - 5) {
          setHumidityStatus('low');
        } else if (sensors.humidity > settings.target_hum + 5) {
          setHumidityStatus('high');
        } else {
          setHumidityStatus('good');
        }
      } catch (error) {
        console.error('Failed to fetch fan data:', error);
        setHumidityStatus('error');
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  const getStatusText = () => {
    switch (humidityStatus) {
      case 'low':
        return 'Too low';
      case 'high':
        return 'Too high';
      case 'good':
        return 'Just right';
      default:
        return 'Loading...';
    }
  };

  const getStatusColor = () => {
    switch (humidityStatus) {
      case 'low':
        return '#FF6B6B';
      case 'high':
        return '#FFB347';
      case 'good':
        return '#4ECDC4';
      default:
        return '#888888';
    }
  };

  const formatStatus = (isOn) => isOn ? 'ON' : 'OFF';

  return (
    <TouchableOpacity 
      style={styles.container}
      activeOpacity={0.9}
    >
      <Text style={styles.title}>Fan</Text>

      <View style={styles.content}>
        <Svg width="40" height="40" viewBox="0 0 60 60">
          <Circle
            cx="30"
            cy="30"
            r="28"
            fill="none"
            stroke={status ? '#00FF00' : '#888888'}
            strokeWidth="2"
          />
          {/* Fan propeller */}
          <Path
            d="M 30 15 L 32 28 L 30 30 L 28 28 Z M 45 30 L 32 32 L 30 30 L 32 28 Z M 30 45 L 28 32 L 30 30 L 32 32 Z M 15 30 L 28 28 L 30 30 L 28 32 Z"
            fill={status ? '#00FF00' : '#888888'}
          />
          {/* Center circle */}
          <Circle
            cx="30"
            cy="30"
            r="3"
            fill={status ? '#00FF00' : '#888888'}
          />
        </Svg>

        <View style={styles.info}>
          <View style={styles.statusRow}>
            <Text style={styles.statusLabel}>
              {formatStatus(status)}
            </Text>
          </View>
          <Text style={[styles.humidityStatusLabel, { color: getStatusColor() }]}>
            {getStatusText()}
          </Text>
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
  statusLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#aaaaaa',
    letterSpacing: 0.3,
  },
  humidityStatusLabel: {
    fontSize: 12,
    fontWeight: '500',
    letterSpacing: 0.2,
    marginTop: 2,
  },
});

export default FanPanel;
