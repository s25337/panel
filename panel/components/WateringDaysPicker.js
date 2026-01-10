import React, { useState, useEffect } from 'react';
import { View, StyleSheet, Text, TouchableOpacity } from 'react-native';
import apiService from '../services/apiService';

const DAYS = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'];
const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const WateringDaysPicker = ({ onDaysChange = () => {} }) => {
  const [selectedDays, setSelectedDays] = useState(['MONDAY', 'WEDNESDAY', 'FRIDAY']);
  const [isLoading, setIsLoading] = useState(true);

  // Pobierz aktualne dni podlewania
  useEffect(() => {
    const fetchWateringDays = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/watering-days');
        if (response.ok) {
          const data = await response.json();
          setSelectedDays(data.watering_days || ['MONDAY', 'WEDNESDAY', 'FRIDAY']);
        }
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
      const response = await fetch('http://localhost:5000/api/watering-days', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ watering_days: newDays })
      });

      if (response.ok) {
        setSelectedDays(newDays);
        onDaysChange(newDays);
      }
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
      <Text style={styles.title}>Watering Days (12:00)</Text>
      
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

      <Text style={styles.infoText}>
        Selected: {selectedDays.length > 0 ? selectedDays.join(', ') : 'None'}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 20,
    backgroundColor: 'rgba(30, 30, 30, 0.7)',
    borderRadius: 16,
    alignItems: 'center',
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: 20,
    letterSpacing: 0.5,
  },
  daysGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-around',
    gap: 12,
    width: '100%',
    marginBottom: 16,
  },
  dayCircle: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#666666',
  },
  dayCircleSelected: {
    backgroundColor: '#FFD700',
    borderColor: '#FFD700',
  },
  innerCircle: {
    width: 42,
    height: 42,
    borderRadius: 21,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
  },
  innerCircleSelected: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
  },
  dayLabel: {
    fontSize: 12,
    fontWeight: '600',
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
