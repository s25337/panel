import React, { useState, useEffect } from 'react';
import { View, StyleSheet, Text } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';

const WateringPanel = () => {
  const [timeLeft, setTimeLeft] = useState({
    days: 2,
    hours: 10,
    minutes: 54,
    seconds: 33,
  });

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft(prev => {
        let { days, hours, minutes, seconds } = prev;
        
        seconds -= 1;
        if (seconds < 0) {
          seconds = 59;
          minutes -= 1;
          if (minutes < 0) {
            minutes = 59;
            hours -= 1;
            if (hours < 0) {
              hours = 23;
              days -= 1;
            }
          }
        }
        
        return { days, hours, minutes, seconds };
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const formatTime = (val) => String(val).padStart(2, '0');

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Watering</Text>

      <View style={styles.content}>
        <View style={styles.iconContainer}>
          <Svg width="60" height="60" viewBox="0 0 60 60">
            <Circle
              cx="30"
              cy="30"
              r="28"
              fill="none"
              stroke="#5DADE2"
              strokeWidth="2"
            />
            {/* Water drop */}
            <Path
              d="M 30 12 C 24 18 20 25 20 32 C 20 41 24 48 30 48 C 36 48 40 41 40 32 C 40 25 36 18 30 12 Z"
              fill="#5DADE2"
            />
          </Svg>
        </View>

        <View style={styles.info}>
          <Text style={styles.timeLabel}>Next in:</Text>
          <Text style={styles.timer}>
            {formatTime(timeLeft.days)} : {formatTime(timeLeft.hours)} : {formatTime(timeLeft.minutes)} : {formatTime(timeLeft.seconds)}
          </Text>
          <Text style={styles.tankInfo}>Water tank: 200 ml</Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#252525',
    borderRadius: 16,
    padding: 18,
    justifyContent: 'space-between',
  },
  title: {
    fontSize: 22,
    fontWeight: '300',
    color: '#ffffff',
    letterSpacing: 0.5,
    marginBottom: 14,
  },
  content: {
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
  },
  iconContainer: {
    marginBottom: 14,
  },
  info: {
    alignItems: 'center',
  },
  timeLabel: {
    fontSize: 12,
    color: '#888888',
    marginBottom: 5,
  },
  timer: {
    fontSize: 14,
    color: '#888888',
    marginBottom: 10,
    letterSpacing: 1,
  },
  tankInfo: {
    fontSize: 12,
    color: '#666666',
  },
});

export default WateringPanel;
