import React, { useState, useEffect, useRef } from 'react';
import { View, ScrollView, Text, TouchableOpacity } from 'react-native';
import { FontFamily } from '../GlobalStyles';
import apiService from '../services/apiService';

const LogModal = ({ visible, onClose, setPairingStatus }) => {
  const [bluetoothLogs, setBluetoothLogs] = useState([]);
  const bluetoothPollInterval = useRef(null);

  useEffect(() => {
    if (visible) {
      startLogging();
    } else {
      stopLogging();
    }

    return () => stopLogging();
  }, [visible]);

  const startLogging = async () => {
    setBluetoothLogs([]);
    
    try {
      const response = await apiService.startBluetooth();
      if (response.status === 'ok') {
        if (setPairingStatus) setPairingStatus('success');
        setTimeout(() => { if (setPairingStatus) setPairingStatus('idle'); }, 3000);
      } else {
        if (setPairingStatus) setPairingStatus('error');
        setTimeout(() => { if (setPairingStatus) setPairingStatus('idle'); }, 3000);
      }
    } catch (error) {
      console.error('Failed to start bluetooth:', error);
      if (setPairingStatus) setPairingStatus('error');
      setTimeout(() => { if (setPairingStatus) setPairingStatus('idle'); }, 3000);
    }

    // Start polling for bluetooth logs
    const pollBluetoothLogs = async () => {
      try {
        const data = await apiService.getBluetoothLogs();
        if (data && data.logs) {
          setBluetoothLogs(data.logs);
        }
      } catch (error) {
        console.error('Error fetching bluetooth logs:', error);
      }
    };

    pollBluetoothLogs();
    bluetoothPollInterval.current = setInterval(pollBluetoothLogs, 2000);
  };

  const stopLogging = () => {
    if (bluetoothPollInterval.current) {
      clearInterval(bluetoothPollInterval.current);
      bluetoothPollInterval.current = null;
    }
  };

  const handleClose = () => {
    stopLogging();
    setBluetoothLogs([]);
    onClose();
  };

  if (!visible) return null;

  return (
    <View style={styles.bluetoothModalOverlay}>
      <View style={styles.spacerTop}></View>
      <View style={styles.bluetoothContent}>
        <ScrollView style={styles.bluetoothLogsContainer}>
          {bluetoothLogs.map((log, index) => (
            <Text key={index} style={styles.bluetoothLogText}>
              {log}
            </Text>
          ))}
          {bluetoothLogs.length === 0 && (
            <Text style={styles.bluetoothLogText}>Waiting for logs...</Text>
          )}
        </ScrollView>
      </View>
      
      <TouchableOpacity 
        style={styles.bluetoothCloseButton} 
        onPress={handleClose}
      >
        <Text style={styles.bluetoothCloseButtonText}>✕</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = {
  bluetoothModalOverlay: {
    position: 'fixed',
    top: 0, 
    left: 0, 
    right: 0, 
    bottom: 0,
    width: '100vw',
    height: '100vh',
    backgroundColor: '#000000',
    zIndex: 99999, // Much higher z-index to be above everything
  },
  spacerTop: {
    height: 150, // Fixed height spacer to push content down
    width: '100%',
  },
  bluetoothContent: {
    flex: 1,
    justifyContent: 'flex-start',
    alignItems: 'center',
    paddingHorizontal: 40,
  },
  bluetoothLogsContainer: {
    flex: 1,
    width: '100%',
    padding: 20,
  },
  bluetoothLogText: {
    color: '#ffffff',
    fontFamily: FontFamily.workSansLight,
    fontSize: 25,
    marginBottom: 5,
    textAlign: 'left',
  },
  bluetoothCloseButton: {
    position: 'absolute',
    top: 40,
    right: 40,
    width: 60,
    height: 60,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 30,
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.5)',
    zIndex: 10001,
  },
  bluetoothCloseButtonText: {
    color: '#ffffff',
    fontSize: 32,
    fontWeight: 'bold',
    textAlign: 'center',
  },
};

export default LogModal;
