import React, { useState, useEffect } from 'react';
import { View, StyleSheet, Text, TouchableOpacity } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';
import apiService from '../services/apiService';

const LightPanel = ({ status = false, onToggle = () => {} }) => {
  const [lightIntensity, setLightIntensity] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchLightIntensity = async () => {
      try {
        const settings = await apiService.getSettings();
        setLightIntensity(settings.light_intensity || 0);
        setIsLoading(false);
      } catch (error) {
        console.error('Error fetching light intensity:', error);
        setIsLoading(false);
      }
    };

    fetchLightIntensity();
    // Update every 10 seconds
    const interval = setInterval(fetchLightIntensity, 10000);
    return () => clearInterval(interval);
  }, []);

  const intensityPercent = Math.round(lightIntensity);
  const isLightOn = lightIntensity > 0;
  const bulbColor = isLightOn ? '#FFD700' : '#D4A574';

  return (
    <TouchableOpacity 
      style={styles.container}
      onPress={onToggle}
      activeOpacity={0.9}
    >
      <Text style={styles.title}>Light</Text>
      
      <View style={styles.content}>
        <View style={styles.iconContainer}>
          <Svg width="60" height="60" viewBox="0 0 60 60">
            <Circle
              cx="30"
              cy="30"
              r="28"
              fill="none"
              stroke={bulbColor}
              strokeWidth="2"
            />
            {/* Light bulb */}
            <Circle cx="30" cy="22" r="8" fill={bulbColor} />
            <Path
              d="M 26 32 Q 26 36 28 38 L 32 38 Q 34 36 34 32"
              fill="none"
              stroke={bulbColor}
              strokeWidth="1.5"
            />
            <Path d="M 28 38 L 28 41 M 32 38 L 32 41" stroke={bulbColor} strokeWidth="1.5" />
          </Svg>
        </View>

        <View style={styles.info}>
          <Text style={styles.status}>{isLightOn ? 'ON' : 'OFF'}</Text>
          <Text style={styles.schedule}>{isLightOn ? 'LED Active' : 'LED Off'}</Text>
        </View>
      </View>

      {/* Light Intensity Display - Only show if light is on */}
      {isLightOn && (
        <View style={styles.intensityDisplay}>
          <Text style={styles.intensityNumber}>{intensityPercent}</Text>
        </View>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#252525',
    borderRadius: 16,
    padding: 18,
    justifyContent: 'space-between',
    cursor: 'pointer',
  },
  title: {
    fontSize: 22,
    fontWeight: '300',
    color: '#ffffff',
    letterSpacing: 0.5,
    marginBottom: 14,
  },
  content: {
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
  },
  iconContainer: {
    marginBottom: 18,
  },
  info: {
    alignItems: 'center',
  },
  status: {
    fontSize: 15,
    color: '#888888',
    marginBottom: 8,
  },
  schedule: {
    fontSize: 12,
    color: '#666666',
    textAlign: 'center',
    lineHeight: 16,
  },
  intensityDisplay: {
    alignItems: 'center',
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#444444',
  },
  intensityLabel: {
    fontSize: 11,
    color: '#888888',
    marginBottom: 6,
    letterSpacing: 0.3,
  },
  intensityNumber: {
    fontSize: 24,
    fontWeight: '300',
    color: '#FFD700',
    letterSpacing: 0.5,
  },
});

export default LightPanel;
