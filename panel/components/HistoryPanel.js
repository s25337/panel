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
      console.log('📊 History data received:', data);
      console.log('✅ Has temperature:', !!data.temperature, '- length:', data.temperature?.length);
      console.log('✅ Has humidity:', !!data.humidity, '- length:', data.humidity?.length);
      console.log('✅ Has brightness:', !!data.brightness, '- length:', data.brightness?.length);
      
      // Normalize all data to 0-100 scale
      const normalizeData = (values, min, max) => {
        if (!values || values.length === 0) return [];
        return values.map(v => {
          // Clamp value to valid range first, then normalize
          const clamped = Math.max(min, Math.min(max, v));
          const normalized = ((clamped - min) / (max - min)) * 100;
          return normalized;
        });
      };

      // Generate day labels (Sun, Mon, Tue, etc.) - 7 days
      const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      
      // Map 48 points to 7 days (approximately 7 points per day)
      const xLabels = Array.from({ length: 48 }, (_, i) => {
        // Show day label every ~7 points (48/7 ≈ 7)
        if (i % 7 === 0) {
          return dayLabels[Math.floor(i / 7)];
        }
        return '';
      });

      // Check if data is valid AFTER we have the normalize function
      if (data.temperature && data.temperature.length > 0 && 
          data.humidity && data.humidity.length > 0 && 
          data.brightness && data.brightness.length > 0) {
        console.log('✅ All data arrays are valid, normalizing...');
        console.log('  Raw temperature last 3:', data.temperature.slice(-3));
        console.log('  Raw humidity last 3:', data.humidity.slice(-3));
        console.log('  Raw brightness last 3:', data.brightness.slice(-3));
        
        // Normalize temperature (0-50°C → 0-100%)
        const tempNormalized = normalizeData(data.temperature, 0, 50);
        
        // Normalize humidity (0-100% → 0-100%)
        const humNormalized = normalizeData(data.humidity, 0, 100);
        
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
        
        console.log('📊 Final normalized data:');
        console.log('  Temperature last 3:', tempNormalized.slice(-3));
        console.log('  Humidity last 3:', humNormalized.slice(-3));
        console.log('  Light last 3:', lightNormalized.slice(-3));
      } else {
        console.log('❌ Data validation failed, using fallback');
        throw new Error('Invalid history data format');
      }
      
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
    
    // Generate 48 labels with day names every ~7 points
    const xLabels = Array.from({ length: 48 }, (_, i) => {
      if (i % 7 === 0) {
        return dayLabels[i / 7];
      }
      return '';
    });
    
    // Normalize all data to 0-100 scale
    const normalizeData = (values, min, max) => {
      if (!values || values.length === 0) return [];
      return values.map(v => {
        const clamped = Math.max(min, Math.min(max, v));
        const normalized = ((clamped - min) / (max - min)) * 100;
        return normalized;
      });
    };
    
    // Generate sample data (RAW values, then normalized)
    const generateSineWave = (baseValue, amplitude, phase = 0) => {
      return Array.from({ length: 48 }, (_, i) => {
        return baseValue + amplitude * Math.sin((i / 48) * Math.PI * 2 + phase);
      });
    };
    
    const rawTemp = generateSineWave(25, 12, 0); // 13-37°C
    const rawHum = generateSineWave(60, 15, 2); // 45-75%
    const rawLight = generateSineWave(400, 300, 4); // 100-700
    
    setGraphData({
      xLabels,
      series: [
        {
          label: 'Temperature',
          data: normalizeData(rawTemp, 0, 50),
          color: '#FF6B6B',
        },
        {
          label: 'Humidity',
          data: normalizeData(rawHum, 0, 100),
          color: '#4ECDC4',
        },
        {
          label: 'Light',
          data: normalizeData(rawLight, 0, 1000),
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
