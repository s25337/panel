import React, { useState, useEffect, useRef } from 'react';
import { View, ScrollView, StyleSheet, Dimensions, SafeAreaView, Text, Animated, ImageBackground, Image, TouchableOpacity, ActivityIndicator } from 'react-native';
import * as Font from 'expo-font';
import { StatusBar } from 'expo-status-bar';
import { FontFamily, Color, scale } from './GlobalStyles';
import CircularGauge from './components/CircularGauge';
import LightPanel from './components/LightPanel';
import ValueSlider from './components/ValueSlider';
import WateringPanel from './components/WateringPanel';
import ControlPanel from './components/ControlPanel';
import HistoryPanel from './components/HistoryPanel';
import ScreenNavigator from './components/ScreenNavigator';
import apiService from './services/apiService';

const { width, height } = Dimensions.get('window');
const cachedSettings = { target_temp: 25, target_hum: 60 };
// Responsive sizes optimized for 1024x600
const RESPONSIVE_SIZES = {
  circularGaugeSize: Math.round(210 * scale),        // 210px on 1024x600
  gridPaddingHorizontal: Math.round(40 * scale),     // 40px horizontal padding
  gridPaddingVertical: Math.round(40 * scale),       // 40px vertical padding
  gridGap: Math.round(28 * scale),                   // 28px gap between items
  borderRadius: Math.round(24 * scale),              // 24px border radius
  componentPadding: Math.round(12 * scale),          // 12px component internal padding
  screensaverSliderWidth: Math.round(320 * scale),   // 320px on 1024x600
  screensaverSliderHeight: Math.round(90 * scale),   // 90px on 1024x600
  topLeftMargin: Math.round(24 * scale),             // 24px top/left margin
};

