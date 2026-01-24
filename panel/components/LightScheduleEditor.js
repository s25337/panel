import React, { useState, useEffect } from 'react';
import { View, StyleSheet, Text, TouchableOpacity } from 'react-native';
import apiService from '../services/apiService';
import { FontFamily, ResponsiveSizes } from '../GlobalStyles';

const LightScheduleEditor = ({ onSliderStart, onSliderEnd }) => {
  const [startHour, setStartHour] = useState(18);
  const [endHour, setEndHour] = useState(6);
  const [isLoading, setIsLoading] = useState(true);

  const cachedHours = { start_hour: 18, end_hour: 6 };


  useEffect(() => {
    const fetchSchedule = async () => {
      try {
        const settings = await apiService.getSettings();
        if (settings.start_hour !== undefined && settings.start_hour !== null && settings.end_hour !== undefined && settings.end_hour !== null) {
          setStartHour(settings.start_hour);
          setEndHour(settings.end_hour);
          setIsLoading(false);
        }
        else {
          console.warn('Start and end hour not found in settings, using cached value.');
          setStartHour((prev) => prev || cachedHours.start_hour);
          setEndHour((prev) => prev || cachedHours.end_hour);
          setIsLoading(false);
        }
    } catch (error) {
       console.error('Error calculating light schedule:', error);
      setStartHour((prev) => prev || cachedHours.start_hour);
      setEndHour((prev) => prev || cachedHours.end_hour);
      setIsLoading(false);
    }
    };

    fetchSchedule();
  }, []);

  const handleStartHourChange = (newHour) => {
    setStartHour(newHour);
  };

  const handleStartHourComplete = async (newHour) => {
    try {
      await apiService.updateSettings({ start_hour: Math.round(newHour) });
    } catch (error) {
      console.error('Error updating start hour:', error);
    }
  };

  const handleEndHourChange = (newHour) => {
    setEndHour(newHour);
  };

  const handleEndHourComplete = async (newHour) => {
    try {
      await apiService.updateSettings({ end_hour: Math.round(newHour) });
    } catch (error) {
      console.error('Error updating end hour:', error);
    }
  };

  const clampHour = (value) => Math.max(0, Math.min(23, value));

  const displayHour = (value) => String(Math.round(value)).padStart(2, '0');

  const changeStartHour = (delta) => {
    const nextHour = clampHour(Math.round(startHour) + delta);
    if (nextHour === Math.round(startHour)) return;
    onSliderStart?.();
    handleStartHourChange(nextHour);
    handleStartHourComplete(nextHour);
    onSliderEnd?.();
  };

  const changeEndHour = (delta) => {
    const nextHour = clampHour(Math.round(endHour) + delta);
    if (nextHour === Math.round(endHour)) return;
    onSliderStart?.();
    handleEndHourChange(nextHour);
    handleEndHourComplete(nextHour);
    onSliderEnd?.();
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
          <View style={styles.timePicker}>
            <TouchableOpacity
              style={styles.timeButton}
              onPress={() => changeStartHour(-1)}
              activeOpacity={0.7}
            >
              <Text style={styles.timeButtonText}>{'<'}</Text>
            </TouchableOpacity>
            <Text style={styles.timeValue}>{displayHour(startHour)}</Text>
            <TouchableOpacity
              style={styles.timeButton}
              onPress={() => changeStartHour(1)}
              activeOpacity={0.7}
            >
              <Text style={styles.timeButtonText}>{'>'}</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Schedule Display - Between Sliders */}
        <View style={styles.scheduleDisplay}>
          <Text style={styles.scheduleText}>
            {displayHour(startHour)}:00
          </Text>
          <Text style={styles.scheduleLabel}>to</Text>
          <Text style={styles.scheduleText}>
            {displayHour(endHour)}:00
          </Text>
        </View>

        {/* End Hour Slider */}
        <View style={styles.sliderWrapper}>
          <Text style={styles.label}>Off at</Text>
          <View style={styles.timePicker}>
            <TouchableOpacity
              style={styles.timeButton}
              onPress={() => changeEndHour(-1)}
              activeOpacity={0.7}
            >
              <Text style={styles.timeButtonText}>{'<'}</Text>
            </TouchableOpacity>
            <Text style={styles.timeValue}>{displayHour(endHour)}</Text>
            <TouchableOpacity
              style={styles.timeButton}
              onPress={() => changeEndHour(1)}
              activeOpacity={0.7}
            >
              <Text style={styles.timeButtonText}>{'>'}</Text>
            </TouchableOpacity>
          </View>
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
  timePicker: {
    width: ResponsiveSizes.sliderWidth,
    height: ResponsiveSizes.sliderHeight,
    borderRadius: ResponsiveSizes.sliderBorderRadius,
    backgroundColor: '#3a3a3a',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 18,
  },
  timeButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  timeButtonText: {
    fontSize: 20,
    fontFamily: FontFamily.workSansMedium,
    color: '#e0e0e0',
  },
  timeValue: {
    fontSize: 18,
    fontWeight: '300',
    fontFamily: FontFamily.workSansLight,
    color: '#ffffff',
    letterSpacing: 0.3,
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
