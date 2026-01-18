import React, { useState, useEffect } from 'react';
import { View, StyleSheet, Text, TextInput, TouchableOpacity, ScrollView } from 'react-native';
import { FontFamily } from '../GlobalStyles';
import apiService from '../services/apiService';
import WateringDaysPicker from './WateringDaysPicker';

const SettingsPanel = () => {
  const [settings, setSettings] = useState({
    light_hours: 0,
    target_temp: 0,
    target_hum: 0,
    water_seconds: 0,
    light_intensity: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');

  // Pobierz ustawienia z backendu
  const fetchSettings = async () => {
    try {
      const data = await apiService.getSettings();
      setSettings(data);
    } catch (error) {
      console.error('Error fetching settings:', error);
    }
  };

  useEffect(() => {
    fetchSettings();
    setIsLoading(false);

    // Pobieraj ustawienia co 30 sekund
    const interval = setInterval(fetchSettings, 30000);
    return () => clearInterval(interval);
  }, []);

  // Zmiana wartości w input'cie
  const handleSettingChange = (key, value) => {
    const numValue = parseFloat(value) || 0;
    setSettings(prev => ({
      ...prev,
      [key]: numValue
    }));
  };

  // Wyślij ustawienia na backend
  const handleSaveSettings = async () => {
    setIsSaving(true);
    setSaveMessage('');
    try {
      const response = await apiService.updateSettings(settings);
      setSaveMessage('✅ Settings saved!');
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (error) {
      console.error('Error saving settings:', error);
      setSaveMessage('❌ Error saving settings');
      setTimeout(() => setSaveMessage(''), 3000);
    }
    setIsSaving(false);
  };

  if (isLoading) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Loading settings...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.scrollContent}>
      <Text style={styles.title}>Settings</Text>

      {/* Light Hours */}
      <View style={styles.settingGroup}>
        <Text style={styles.settingLabel}>Light Hours</Text>
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            value={String(settings.light_hours)}
            onChangeText={(value) => handleSettingChange('light_hours', value)}
            keyboardType="decimal-pad"
            placeholder="Light hours"
          />
          <Text style={styles.unit}>h</Text>
        </View>
      </View>

      {/* Target Temperature */}
      <View style={styles.settingGroup}>
        <Text style={styles.settingLabel}>Target Temperature</Text>
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            value={String(settings.target_temp)}
            onChangeText={(value) => handleSettingChange('target_temp', value)}
            keyboardType="decimal-pad"
            placeholder="Target temp"
          />
          <Text style={styles.unit}>°C</Text>
        </View>
      </View>

      {/* Target Humidity */}
      <View style={styles.settingGroup}>
        <Text style={styles.settingLabel}>Target Humidity</Text>
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            value={String(settings.target_hum)}
            onChangeText={(value) => handleSettingChange('target_hum', value)}
            keyboardType="decimal-pad"
            placeholder="Target humidity"
          />
          <Text style={styles.unit}>%</Text>
        </View>
      </View>

      {/* Watering Days (12:00) */}
      <View style={styles.settingGroup}>
        <WateringDaysPicker />
      </View>

      {/* Water Seconds */}
      <View style={styles.settingGroup}>
        <Text style={styles.settingLabel}>Water Duration</Text>
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            value={String(settings.water_seconds)}
            onChangeText={(value) => handleSettingChange('water_seconds', value)}
            keyboardType="number-pad"
            placeholder="Seconds"
          />
          <Text style={styles.unit}>s</Text>
        </View>
      </View>

      {/* Light Intensity */}
      <View style={styles.settingGroup}>
        <Text style={styles.settingLabel}>Default Light Intensity</Text>
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            value={String(settings.light_intensity)}
            onChangeText={(value) => handleSettingChange('light_intensity', value)}
            keyboardType="number-pad"
            placeholder="Light intensity"
          />
          <Text style={styles.unit}>%</Text>
        </View>
      </View>

      {/* Save Button */}
      <TouchableOpacity
        style={[styles.saveButton, isSaving && styles.saveButtonDisabled]}
        onPress={handleSaveSettings}
        disabled={isSaving}
      >
        <Text style={styles.saveButtonText}>
          {isSaving ? 'Saving...' : 'Save Settings'}
        </Text>
      </TouchableOpacity>

      {/* Save Message */}
      {saveMessage ? (
        <Text style={styles.message}>{saveMessage}</Text>
      ) : null}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: 20,
    paddingVertical: 20,
    backgroundColor: 'rgba(30, 30, 30, 0.7)',
  },
  scrollContent: {
    paddingBottom: 30,
  },
  title: {
    fontSize: 24,
    fontFamily: FontFamily.workSansMedium,
    color: '#ffffff',
    marginBottom: 24,
    textAlign: 'center',
    letterSpacing: 1,
  },
  settingGroup: {
    marginBottom: 20,
  },
  settingLabel: {
    fontSize: 14,
    fontFamily: FontFamily.workSansMedium,
    color: '#aaaaaa',
    marginBottom: 8,
    letterSpacing: 0.5,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(60, 60, 60, 0.8)',
    borderRadius: 12,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: '#444444',
  },
  input: {
    flex: 1,
    height: 44,
    color: '#ffffff',
    fontSize: 16,
    fontFamily: FontFamily.workSansRegular,
    paddingVertical: 10,
  },
  unit: {
    fontSize: 14,
    fontFamily: FontFamily.workSansRegular,
    color: '#888888',
    marginLeft: 8,
  },
  saveButton: {
    backgroundColor: '#f6ae41',
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 20,
    marginTop: 24,
    alignItems: 'center',
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 3,
  },
  saveButtonDisabled: {
    backgroundColor: '#888888',
    opacity: 0.6,
  },
  saveButtonText: {
    fontSize: 16,
    fontFamily: FontFamily.workSansMedium,
    color: '#000000',
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  message: {
    fontSize: 14,
    fontFamily: FontFamily.workSansRegular,
    color: '#4ECDC4',
    marginTop: 12,
    textAlign: 'center',
  },
});

export default SettingsPanel;
