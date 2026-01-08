import React, { useState, useEffect, useRef } from 'react';
import { View, StyleSheet, Dimensions, SafeAreaView, Text, Animated, ImageBackground } from 'react-native';
import * as Font from 'expo-font';
import { StatusBar } from 'expo-status-bar';
import { FontFamily, Color } from './GlobalStyles';
import CircularGauge from './components/CircularGauge';
import LightPanel from './components/LightPanel';
import LightSchedulePanel from './components/LightSchedulePanel';
import FanPanel from './components/FanPanel';
import WateringPanel from './components/WateringPanel';
import ControlPanel from './components/ControlPanel';
import ScreenNavigator from './components/ScreenNavigator';
import apiService from './services/apiService';

const { width, height } = Dimensions.get('window');

export default function App() {
  const [fontsLoaded, setFontsLoaded] = useState(false);
  const [time, setTime] = useState(new Date());
  const [temperature, setTemperature] = useState(28);
  const [humidity, setHumidity] = useState(30);
  const [targetTemp, setTargetTemp] = useState(25);
  const [targetHumidity, setTargetHumidity] = useState(60);
  const [isScreenOn, setIsScreenOn] = useState(true);
  const [lightStatus, setLightStatus] = useState(false);
  const [fanStatus, setFanStatus] = useState(false);
  const [manualMode, setManualMode] = useState(false);
  const [wateringInterval, setWateringInterval] = useState(null);
  const [currentScreen, setCurrentScreen] = useState(0);
  const screenTimeoutRef = useRef(null);
  const SCREEN_TIMEOUT = 30000; // 30 sekund
  const sensorPollInterval = useRef(null);
  const wateringPollInterval = useRef(null);

  // Load custom fonts
  useEffect(() => {
    const loadFonts = async () => {
      try {
        await Font.loadAsync({
          'WorkSans-ExtraLight': require('./assets/fonts/WorkSans-ExtraLight.ttf'),
          'WorkSans-Light': require('./assets/fonts/WorkSans-Light.ttf'),
          'WorkSans-Regular': require('./assets/fonts/WorkSans-Regular.ttf'),
          'WorkSans-Medium': require('./assets/fonts/WorkSans-Medium.ttf'),
        });
        setFontsLoaded(true);
      } catch (e) {
        console.error('Error loading fonts:', e);
      }
    };

    loadFonts();
  }, []);

  const fetchSensors = async () => {
    const data = await apiService.getSensors();
    if (data.temperature !== null) setTemperature(data.temperature);
    if (data.humidity !== null) setHumidity(data.humidity);
  };

  const fetchStatus = async () => {
    const data = await apiService.getStatus();
    setLightStatus(data.light || false);
    // Nie pobieramy pump/sprinkler - są obsługiwane w ControlPanel
    setFanStatus(data.fan || false);
    setManualMode(data.manual_mode || false);
  };

  const fetchSettings = async () => {
    const data = await apiService.getSettings();
    setTargetTemp(data.target_temp || 25);
    setTargetHumidity(data.target_hum || 60);
  };

  const fetchWateringTimer = async () => {
    const data = await apiService.getWateringTimer();
    if (data && data.interval_seconds) {
      setWateringInterval(data.interval_seconds);
    }
  };

  // Pobieraj dane czujników co 2 sekundy
  useEffect(() => {
    // Początkowe pobranie
    fetchSensors();
    fetchStatus();
    fetchSettings();
    fetchWateringTimer();

    // Polling co 2 sekundy
    sensorPollInterval.current = setInterval(() => {
      fetchSensors();
      fetchStatus();
    }, 2000);

    // Polling dla watering timera co 5 sekund (rzadsze)
    wateringPollInterval.current = setInterval(() => {
      fetchWateringTimer();
    }, 5000);

    return () => {
      if (sensorPollInterval.current) {
        clearInterval(sensorPollInterval.current);
      }
      if (wateringPollInterval.current) {
        clearInterval(wateringPollInterval.current);
      }
    };
  }, []);

  // Refetchuj settings gdy wrócisz na main screen (screen 0)
  useEffect(() => {
    if (currentScreen === 0) {
      fetchSettings();
    }
  }, [currentScreen]);

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Resetuj timeout bezczynności
  const resetScreenTimeout = () => {
    if (!isScreenOn) {
      wakeScreen();
      return;
    }

    if (screenTimeoutRef.current) {
      clearTimeout(screenTimeoutRef.current);
    }

    screenTimeoutRef.current = setTimeout(() => {
      sleepScreen();
    }, SCREEN_TIMEOUT);
  };

  const sleepScreen = () => {
    setIsScreenOn(false);
  };

  const wakeScreen = () => {
    setIsScreenOn(true);
    resetScreenTimeout();
  };

  const handleInteraction = () => {
    resetScreenTimeout();
  };

  useEffect(() => {
    resetScreenTimeout();
    return () => {
      if (screenTimeoutRef.current) {
        clearTimeout(screenTimeoutRef.current);
      }
    };
  }, []);

  const formatDate = () => {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const day = days[time.getDay()];
    const month = months[time.getMonth()];
    const date = time.getDate();
    return `${day}, ${month} ${date}`;
  };

  const formatTime = () => {
    return time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Wait for fonts to load before rendering
  if (!fontsLoaded) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#000' }}>
        <Text style={{ color: '#fff', fontSize: 16 }}>Loading...</Text>
      </View>
    );
  }

  return (
    <ImageBackground
      source={require('./assets/wallpaper.jpg')}
      style={styles.fullBackground}
      resizeMode="cover"
    >
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" />
        
        <View style={styles.contentWrapper}>
        {/* Screensaver - Only show current temperature and humidity */}
        {!isScreenOn ? (
          <ImageBackground
            source={require('./assets/wallpaper.jpg')}
            style={styles.fullBackground}
            resizeMode="cover"
          >
            <View 
              style={styles.screensaverContainer}
              onMouseMove={handleInteraction}
              onTouchMove={handleInteraction}
              onClick={handleInteraction}
            >
              <View style={styles.screensaverContent}>
                <View style={styles.screensaverSlider}>
                  <Text style={styles.screensaverValue}>{temperature.toFixed(1)}°C</Text>
                </View>
                
                <View style={styles.screensaverSlider}>
                  <Text style={styles.screensaverValue}>{humidity.toFixed(0)}%</Text>
                </View>
              </View>
            </View>
          </ImageBackground>
        ) : (
          <ImageBackground
            source={require('./assets/wallpaper.jpg')}
            style={styles.fullBackground}
            resizeMode="cover"
          >
            <ScreenNavigator
              onScreenChange={setCurrentScreen}
              screens={[
                // Screen 0: Main Panel - 3x2 Grid
                <View
                  key="main"
                  style={styles.screenContainer}
                >
                  {/* Top Left Time and Date */}
                  <View style={styles.topLeftTimeContainer}>
                    <Text style={styles.topLeftTime}>{formatTime()}</Text>
                    <Text style={styles.topLeftDate}>{formatDate()}</Text>
                  </View>

                  <View 
                    style={styles.mainGrid}
                  >
                {/* ROW 1 - TALL */}
                <View style={styles.rowWrapperTall}>
                  {/* Col 1: Humidity Slider */}
                  <View style={styles.gridItemTall}>
                    <CircularGauge
                      mode="humidity"
                      value={targetHumidity}
                      onChange={(newHum) => {
                        setTargetHumidity(newHum);
                        apiService.updateSettings({ target_hum: newHum });
                      }}
                      size={230}
                    />
                    <View style={styles.currentValueContainer}>
                      <Text style={styles.currentLabel}>Current: </Text>
                      <Text style={[styles.currentValue, { color: '#4ECDC4' }]}>
                        {humidity}%
                      </Text>
                    </View>
                  </View>

                  {/* Col 2: Temperature Slider */}
                  <View style={styles.gridItemTall}>
                    <CircularGauge
                      mode="temperature"
                      value={targetTemp}
                      onChange={(newTemp) => {
                        setTargetTemp(newTemp);
                        apiService.updateSettings({ target_temp: newTemp });
                      }}
                      size={230}
                    />
                    <View style={styles.currentValueContainer}>
                      <Text style={styles.currentLabel}>Current: </Text>
                      <Text style={[styles.currentValue, { color: '#FF6B6B' }]}>
                        {temperature}°C
                      </Text>
                    </View>
                  </View>

                  {/* Col 3: Manual Mode Indicator */}
                  <View style={styles.gridItemTall}>
                    <View style={styles.headerBox}>
                      <Text style={[
                        styles.manualModeIndicator,
                        { color: manualMode ? '#FF9800' : '#666666' }
                      ]}>
                        MANUAL IS {manualMode ? 'ON' : 'OFF'}
                      </Text>
                    </View>
                  </View>
                </View>

                {/* ROW 2 - SHORT */}
                <View style={styles.rowWrapperShort}>
                  {/* Col 1: Light Schedule */}
                  <View style={styles.gridItemShort}>
                    <LightSchedulePanel status={lightStatus} />
                  </View>

                  {/* Col 2: Watering Info */}
                  <View style={styles.gridItemShort}>
                    <WateringPanel />
                  </View>

                  {/* Col 3: Fan Status */}
                  <View style={styles.gridItemShort}>
                    <FanPanel status={fanStatus} />
                  </View>
                </View>
              </View>
                </View>,
              // Screen 1: Control Panel
              <View
                key="control"
                style={styles.screenContainer}
              >
                <View
                  style={styles.container}
                >
                  <ControlPanel />
                </View>
              </View>,
            ]}
            />
          </ImageBackground>
        )}
        </View>
      </SafeAreaView>
    </ImageBackground>
  );
}