export default function App() {
  const [fontsLoaded, setFontsLoaded] = useState(false);
  const [time, setTime] = useState(new Date());
  const [temperature, setTemperature] = useState(28);
  const [humidity, setHumidity] = useState(30);
  const [targetTemp, setTargetTemp] = useState(25);
  const [targetHumidity, setTargetHumidity] = useState(60);
  const [isScreenOn, setIsScreenOn] = useState(true);
  const [lightStatus, setLightStatus] = useState(false);
  const [lightIntensity, setLightIntensity] = useState(50);
  const [lightSchedule, setLightSchedule] = useState(null);
  const [manualMode, setManualMode] = useState(false);
  const [wateringInterval, setWateringInterval] = useState(null);
  const [currentScreen, setCurrentScreen] = useState(0);
  const [isSliderActive, setIsSliderActive] = useState(false);
  const [pairingStatus, setPairingStatus] = useState('idle'); // idle, loading, success, error
  const screenTimeoutRef = useRef(null);
  const SCREEN_TIMEOUT = 30000; // 30 sekund
  const sensorPollInterval = useRef(null);
  const wateringPollInterval = useRef(null);
  const [showLogModal, setShowLogModal] = React.useState(false);
  const [logs, setLogs] = React.useState([]);
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

 useEffect(() => {
  const loadSettings = async () => {
    try {
      const response = await fetch('/settings_config.json');
      if (!response.ok) {
        throw new Error('Failed to fetch settings');
      }
      const data = await response.json();
      cachedSettings.target_temp = data.target_temp || cachedSettings.target_temp;
      console.log('cachedSettings.target_temp updated:', cachedSettings.target_temp);
      cachedSettings.target_hum = data.target_hum || cachedSettings.target_hum;
      console.log('cachedSettings.target_hum updated:', cachedSettings.target_hum);
      setTargetTemp(cachedSettings.target_temp);
      setTargetHumidity(cachedSettings.target_hum);
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  };

  loadSettings();
}, []);
  const fetchSensors = async () => {
    const data = await apiService.getSensors();
    if (data.temperature !== null) setTemperature(data.temperature);
    if (data.humidity !== null) setHumidity(data.humidity);
  };

  const fetchStatus = async () => {
    const data = await apiService.getStatus();
    setLightStatus(data.light || false);
    setManualMode(data.manual_mode || false);
  };

  const fetchLightIntensity = async () => {
    try {
      const settings = await apiService.getSettings();
      setLightIntensity(settings.light_intensity || 50);
    } catch (error) {
      console.error('Error fetching light intensity:', error);
    }
  };

   const fetchSettings = async () => {
  try {
    const data = await apiService.getSettings();
    if (data.target_temp !== undefined && data.target_temp !== null) {
      setTargetTemp(data.target_temp);
    }
    if (data.target_hum !== undefined && data.target_hum !== null) {
      setTargetHumidity(data.target_hum);
    }
  } catch (error) {
    console.error('Error fetching settings from API:', error);
    // Fallback to cached settings only if the state is not already set
    setTargetTemp((prev) => prev || cachedSettings.target_temp);
    setTargetHumidity((prev) => prev || cachedSettings.target_hum);
  }
};
     
  const fetchWateringTimer = async () => {
    const data = await apiService.getWateringTimer();
    if (data && data.interval_seconds) {
      setWateringInterval(data.interval_seconds);
    }
  };


  // Wylicz harmonogram światła na podstawie settings
  const fetchLightSchedule = async () => {
    try {
      const settings = await apiService.getSettings();
      setLightSchedule({
        light_hours: settings.light_hours,
        start_hour: settings.start_hour,
        end_hour: settings.end_hour,
        start_minute: settings.start_minute || 0,
        end_minute: settings.end_minute || 0
      });
    } catch (error) {
      console.error('Error calculating light schedule:', error);
    }
  };

  // Pobieraj dane czujników co 2 sekundy
  useEffect(() => {
    // Początkowe pobranie
    fetchSensors();
    fetchStatus();
    fetchSettings();
    fetchLightIntensity();
    fetchWateringTimer();
    fetchLightSchedule();

    // Polling co 5 sekund
    sensorPollInterval.current = setInterval(() => {
      fetchSensors();
      fetchStatus();
      fetchLightIntensity();
    }, 5000);

    // Polling dla watering timera co 5 sekund (rzadsze)
    wateringPollInterval.current = setInterval(() => {
      fetchWateringTimer();
      fetchLightSchedule();
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
     // fetchSettings();
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
    // Nie wołaj resetScreenTimeout - to może spowodować pętlę
    if (screenTimeoutRef.current) {
      clearTimeout(screenTimeoutRef.current);
    }
    screenTimeoutRef.current = setTimeout(() => {
      sleepScreen();
    }, SCREEN_TIMEOUT);
  };

  const handleInteraction = () => {
    resetScreenTimeout();
  };

  const handleSliderStart = () => {
    setIsSliderActive(true);
  };

  const handleSliderEnd = () => {
    setIsSliderActive(false);
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


  const handleStartBluetooth = async () => {
    setPairingStatus('loading');
    setLogs([]); // Clear old logs
    setShowLogModal(true); // Open the popup
const eventSource = new EventSource(`${API_BASE_URL}/api/bluetooth-logs`);
eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setLogs((prevLogs) => [...prevLogs, data.message]);
};

eventSource.onerror = (err) => {
        console.error("EventSource failed:", err);
        eventSource.close();
    };    

try {
      const response = await apiService.startBluetooth();
      if (response.status === 'ok') {
        setPairingStatus('success');
        setTimeout(() => setPairingStatus('idle'), 3000);
      } else {
        setPairingStatus('error');
        setTimeout(() => setPairingStatus('idle'), 3000);
      }
    } catch (error) {
      setPairingStatus('error');
      setTimeout(() => setPairingStatus('idle'), 3000);
    }
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
          <View
            style={styles.screensaverContainer}
            onMouseMove={handleInteraction}
            onTouchMove={handleInteraction}
            onClick={handleInteraction}
          >
            <View style={styles.screensaverContent}>
              <Text style={styles.screensaverLabel}>Temperature</Text>
              <Text style={styles.screensaverValue}>{temperature.toFixed(1)}°C</Text>
              
              <Text style={styles.screensaverLabel}>Humidity</Text>
              <Text style={styles.screensaverValue}>{humidity.toFixed(0)}%</Text>
            </View>
          </View>
        ) : (
          <ImageBackground
            source={require('./assets/wallpaper.jpg')}
            style={styles.fullBackground}
            resizeMode="cover"
          >
            <ScreenNavigator
              currentScreen={currentScreen}
              onScreenChange={setCurrentScreen}
              isSliderActive={isSliderActive || currentScreen === 2} // blokuj gesty na HistoryPanel
              screens={[
                // Screen 0: Main Panel - 3x2 Grid
                <View
                  key="main"
                  style={styles.screenContainer}
                >
                  {/* Top Left Time and Date + Manual Mode */}
                  <View style={styles.topLeftTimeContainer}>
                    <View>
                      <Text style={styles.topLeftTime}>{formatTime()}</Text>
                      <Text style={styles.topLeftDate}>{formatDate()}</Text>
                    </View>
                    <Text style={[
                      styles.manualModeIndicator,
                      { color: manualMode ? '#FF9800' : '#666666' }
                    ]}>
                      MANUAL IS {manualMode ? 'ON' : 'OFF'}
                    </Text>
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
                      size={RESPONSIVE_SIZES.circularGaugeSize}
                    />
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
                      size={RESPONSIVE_SIZES.circularGaugeSize}
                    />
                  </View>

                  {/* Col 3: Current Temperature & Humidity */}
                  <View style={[styles.gridItemTall, { flex: 0.6, justifyContent: 'center', gap: 20 }]}>
                    <View style={{ alignItems: 'center' }}>
                      <Text style={styles.sensorLabel}>Temperature</Text>
                      <Text style={styles.sensorValue}>
                        {temperature.toFixed(1)}°C
                      </Text>
                    </View>
                    <View style={{ alignItems: 'center' }}>
                      <Text style={styles.sensorLabel}>Humidity</Text>
                      <Text style={styles.sensorValue}>
                        {humidity.toFixed(0)}%
                      </Text>
                    </View>
                  </View>
                </View>

                {/* ROW 2 - SHORT */}
                <View style={styles.rowWrapperShort}>
                  {/* Col 1: Light Intensity */}
                  <View style={styles.gridItemShort}>
                    <ValueSlider
                      name1="Intensity"
                      value={lightIntensity}
                      min={0}
                      max={100}
                      step={1}
                      unit="%"
                      onSliderStart={handleSliderStart}
                      onSliderEnd={handleSliderEnd}
                      onValueChange={(newIntensity) => {
                        setLightIntensity(newIntensity);
                        if (manualMode) {
                          // W manual mode wysyłaj bezpośrednio do control endpoint
                          apiService.toggleDevice('light', newIntensity);
                        } else {
                          // W auto mode ustawiaj settings
                          apiService.updateSettings({ light_intensity: newIntensity });
                        }
                      }}
                    />
                  </View>

                  {/* Col 2: Watering Info */}
                  <View style={styles.gridItemShort}>
                    <WateringPanel onSliderStart={handleSliderStart} onSliderEnd={handleSliderEnd} />
                  </View>

                  {/* Col 3: Pair Modules Button */}
                  <TouchableOpacity 
                    style={[
                      styles.gridItemShort,
                      { flex: 0.6 },
                      pairingStatus === 'loading' && styles.pairingButtonLoading,
                      pairingStatus === 'success' && styles.pairingButtonSuccess,
                      pairingStatus === 'error' && styles.pairingButtonError,
                    ]}
                    onPress={handleStartBluetooth}
                    activeOpacity={0.7}
                    disabled={pairingStatus === 'loading'}
                  >
                    {pairingStatus === 'loading' && (
                      <ActivityIndicator size={45} color="#ffffff" />
                    )}
                    {pairingStatus !== 'loading' && (
                      <Image 
                        source={require('./assets/bluetooth.png')} 
                        style={styles.bluetoothImage}
                      />
                    )}
                    <Text style={[
                      styles.pairModulesButtonText,
                      (pairingStatus === 'idle' || pairingStatus === 'success') && { color: '#4CAF50' },
                      pairingStatus === 'error' && styles.pairModulesButtonTextError,
                    ]}>
                      {pairingStatus === 'idle' && 'Pair'}
                      {pairingStatus === 'loading' && 'Pairing...'}
                      {pairingStatus === 'success' && 'OK'}
                      {pairingStatus === 'error' && 'Error'}
                    </Text>
                  </TouchableOpacity>
                 {/* --- LOG MODAL --- */}
{showLogModal && (
    <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Bluetooth Device Logs</Text>
            
            {/* Scrollable Log Area */}
            <ScrollView style={styles.logContainer}>
                {logs.map((log, index) => (
                    <Text key={index} style={styles.logText}>{log.trim()}</Text>
                ))}
            </ScrollView>

            {/* Close Button */}
            <TouchableOpacity 
                style={styles.closeButton} 
                onPress={() => {
                    setShowLogModal(false);
                    // Optional: You might want to stop the backend process here too
                }}
            >
                <Text style={styles.closeButtonText}>Close</Text>
            </TouchableOpacity>
        </View>
    </View>
)}
                </View>
              </View>
                </View>,
              // Screen 1: Control Panel
              <View
                key="control"
                style={styles.screenContainer}
                pointerEvents="box-none"
              >
                <View
                  style={styles.container}
                  pointerEvents="auto"
                >
                  <ControlPanel onSliderStart={handleSliderStart} onSliderEnd={handleSliderEnd} />
                </View>
              </View>,
              // Screen 2: History
              <View
                key="history"
                style={styles.screenContainer}
                pointerEvents="box-none"
              >
                <View
                  style={styles.container}
                  pointerEvents="auto"
                >
                  <HistoryPanel />
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
    paddingHorizontal: RESPONSIVE_SIZES.gridPaddingHorizontal,
    paddingVertical: RESPONSIVE_SIZES.gridPaddingVertical,
    gap: RESPONSIVE_SIZES.gridGap,
    justifyContent: 'space-between',
    marginTop: Math.round(50 * scale),  // Responsive margin for time/date area
  },
  rowWrapperTall: {
    flex: 1.2,
    flexDirection: 'row',
    gap: RESPONSIVE_SIZES.gridGap,
  },
  rowWrapperShort: {
    flex: 0.7,
    flexDirection: 'row',
    gap: RESPONSIVE_SIZES.gridGap,
  },
  gridItemTall: {
    flex: 1,
    backgroundColor: 'rgba(30, 30, 30, 0.7)',
    borderRadius: RESPONSIVE_SIZES.borderRadius,
    padding: RESPONSIVE_SIZES.componentPadding,
    justifyContent: 'center',
    alignItems: 'center',
    opacity: 0.7,
  },
  gridItemShort: {
    flex: 1,
    backgroundColor: 'rgba(30, 30, 30, 0.7)',
    borderRadius: RESPONSIVE_SIZES.borderRadius,
    padding: RESPONSIVE_SIZES.componentPadding,
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
  sensorLabel: {
    fontSize: 12,
    fontFamily: FontFamily.workSansRegular,
    color: '#888888',
    letterSpacing: 0.3,
    marginBottom: 4,
  },
  sensorValue: {
    fontSize: 36,
    fontFamily: FontFamily.workSansExtraLight,
    color: "#FFFFFF",
    letterSpacing: 0.5,
    fontWeight: '600',
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
    backgroundColor: '#000000',
  },
  screensaverContent: {
    alignItems: 'center',
    gap: 40,
  },
  screensaverLabel: {
    fontSize: 32,
    fontFamily: FontFamily.workSansLight,
    color: '#ffffff',
    letterSpacing: 1,
  },
  screensaverValue: {
    fontSize: 72,
    fontFamily: FontFamily.workSansLight,
    color: '#ffffff',
    letterSpacing: 2,
  },
  topLeftTimeContainer: {
    position: 'absolute',
    top: RESPONSIVE_SIZES.topLeftMargin,
    left: RESPONSIVE_SIZES.topLeftMargin,
    right: RESPONSIVE_SIZES.topLeftMargin,
    zIndex: 100,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
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
  lightScheduleText: {
    fontSize: 12,
    fontFamily: FontFamily.workSansMedium,
    color: '#e0e0e0',
    letterSpacing: 0.5,
    marginBottom: 8,
    textAlign: 'center',
  },
  bluetoothImage: {
    width: 50,
    height: 50,
    marginBottom: 6,
    resizeMode: 'contain',
    tintColor: '#ffffff',
  },
  pairModulesButtonText: {
    fontSize: 17,
    fontFamily: FontFamily.workSansLight,
    fontWeight: '600',
    textAlign: 'center',
  },
  pairModulesButtonTextSuccess: {
    color: '#4CAF50',
  },
  pairModulesButtonTextError: {
    color: '#FF6B6B',
  },
  pairingButtonLoading: {
    opacity: 2,
  },
  pairingButtonSuccess: {
    backgroundColor: 'rgba(76, 175, 80, 0.2)',
    borderWidth: 2,
    borderColor: '#4CAF50',
  },
  pairingButtonError: {
    backgroundColor: 'rgba(255, 107, 107, 0.2)',
    borderWidth: 2,
    borderColor: '#FF6B6B',
  },
modalOverlay: {
    position: 'absolute',
    top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.7)', // Semi-transparent black
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000, // Ensure it sits on top
  },
  modalContent: {
    width: '80%',
    height: '60%',
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 20,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#333',
    textAlign: 'center',
  },
  logContainer: {
    flex: 1,
    backgroundColor: '#1e1e1e', // Dark terminal-like background
    padding: 10,
    borderRadius: 5,
    marginBottom: 15,
  },
  logText: {
    color: '#00FF00', // Hacker green text
    fontFamily: 'monospace',
    fontSize: 12,
    marginBottom: 2,
  },
  closeButton: {
    backgroundColor: '#FF5252',
    padding: 10,
    borderRadius: 5,
    alignItems: 'center',
  },
  closeButtonText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 16,
  }
});
