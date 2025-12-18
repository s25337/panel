import React from 'react';
import { View, StyleSheet, Text } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';

const LightPanel = () => {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Light</Text>
      
      <View style={styles.content}>
        <View style={styles.iconContainer}>
          <Svg width="60" height="60" viewBox="0 0 60 60">
            <Circle
              cx="30"
              cy="30"
              r="28"
              fill="none"
              stroke="#D4A574"
              strokeWidth="2"
            />
            {/* Light bulb */}
            <Circle cx="30" cy="22" r="8" fill="#D4A574" />
            <Path
              d="M 26 32 Q 26 36 28 38 L 32 38 Q 34 36 34 32"
              fill="none"
              stroke="#D4A574"
              strokeWidth="1.5"
            />
            <Path d="M 28 38 L 28 41 M 32 38 L 32 41" stroke="#D4A574" strokeWidth="1.5" />
          </Svg>
        </View>

        <View style={styles.info}>
          <Text style={styles.status}>On</Text>
          <Text style={styles.schedule}>Schedule: 18:00 - 06:00</Text>
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
    marginBottom: 18,
  },
  info: {
    alignItems: 'center',
  },
  status: {
    fontSize: 15,
    color: '#888888',
    marginBottom: 8,
  },
  schedule: {
    fontSize: 12,
    color: '#666666',
    textAlign: 'center',
    lineHeight: 16,
  },
});

export default LightPanel;
