import React, { useState, useEffect } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { FontFamily } from '../GlobalStyles';
import HistoryGraph from './HistoryGraph';

const HistoryPanel = () => {
  const [temperatureData, setTemperatureData] = useState(null);
  const [humidityData, setHumidityData] = useState(null);
  const [lightData, setLightData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchHistoryData();
  }, []);

  const fetchHistoryData = async (retries = 3) => {
    try {
      setLoading(true);
      setError(null);
      
      console.log(`📡 Fetching history (attempt ${4 - retries}/3)...`);
      
      const response = await fetch('http://localhost:5000/api/history', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      
      console.log('📡 Response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('📊 History data received:', data);
      console.log('✅ Data points:', data.count);
      
      // Transform API data to graph format
      const transformToGraphData = (values, title, yMin, yMax, color) => {
        const labels = (data.timestamps || []).map((ts) => {
          const date = new Date(ts);
          return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
        });
        
        return {
          title,
          labels: labels.length > 0 ? labels : ['No data'],
          series: values && values.length > 0 ? values : [0],
          yMin,
          yMax,
          yTicks: generateTicks(yMin, yMax),
          color,
        };
      };
      
      setTemperatureData(transformToGraphData(
        data.temperature,
        'Temperature History',
        18,
        30,
        '#FF6B6B'
      ));
      
      setHumidityData(transformToGraphData(
        data.humidity,
        'Humidity History',
        40,
        70,
        '#4ECDC4'
      ));
      
      setLightData(transformToGraphData(
        data.brightness,
        'Light Intensity History',
        0,
        1000,
        '#FFD93D'
      ));
      
    } catch (err) {
      console.error('❌ Error fetching history:', err);
      console.error('❌ Error message:', err.message);
      setError(err.message);
      // Use fallback data on error
      useFallbackData();
    } finally {
      setLoading(false);
    }
  };

  const useFallbackData = () => {
    const fallbackLabels = ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00'];
    
    setTemperatureData({
      title: 'Temperature History',
      labels: fallbackLabels,
      series: [22, 21, 20, 25, 28, 26, 23],
      yMin: 18,
      yMax: 30,
      yTicks: [18, 21, 24, 27, 30],
      color: '#FF6B6B',
    });

    setHumidityData({
      title: 'Humidity History',
      labels: fallbackLabels,
      series: [45, 50, 55, 60, 58, 52, 48],
      yMin: 40,
      yMax: 70,
      yTicks: [40, 50, 60, 70],
      color: '#4ECDC4',
    });

    setLightData({
      title: 'Light Intensity History',
      labels: fallbackLabels,
      series: [0, 0, 20, 80, 100, 60, 0],
      yMin: 0,
      yMax: 100,
      yTicks: [0, 25, 50, 75, 100],
      color: '#FFD93D',
    });
  };

  const generateTicks = (min, max, count = 5) => {
    const step = (max - min) / (count - 1);
    return Array.from({ length: count }, (_, i) => Math.round(min + i * step));
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <Text style={styles.loadingText}>Loading history...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>Error: {error}</Text>
        <Text style={styles.retryText}>Using sample data</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <View style={styles.header}>
        <Text style={styles.title}>History</Text>
        <Text style={styles.subtitle}>Daily Statistics</Text>
      </View>

      {temperatureData && <HistoryGraph {...temperatureData} />}
      {humidityData && <HistoryGraph {...humidityData} />}
      {lightData && <HistoryGraph {...lightData} />}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  contentContainer: {
    paddingHorizontal: 60,
    paddingVertical: 50,
    paddingBottom: 40,
  },
  header: {
    marginBottom: 30,
    gap: 8,
  },
  title: {
    fontSize: 28,
    fontFamily: FontFamily.workSansMedium,
    color: '#ffffff',
  },
  subtitle: {
    fontSize: 14,
    fontFamily: FontFamily.workSansLight,
    color: '#888888',
  },
  loadingText: {
    fontSize: 16,
    fontFamily: FontFamily.workSansLight,
    color: '#cccccc',
    textAlign: 'center',
    marginTop: 50,
  },
  errorText: {
    fontSize: 14,
    fontFamily: FontFamily.workSansLight,
    color: '#ff6b6b',
    textAlign: 'center',
    marginTop: 50,
  },
  retryText: {
    fontSize: 12,
    fontFamily: FontFamily.workSansLight,
    color: '#888888',
    textAlign: 'center',
    marginTop: 10,
  },
});

export default HistoryPanel;
