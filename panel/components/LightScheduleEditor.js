import React, { useState, useEffect } from 'react';
import { View, StyleSheet, Text } from 'react-native';
import apiService from '../services/apiService';
import ValueSlider from './ValueSlider';
import { FontFamily } from '../GlobalStyles';

const LightScheduleEditor = ({ onSliderStart, onSliderEnd }) => {
  const [startHour, setStartHour] = useState(18);
  const [endHour, setEndHour] = useState(6);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch current light schedule
  useEffect(() => {
    const fetchSchedule = async () => {
      try {
        const settings = await apiService.getSettings();
        setStartHour(settings.start_hour || 18);
        setEndHour(settings.end_hour || 6);
        setIsLoading(false);
      } catch (error) {
        console.error('Error calculating light schedule:', error);
        setIsLoading(false);
      }
    };

    fetchSchedule();
  }, []);

  const handleStartHourChange = async (newHour) => {
    setStartHour(newHour);
    try {
      await apiService.updateSettings({ start_hour: Math.round(newHour) });
    } catch (error) {
      console.error('Error updating start hour:', error);
    }
  };

  const handleEndHourChange = async (newHour) => {
    setEndHour(newHour);
    try {
      await apiService.updateSettings({ end_hour: Math.round(newHour) });
    } catch (error) {
      console.error('Error updating end hour:', error);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.container}>
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.slidersContainer}>
        {/* Light Label */}
        <View style={styles.lightLabelWrapper}>
          <Text style={styles.lightLabel}>Light</Text>
        </View>

        {/* Start Hour Slider */}
        <View style={styles.sliderWrapper}>
          <Text style={styles.label}>On at</Text>
          <ValueSlider
            name1="Start"
            value={startHour}
            min={0}
            max={23}
            step={1}
            unit="h"
            onValueChange={handleStartHourChange}
            onSliderStart={onSliderStart}
            onSliderEnd={onSliderEnd}
          />
        </View>

        {/* Schedule Display - Between Sliders */}
        <View style={styles.scheduleDisplay}>
          <Text style={styles.scheduleText}>
            {String(Math.round(startHour)).padStart(2, '0')}:00
          </Text>
          <Text style={styles.scheduleLabel}>to</Text>
          <Text style={styles.scheduleText}>
            {String(Math.round(endHour)).padStart(2, '0')}:00
          </Text>
        </View>

        {/* End Hour Slider */}
        <View style={styles.sliderWrapper}>
          <Text style={styles.label}>Off at</Text>
          <ValueSlider
            name1="End"
            value={endHour}
            min={0}
            max={23}
            step={1}
            unit="h"
            onValueChange={handleEndHourChange}
            onSliderStart={onSliderStart}
            onSliderEnd={onSliderEnd}
          />
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'rgba(30, 30, 30, 0.7)',
    borderRadius: 16,
    paddingLeft: 20,
    paddingRight: 16,
    paddingTop: 16,
    paddingBottom: 16,
    minHeight: 120,
    opacity: 0.7,
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    fontFamily: FontFamily.workSansMedium,
    color: '#ffffff',
    marginBottom: 14,
    letterSpacing: 0.5,
    textAlign: 'center',
  },
  slidersContainer: {
    flexDirection: 'row',
    justifyContent: 'flex-start',
    alignItems: 'center',
    gap: 20,
    marginBottom: 12,
  },
  lightLabelWrapper: {
    justifyContent: 'center',
    alignItems: 'center',
    width: 50,
  },
  lightLabel: {
    fontSize: 22,
    fontWeight: '300',
    fontFamily: FontFamily.workSansLight,
    color: '#ffffff',
    letterSpacing: 0.3,
  },
  sliderWrapper: {
    flex: 1,
    alignItems: 'center',
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
    fontFamily: FontFamily.workSansMedium,
    color: '#aaaaaa',
    marginBottom: 8,
    letterSpacing: 0.3,
  },
  scheduleDisplay: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 8,
    flexDirection: 'column',
  },
  scheduleLabel: {
    fontSize: 12,
    fontFamily: FontFamily.workSansRegular,
    color: '#888888',
    letterSpacing: 0.2,
    marginVertical: 4,
  },
  scheduleText: {
    fontSize: 18,
    fontWeight: '300',
    fontFamily: FontFamily.workSansLight,
    color: '#ffffff',
    letterSpacing: 0.3,
  },
  loadingText: {
    fontSize: 14,
    fontFamily: FontFamily.workSansRegular,
    color: '#888888',
    textAlign: 'center',
  },
});

export default LightScheduleEditor;
