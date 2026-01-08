import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert, PanResponder } from 'react-native';
import apiService from '../services/apiService';

const ControlPanel = () => {
  const [manualMode, setManualMode] = useState(false);
  const [lightOn, setLightOn] = useState(false);
  const [heaterOn, setHeaterOn] = useState(false);
  const [fanOn, setFanOn] = useState(false);
  const [pumpOn, setPumpOn] = useState(false);
  const [sprinklerOn, setSprinklerOn] = useState(false);
  const [loading, setLoading] = useState({});
  const [isWateringPressed, setIsWateringPressed] = useState(false);
  const [isSprinklerPressed, setIsSprinklerPressed] = useState(false);

  // Fetch initial status
  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const manualSettings = await apiService.getManualSettings();
      setManualMode(manualSettings.is_manual === true);
      setLightOn(manualSettings.light === true);
      setHeaterOn(manualSettings.heater === true);
      setFanOn(manualSettings.fan === true);
      setPumpOn(manualSettings.pump === true);
      setSprinklerOn(manualSettings.sprinkler === true);
    } catch (error) {
      console.error('Error fetching status:', error);
    }
  };

  const handleDeviceToggle = async (device, currentState) => {
    const newState = currentState ? 'off' : 'on';
    setLoading(prev => ({ ...prev, [device]: true }));

    try {
      await apiService.toggleDevice(device, newState);
      
      if (device === 'manual_mode') setManualMode(!manualMode);
      if (device === 'light') setLightOn(!lightOn);
      if (device === 'heater') setHeaterOn(!heaterOn);
      if (device === 'fan') setFanOn(!fanOn);
      if (device === 'pump') setPumpOn(!pumpOn);
      if (device === 'sprinkler') setSprinklerOn(!sprinklerOn);
    } catch (error) {
      Alert.alert('Błąd', `Nie udało się zmienić stanu ${device}`);
      console.error(`Error toggling ${device}:`, error);
    } finally {
      setLoading(prev => ({ ...prev, [device]: false }));
    }
  };

  // Watering - press and hold
  const handleWateringStart = async () => {
    setIsWateringPressed(true);
    setLoading(prev => ({ ...prev, pump: true }));
    try {
      await apiService.toggleDevice('pump', 'on');
      setPumpOn(true);
    } catch (error) {
      Alert.alert('Błąd', 'Nie udało się włączyć nawadniania');
      console.error('Error starting watering:', error);
    } finally {
      setLoading(prev => ({ ...prev, pump: false }));
    }
  };

  const handleWateringEnd = async () => {
    setIsWateringPressed(false);
    setLoading(prev => ({ ...prev, pump: true }));
    try {
      await apiService.toggleDevice('pump', 'off');
      setPumpOn(false);
    } catch (error) {
      Alert.alert('Błąd', 'Nie udało się wyłączyć nawadniania');
      console.error('Error stopping watering:', error);
    } finally {
      setLoading(prev => ({ ...prev, pump: false }));
    }
  };

  // Sprinkler - press and hold
  const handleSprinklerStart = async () => {
    setIsSprinklerPressed(true);
    setLoading(prev => ({ ...prev, sprinkler: true }));
    try {
      await apiService.toggleDevice('sprinkler', 'on');
      setSprinklerOn(true);
    } catch (error) {
      Alert.alert('Błąd', 'Nie udało się włączyć zraszania');
      console.error('Error starting sprinkler:', error);
    } finally {
      setLoading(prev => ({ ...prev, sprinkler: false }));
    }
  };

  const handleSprinklerEnd = async () => {
    setIsSprinklerPressed(false);
    setLoading(prev => ({ ...prev, sprinkler: true }));
    try {
      await apiService.toggleDevice('sprinkler', 'off');
      setSprinklerOn(false);
    } catch (error) {
      Alert.alert('Błąd', 'Nie udało się wyłączyć zraszania');
      console.error('Error stopping sprinkler:', error);
    } finally {
      setLoading(prev => ({ ...prev, sprinkler: false }));
    }
  };

  const ControlTile = ({ device, label, isOn, isPressable, onPressIn, onPressOut }) => (
    <TouchableOpacity
      style={[
        styles.tile,
        isOn && styles.tileActive,
        isPressable && isOn && styles.tilePressableActive,
        isPressable && !isOn && styles.tilePressable,
        !manualMode && device !== 'manual_mode' && styles.tileDisabled
      ]}
      onPress={!isPressable ? () => handleDeviceToggle(device, isOn) : undefined}
      onPressIn={isPressable ? onPressIn : undefined}
      onPressOut={isPressable ? onPressOut : undefined}
      disabled={loading[device] || (!manualMode && device !== 'manual_mode')}
      activeOpacity={0.7}
      hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
    >
      <Text style={[styles.tileLabel, isOn && styles.tileLabelActive]}>
        {label}
      </Text>
      <Text style={[styles.tileStatus, isOn && styles.tileStatusActive]}>
        {isPressable 
          ? (isOn ? '🟢 ACTIVE' : 'PRESS & HOLD')
          : (isOn ? '✓ ON' : '○ OFF')
        }
      </Text>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <View style={styles.grid}>
        {/* Row 1 */}
        <ControlTile 
          device="manual_mode" 
          label="Manual Mode" 
          isOn={manualMode}
        />
        <ControlTile 
          device="light" 
          label="Light" 
          isOn={lightOn}
        />

        {/* Row 2 */}
        <ControlTile 
          device="heater" 
          label="Heater" 
          isOn={heaterOn}
        />
        <ControlTile 
          device="fan" 
          label="Fan" 
          isOn={fanOn}
        />

        {/* Row 3 */}
        <ControlTile 
          device="pump" 
          label="Watering" 
          isOn={pumpOn}
          isPressable={true}
          onPressIn={handleWateringStart}
          onPressOut={handleWateringEnd}
        />
        <ControlTile 
          device="sprinkler" 
          label="Sprinkler" 
          isOn={sprinklerOn}
          isPressable={true}
          onPressIn={handleSprinklerStart}
          onPressOut={handleSprinklerEnd}
        />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'transparent',
    paddingTop: 20,
    paddingHorizontal: 60,
    paddingBottom: 20,
    justifyContent: 'center',
  },
  grid: {
    flex: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: 30,
    alignContent: 'space-around',
  },
  tile: {
    width: '22%',
    aspectRatio: 1,
    backgroundColor: 'rgba(30, 30, 30, 0.7)',
    borderRadius: 14,
    padding: 6,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 0,
  },
  tileActive: {
    backgroundColor: 'rgba(76, 175, 80, 0.8)',
  },
  tilePressable: {
    backgroundColor: 'rgba(30, 30, 30, 0.7)',
  },
  tilePressableActive: {
    backgroundColor: 'rgba(76, 175, 80, 0.9)',
  },
  tileDisabled: {
    backgroundColor: 'rgba(80, 80, 80, 0.5)',
    opacity: 0.5,
  },
  tileLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#aaa',
    marginBottom: 6,
    textAlign: 'center',
  },
  tileLabelActive: {
    color: '#fff',
  },
  tileStatus: {
    fontSize: 11,
    color: '#888',
    fontWeight: '500',
    textAlign: 'center',
  },
  tileStatusActive: {
    color: '#fff',
  },
});

export default ControlPanel;
