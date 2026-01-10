import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert, PanResponder } from 'react-native';
import apiService from '../services/apiService';
import WateringDaysPicker from './WateringDaysPicker';
import LightScheduleEditor from './LightScheduleEditor';
import { FontFamily } from '../GlobalStyles';

const ControlPanel = () => {
  const [manualMode, setManualMode] = useState(false);
  const [lightOn, setLightOn] = useState(false);
  const [heaterOn, setHeaterOn] = useState(false);
  const [fanOn, setFanOn] = useState(false);
  const [loading, setLoading] = useState({});

  // Fetch initial status
  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const manualSettings = await apiService.getManualSettings();
      setManualMode(manualSettings.is_manual === true);
      setLightOn(manualSettings.light === true || manualSettings.light > 0);
      setHeaterOn(manualSettings.heater === true);
      setFanOn(manualSettings.fan === true);
      // Nie pobieramy pump/sprinkler - są obsługiwane przez press/hold UI
    } catch (error) {
      console.error('Error fetching status:', error);
    }
  };

  const handleDeviceToggle = async (device, currentState) => {
    const newState = currentState ? 'off' : 'on';
    setLoading(prev => ({ ...prev, [device]: true }));

    try {
      if (device === 'manual_mode') {
        // Special handling for manual mode toggle
        await apiService.toggleManualMode(newState);
        setManualMode(newState === 'on');
      } else {
        await apiService.toggleDevice(device, newState);
        // Refetch status po zmianie aby być pewnym stanu
        await fetchStatus();
      }
    } catch (error) {
      Alert.alert('Błąd', `Nie udało się zmienić stanu ${device}`);
      console.error(`Error toggling ${device}:`, error);
    } finally {
      setLoading(prev => ({ ...prev, [device]: false }));
    }
  };

  const ControlTile = ({ device, label, isOn, isPressable, onClick }) => (
    <TouchableOpacity
      style={[
        styles.tile,
        isOn && styles.tileActive,
        isPressable && isOn && styles.tilePressableActive,
        isPressable && !isOn && styles.tilePressable,
        !manualMode && device !== 'manual_mode' && styles.tileDisabled
      ]}
      onPress={isPressable ? onClick : () => handleDeviceToggle(device, isOn)}
      disabled={loading[device] || (!manualMode && device !== 'manual_mode')}
      activeOpacity={0.7}
      hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
    >
      <Text style={[styles.tileLabel, isOn && styles.tileLabelActive]}>
        {label}
      </Text>
      <Text style={[styles.tileStatus, isOn && styles.tileStatusActive]}>
        {isPressable 
          ? (isOn ? '🟢 ACTIVE' : 'CLICK TO RUN 2s')
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
      </View>

      {/* Light Schedule Editor - Full Width Above Watering Days */}
      <LightScheduleEditor />

      {/* Watering Days Picker - Full Width Below Grid */}
      <View style={styles.tileWateringDays}>
        <WateringDaysPicker />
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
    justifyContent: 'space-between',
    flexDirection: 'column',
  },
  grid: {
    flex: 0.6,
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: 30,
    alignContent: 'flex-start',
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
    backgroundColor: 'rgba(30, 30, 30, 0.7)',
    opacity: 0.6,
  },
  tileLabel: {
    fontSize: 13,
    fontWeight: '600',
    fontFamily: FontFamily.workSansMedium,
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
    fontFamily: FontFamily.workSansRegular,
    textAlign: 'center',
  },
  tileStatusActive: {
    color: '#fff',
  },
  tileLarge: {
    width: '46%',
    aspectRatio: 1,
    padding: 10,
  },
  tileWateringDays: {
    width: '100%',
    aspectRatio: 'auto',
    height: 100,
    backgroundColor: 'rgba(37, 37, 37, 0.7)',
    borderRadius: 16,
    padding: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
});

export default ControlPanel;
