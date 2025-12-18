import React, { useState, useEffect } from 'react';
import { View, StyleSheet, Dimensions, SafeAreaView, Text } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import CircularGauge from './components/CircularGauge';
import LightPanel from './components/LightPanel';
import WateringPanel from './components/WateringPanel';

const { width, height } = Dimensions.get('window');

export default function App() {
  const [time, setTime] = useState(new Date());
  const [temperature, setTemperature] = useState(28);
  const [humidity, setHumidity] = useState(30);

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const formatDate = () => {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const day = days[time.getDay()];
    const month = months[time.getMonth()];
    const date = time.getDate();
    return `${day}, ${month} ${date}`;
  };

  const formatTime = () => {
    return time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* Main Grid Layout */}
      <View style={styles.mainGrid}>
        {/* Left Column - Gauges */}
        <View style={styles.leftColumn}>
          {/* Header - Time and Date */}
          <View style={styles.header}>
            <Text style={styles.time}>{formatTime()}</Text>
            <Text style={styles.date}>{formatDate()}</Text>
          </View>

          {/* Gauges Row */}
          <View style={styles.gaugesRow}>
          <CircularGauge
            value={temperature}
            maxValue={50}
            unit="°C"
            label="Temperature"
            color="#FF6B6B"
            size={200}
            onValueChange={setTemperature}
          />
          <CircularGauge
            value={humidity}
            maxValue={100}
            unit="%"
            label="Humidity"
            color="#4ECDC4"
            size={200}
            onValueChange={setHumidity}
          />
          </View>
        </View>

        {/* Right Column - Panels */}
        <View style={styles.rightColumn}>
          <LightPanel />
          <WateringPanel />
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a1a',
  },
  mainGrid: {
    flex: 1,
    flexDirection: 'row',
    paddingHorizontal: 24,
    paddingVertical: 24,
    gap: 24,
  },
  leftColumn: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  rightColumn: {
    flex: 0.75,
    flexDirection: 'column',
    justifyContent: 'space-between',
    gap: 16,
  },
  header: {
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 30,
  },
  time: {
    fontSize: 72,
    fontWeight: '300',
    color: '#ffffff',
    letterSpacing: 2,
  },
  date: {
    fontSize: 18,
    color: '#888888',
    marginTop: 10,
    letterSpacing: 0.5,
  },
  gaugesRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 30,
    alignItems: 'center',
  },
});
