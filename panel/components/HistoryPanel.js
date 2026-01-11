import React, { useState, useEffect } from 'react';
import { ScrollView, StyleSheet, Text, View, Dimensions } from 'react-native';
import { FontFamily, scale } from '../GlobalStyles';
import CombinedHistoryGraph from './CombinedHistoryGraph';

const { width } = Dimensions.get('window');

const HistoryPanel = () => {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchHistoryData();
  }, []);

  const fetchHistoryData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('http://localhost:5000/api/history', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Normalize all data to 0-100 scale
      const normalizeData = (values, min, max) => {
        if (!values || values.length === 0) return [];
        return values.map(v => {
          const normalized = ((v - min) / (max - min)) * 100;
          return Math.max(0, Math.min(100, normalized));
        });
      };

      // Generate day labels (Sun, Mon, Tue, etc.)
      const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const xLabels = data.timestamps ? data.timestamps.map((ts) => {
        const date = new Date(ts);
        return dayLabels[date.getDay()];
      }) : [];

      // Normalize temperature (0-50°C → 0-100%)
      const tempNormalized = normalizeData(data.temperature, 0, 50);
      
      // Humidity is already ~0-100%
      const humNormalized = data.humidity || [];
      
      // Normalize light (0-1000 → 0-100%)
      const lightNormalized = normalizeData(data.brightness, 0, 1000);

      setGraphData({
        xLabels,
        series: [
          {
            label: 'Temperature',
            data: tempNormalized,
            color: '#FF6B6B',
          },
          {
            label: 'Humidity',
            data: humNormalized,
            color: '#4ECDC4',
          },
          {
            label: 'Light',
            data: lightNormalized,
            color: '#FFD93D',
          },
        ],
      });
      
    } catch (err) {
      setError(err.message);
      // Use fallback data on error
      useFallbackData();
    } finally {
      setLoading(false);
    }
  };

  const useFallbackData = () => {
    const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    
    setGraphData({
      xLabels: dayLabels,
      series: [
        {
          label: 'Temperature',
          data: [40, 35, 30, 45, 60, 50, 40],
          color: '#FF6B6B',
        },
        {
          label: 'Humidity',
          data: [45, 50, 55, 60, 58, 52, 48],
          color: '#4ECDC4',
        },
        {
          label: 'Light',
          data: [0, 10, 20, 80, 100, 60, 0],
          color: '#FFD93D',
        },
      ],
    });
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <View style={styles.tile}>
          <Text style={styles.loadingText}>Loading history...</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.tile}>
        {graphData && <CombinedHistoryGraph {...graphData} />}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'transparent',
    paddingHorizontal: 60,
    paddingVertical: 50,
  },
  tile: {
    flex: 1,
    backgroundColor: 'rgba(30, 30, 30, 0.7)',
    borderRadius: 14,
    padding: 20,
    borderWidth: 0,
  },
  loadingText: {
    fontSize: 16,
    fontFamily: FontFamily.workSansLight,
    color: '#cccccc',
    textAlign: 'center',
    marginTop: 50,
  },
});

export default HistoryPanel;