const styles = StyleSheet.create({
  fullBackground: {
    flex: 1,
    width: '100%',
    height: '100%',
  },
  screenContainer: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  container: {
    flex: 1,
    backgroundColor: 'transparent',
    fontFamily: FontFamily.workSansRegular,
  },
  contentWrapper: {
    flex: 1,
  },
  backgroundImage: {
    resizeMode: 'cover',
    flex: 1,
  },
  mainGrid: {
    flex: 1,
    flexDirection: 'column',
    paddingHorizontal: 35,
    paddingVertical: 35,
    gap: 25,
    justifyContent: 'space-between',
    marginTop: 45,
  },
  rowWrapperTall: {
    flex: 1.2,
    flexDirection: 'row',
    gap: 25,
  },
  rowWrapperShort: {
    flex: 0.7,
    flexDirection: 'row',
    gap: 25,
  },
  gridItemTall: {
    flex: 1,
    backgroundColor: 'rgba(30, 30, 30, 0.7)',
    borderRadius: 24,
    padding: 8,
    justifyContent: 'center',
    alignItems: 'center',
    opacity: 0.7,
  },
  gridItemShort: {
    flex: 1,
    backgroundColor: 'rgba(30, 30, 30, 0.7)',
    borderRadius: 24,
    padding: 8,
    justifyContent: 'center',
    alignItems: 'center',
    opacity: 0.7,
  },
  gridLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#aaaaaa',
    marginBottom: 8,
    letterSpacing: 0.5,
  },
  currentValue: {
    fontSize: 18,
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  currentLabel: {
    fontSize: 12,
    color: '#888888',
    letterSpacing: 0.3,
  },
  currentValueContainer: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginTop: -20,
    justifyContent: 'center',
  },
  headerBox: {
    justifyContent: 'center',
    alignItems: 'center',
    flex: 1,
  },
  statusBox: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 10,
    flex: 1,
  },
  statusIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  statusOn: {
    backgroundColor: '#4CAF50',
    shadowColor: '#4CAF50',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 8,
  },
  statusOff: {
    backgroundColor: '#666666',
  },
  statusText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#ffffff',
  },
  leftColumn: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  rightColumn: {
    flex: 0.75,
    flexDirection: 'column',
    justifyContent: 'space-between',
    gap: 16,
  },
  leftColumnSmall: {
    flex: 0.5,
    justifyContent: 'flex-start',
    alignItems: 'stretch',
    paddingTop: 10,
  },
  rightColumnLarge: {
    flex: 1.5,
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
  },
  panelsColumn: {
    flex: 1,
    justifyContent: 'space-between',
    gap: 16,
  },
  gaugesColumn: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 40,
    alignItems: 'center',
  },
  header: {
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 30,
  },
  time: {
    fontSize: 72,
    fontFamily: FontFamily.workSansLight,
    color: '#ffffff',
    letterSpacing: 2,
  },
  date: {
    fontSize: 18,
    color: '#888888',
    marginTop: 10,
    letterSpacing: 0.5,
  },
  manualModeIndicator: {
    fontSize: 14,
    color: '#FF9800',
    marginTop: 8,
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  sensorValues: {
    alignItems: 'center',
    marginBottom: 20,
  },
  sensorText: {
    fontSize: 16,
    color: '#aaaaaa',
    letterSpacing: 0.5,
  },
  screensaverContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
  },
  screensaverContent: {
    alignItems: 'center',
    gap: 20,
  },
  screensaverLabel: {
    fontSize: 24,
    fontFamily: FontFamily.workSansLight,
    color: '#ffffff',
    letterSpacing: 1,
  },
  screensaverSlider: {
    width: 300,
    height: 80,
    backgroundColor: '#252525',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#444444',
  },
  screensaverValue: {
    fontSize: 48,
    fontFamily: FontFamily.workSansLight,
    color: '#4ECDC4',
    letterSpacing: 2,
  },
  topLeftTimeContainer: {
    position: 'absolute',
    top: 20,
    left: 20,
    zIndex: 100,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  topLeftTime: {
    fontSize: 20,
    fontFamily: FontFamily.workSansLight,
    color: '#ffffff',
    letterSpacing: 1,
  },
  topLeftDate: {
    fontSize: 20,
    fontFamily: FontFamily.workSansLight,
    color: '#ffffff',
    letterSpacing: 0.5,
  },
});
