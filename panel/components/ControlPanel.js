import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import * as apiService from '../services/apiService';

const ControlPanel = () => {
  const [fanOn, setFanOn] = useState(false);
  const [lightOn, setLightOn] = useState(false);
  const [pumpOn, setPumpOn] = useState(false);
  const [loading, setLoading] = useState({});

  // Fetch initial status
  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const status = await apiService.getStatus();
      setFanOn(status.fan === 'on');
      setLightOn(status.light === 'on');
      setPumpOn(status.pump === 'on');
    } catch (error) {
      console.error('Error fetching status:', error);
    }
  };

  const handleDeviceToggle = async (device, currentState) => {
    const newState = currentState ? 'off' : 'on';
    setLoading(prev => ({ ...prev, [device]: true }));

    try {
      await apiService.toggleDevice(device, newState);
      
      if (device === 'fan') setFanOn(!fanOn);
      if (device === 'light') setLightOn(!lightOn);
      if (device === 'pump') setPumpOn(!pumpOn);
    } catch (error) {
      Alert.alert('Błąd', `Nie udało się zmienić stanu ${device}`);
      console.error(`Error toggling ${device}:`, error);
    } finally {
      setLoading(prev => ({ ...prev, [device]: false }));
    }
  };

  const DeviceButton = ({ device, label, isOn }) => (
    <TouchableOpacity
      style={[styles.deviceButton, isOn && styles.deviceButtonActive]}
      onPress={() => handleDeviceToggle(device, isOn)}
      disabled={loading[device]}
    >
      <Text style={[styles.deviceButtonText, isOn && styles.deviceButtonTextActive]}>
        {label}
      </Text>
      <Text style={[styles.deviceButtonStatus, isOn && styles.deviceButtonStatusActive]}>
        {isOn ? 'WŁĄCZONY' : 'WYŁĄCZONY'}
      </Text>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerText}>STEROWANIE MANUALNE</Text>
      </View>

      <View style={styles.devicesGrid}>
        <DeviceButton device="fan" label="WIATRAK" isOn={fanOn} />
        <DeviceButton device="light" label="ŚWIATŁO" isOn={lightOn} />
        <DeviceButton device="pump" label="PODLEWANIE" isOn={pumpOn} />
      </View>

      <View style={styles.infoBox}>
        <Text style={styles.infoText}>
          💡 Przesuń w lewo aby wrócić do panelu głównego
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a1a',
    paddingTop: 40,
    paddingHorizontal: 20,
  },
  header: {
    marginBottom: 40,
    alignItems: 'center',
  },
  headerText: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#4CAF50',
    letterSpacing: 2,
  },
  devicesGrid: {
    flex: 1,
    justifyContent: 'center',
    gap: 20,
  },
  deviceButton: {
    backgroundColor: '#2a2a2a',
    borderRadius: 12,
    padding: 30,
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#555',
    justifyContent: 'center',
  },
  deviceButtonActive: {
    backgroundColor: '#4CAF50',
    borderColor: '#45a049',
  },
  deviceButtonText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#888',
    marginBottom: 8,
  },
  deviceButtonTextActive: {
    color: '#fff',
  },
  deviceButtonStatus: {
    fontSize: 14,
    color: '#666',
    fontWeight: 'bold',
  },
  deviceButtonStatusActive: {
    color: '#fff',
  },
  infoBox: {
    backgroundColor: '#2a2a2a',
    borderRadius: 8,
    padding: 15,
    marginTop: 20,
    marginBottom: 20,
    borderLeftWidth: 4,
    borderLeftColor: '#4CAF50',
  },
  infoText: {
    color: '#aaa',
    fontSize: 12,
    textAlign: 'center',
  },
});

export default ControlPanel;
