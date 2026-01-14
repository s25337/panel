import React, { useState, useEffect } from 'react';
import { View, StyleSheet, Text, TouchableOpacity } from 'react-native';
import apiService from '../services/apiService';
import { FontFamily } from '../GlobalStyles';

const DAYS = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'];
const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const WateringDaysPicker = ({ onDaysChange = () => {} }) => {
  const [selectedDays, setSelectedDays] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const cachedDays = { watering_days: ['MONDAY', 'WEDNESDAY', 'FRIDAY'] };

  // Pobierz aktualne dni podlewania
  useEffect(() => {
    const fetchWateringDays = async () => {
      try {
        const response = await fetch('/settings_config.json');
      if (!response.ok) {
        throw new Error('Failed to fetch settings');
      }
      const data = await response.json();
        // Zamień numery dni na nazwy (jeśli trzeba)
        const DAYS = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'];
        let selected = data.watering_days || [];
        if (selected && typeof selected[0] === 'number') {
          selected = selected.map(d => DAYS[(d-1)%7]);
        }
        cachedDays.watering_days = selected || cachedDays.watering_days;
      console.log('cachedDays.watering_days updated:', cachedDays.watering_days);
      console.log('Fetched watering days:', selected);
      setSelectedDays(selected || cachedDays.watering_days);
       
      } catch (error) {
        console.error('Error fetching watering days:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchWateringDays();
  }, []);


  const toggleDay = async (day) => {
    let newDays;
    
    if (selectedDays.includes(day)) {
      // Usuń dzień
      newDays = selectedDays.filter(d => d !== day);
    } else {
      // Dodaj dzień
      newDays = [...selectedDays, day];
    }

    // Utrzymaj kolejność dni tygodnia
    newDays = DAYS.filter(d => newDays.includes(d));

    try {
      // Zamień nazwy dni na numery (1=MONDAY, 7=SUNDAY)
      const DAY_NUMS = { MONDAY: 1, TUESDAY: 2, WEDNESDAY: 3, THURSDAY: 4, FRIDAY: 5, SATURDAY: 6, SUNDAY: 7 };
      const daysAsNums = newDays.map(d => DAY_NUMS[d]);
      await apiService.updateSettings({ watering_days: daysAsNums });
      setSelectedDays(newDays);
      onDaysChange(newDays);
    } catch (error) {
      console.error('Error updating watering days:', error);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Watering Schedule</Text>
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.contentWrapper}>
        {/* Water Label */}
        <View style={styles.waterLabelWrapper}>
          <Text style={styles.waterLabel}>Water</Text>
        </View>

        {/* Days Grid */}
        <View style={styles.daysGrid}>
          {DAYS.map((day, index) => {
            const isSelected = selectedDays.includes(day);
            return (
              <TouchableOpacity
                key={day}
                style={[
                  styles.dayCircle,
                  isSelected && styles.dayCircleSelected
                ]}
                onPress={() => toggleDay(day)}
                activeOpacity={0.7}
              >
                <View style={[
                  styles.innerCircle,
                  isSelected && styles.innerCircleSelected
                ]}>
                  <Text style={[
                    styles.dayLabel,
                    isSelected && styles.dayLabelSelected
                  ]}>
                    {DAY_LABELS[index]}
                  </Text>
                </View>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    height: '100%',
    paddingHorizontal: 6,
    paddingVertical: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  contentWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-start',
    gap: 20,
    width: '100%',
  },
  waterLabelWrapper: {
    justifyContent: 'center',
    alignItems: 'center',
    width: 50,
  },
  waterLabel: {
    fontSize: 22,
    fontWeight: '300',
    fontFamily: FontFamily.workSansLight,
    color: '#ffffff',
    letterSpacing: 0.3,
  },
  daysGrid: {
    flexDirection: 'row',
    flexWrap: 'nowrap',
    justifyContent: 'center',
    gap: 12,
    flex: 1,
  },
  dayCircle: {
    width: 65,
    height: 65,
    borderRadius: 32.5,
    backgroundColor: '#666666',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 0,
  },
  dayCircleSelected: {
    backgroundColor: '#4ECDC4',
  },
  innerCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'transparent',
  },
  innerCircleSelected: {
    backgroundColor: 'transparent',
  },
  dayLabel: {
    fontSize: 11,
    fontWeight: '600',
    fontFamily: FontFamily.workSansMedium,
    color: '#ffffff',
    letterSpacing: 0.3,
  },
  dayLabelSelected: {
    color: '#000000',
    fontWeight: '700',
  },
  infoText: {
    fontSize: 12,
    color: '#aaaaaa',
    marginTop: 8,
    letterSpacing: 0.3,
    textAlign: 'center',
  },
  loadingText: {
    fontSize: 14,
    color: '#888888',
  },
});

export default WateringDaysPicker;
