import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert, PanResponder, Dimensions } from 'react-native';
import apiService from '../services/apiService';
import WateringDaysPicker from './WateringDaysPicker';
import LightScheduleEditor from './LightScheduleEditor';
import ValueSlider from './ValueSlider';
import { FontFamily, scale } from '../GlobalStyles';

const { width, height } = Dimensions.get('window');

// Responsive sizes optimized for 1024x600
const RESPONSIVE_SIZES = {
  gridPaddingVertical: Math.round(40 * scale),       // 40px vertical padding
  gridPaddingHorizontal: Math.round(60 * scale),     // 60px horizontal padding
  topMargin: Math.round(50 * scale),                 // 50px top margin
};

const ControlPanel = ({ onSliderStart, onSliderEnd }) => {
  const [manualMode, setManualMode] = useState(false);
  const [lightOn, setLightOn] = useState(false);
  const [heaterOn, setHeaterOn] = useState(false);
  const [fanOn, setFanOn] = useState(false);
  const [lightIntensity, setLightIntensity] = useState(50);
  const [plantName, setPlantName] = useState('');
  const [settingId, setSettingId] = useState('');
  const [loading, setLoading] = useState({});

  // Fetch initial status
  useEffect(() => {
    fetchStatus();
    fetchLightIntensity();
    fetchCurrentSettings();
  }, []);

  const fetchLightIntensity = async () => {
    try {
      const settings = await apiService.getSettings();
      setLightIntensity(settings.light_intensity || 50);
    } catch (error) {
      console.error('Error fetching light intensity:', error);
    }
  };

  const fetchCurrentSettings = async () => {
    try {
      const settings = await apiService.getSettings();
      setSettingId(settings.setting_id || '');
      setPlantName(settings.plant_name || '');
    } catch (error) {
      console.error('Error fetching current settings:', error);
    }
  };

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

  const handleLightIntensityChange = async (newIntensity) => {
    setLightIntensity(newIntensity);
    try {
      await apiService.updateSettings({ light_intensity: Math.round(newIntensity) });
    } catch (error) {
      console.error('Error updating light intensity:', error);
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
        {/* Row 1 - Settings Display + Intensity + Heater + Fan */}
        <View style={styles.settingsDisplayTile}>
          <Text style={styles.settingLabel}>setting_id</Text>
          <Text style={styles.settingId}>{settingId}</Text>
          <Text style={styles.settingLabel}>plant_name</Text>
          <Text style={styles.plantName}>{plantName}</Text>
        </View>
        
        {/* Current Light Intensity Display */}
        <View style={styles.intensityDisplayTile}>
          <Text style={styles.intensityDisplayLabel}>Intensity</Text>
          <Text style={styles.intensityDisplayValue}>{Math.round(lightIntensity)}</Text>
        </View>
        
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
      <LightScheduleEditor onSliderStart={onSliderStart} onSliderEnd={onSliderEnd} />

      {/* Watering Days Picker - Full Width Below Grid */}
      <View style={styles.tileWateringDays}>
        <WateringDaysPicker />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'transparent',
    paddingTop: RESPONSIVE_SIZES.topMargin,
    paddingHorizontal: RESPONSIVE_SIZES.gridPaddingHorizontal,
    paddingBottom: RESPONSIVE_SIZES.gridPaddingVertical,
    justifyContent: 'flex-start',
    flexDirection: 'column',
    gap: 20,
  },
  grid: {
    width: '100%',
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: 30,
  },
  tile: {
    width: '22%',
    height: 90,
    backgroundColor: 'rgba(30, 30, 30, 0.7)',
    borderRadius: 14,
    padding: 6,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 0,
  },
  settingsDisplayTile: {
    width: '22%',
    height: 90,
    backgroundColor: 'rgba(30, 30, 30, 0.7)',
    borderRadius: 14,
    padding: 10,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 0,
  },
  intensityDisplayTile: {
    width: '22%',
    height: 90,
    backgroundColor: 'rgba(30, 30, 30, 0.7)',
    borderRadius: 14,
    padding: 10,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 0,
  },
  intensityDisplayLabel: {
    fontSize: 10,
    fontWeight: '500',
    fontFamily: FontFamily.workSansRegular,
    color: '#888',
    marginBottom: 4,
  },
  intensityDisplayValue: {
    fontSize: 24,
    fontWeight: '300',
    fontFamily: FontFamily.workSansLight,
    color: '#FFD700',
    letterSpacing: 0.5,
  },
  settingId: {
    fontSize: 13,
    fontWeight: '600',
    fontFamily: FontFamily.workSansMedium,
    color: '#FFD700',
    textAlign: 'center',
    marginBottom: 8,
  },
  plantName: {
    fontSize: 13,
    fontWeight: '600',
    fontFamily: FontFamily.workSansMedium,
    color: '#FFD700',
    textAlign: 'center',
  },
  settingsRow: {
    flexDirection: 'row',
    gap: 6,
    justifyContent: 'center',
    width: '100%',
  },
  settingItem: {
    alignItems: 'center',
  },
  settingLabel: {
    fontSize: 10,
    fontWeight: '500',
    fontFamily: FontFamily.workSansRegular,
    color: '#888',
    marginBottom: 2,
  },
  settingValue: {
    fontSize: 11,
    fontWeight: '600',
    fontFamily: FontFamily.workSansMedium,
    color: '#fff',
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
    height: 120,
    backgroundColor: 'rgba(30, 30, 30, 0.7)',
    borderRadius: 16,
    paddingLeft: 20,
    paddingRight: 12,
    paddingTop: 12,
    paddingBottom: 12,
    alignItems: 'center',
    justifyContent: 'center',
    opacity: 0.7,
  },
});

export default ControlPanel;
