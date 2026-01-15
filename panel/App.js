import React, { useState, useEffect, useRef } from 'react';
import { View, StyleSheet, Dimensions, SafeAreaView, Text, Animated, ImageBackground, Image, TouchableOpacity, ActivityIndicator } from 'react-native';
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
import { styles, RESPONSIVE_SIZES } from './AppStyles';

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
  const [lightIntensity, setLightIntensity] = useState(50);
  const [currentScreen, setCurrentScreen] = useState(0);
  const [isSliderActive, setIsSliderActive] = useState(false);
  const [pairingStatus, setPairingStatus] = useState('idle'); // idle, loading, success, error
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
    const data = await apiService.getSettings();
    setTargetTemp(data.target_temp || 25);
    setTargetHumidity(data.target_hum || 60);
  };

  const fetchWateringTimer = async () => {
  };

  useEffect(() => {
    // Początkowe pobranie
    fetchSensors();
    fetchStatus();
    fetchSettings();
    fetchLightIntensity();
    fetchWateringTimer();

    // Polling co 10 sekund
    sensorPollInterval.current = setInterval(() => {
      fetchSensors();
      fetchStatus();
      fetchLightIntensity();
    }, 10000);

    // Polling dla watering timera co 60
    wateringPollInterval.current = setInterval(() => {
      fetchWateringTimer();
    }, 60000);

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
    // Nie wołaj resetScreenTimeout bo petla
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

  const handleLightIntensitySliderEnd = async () => {
    try {
      await apiService.updateSettings({ light_intensity: lightIntensity });
    } catch (error) {
      console.error('Error updating light intensity:', error);
    }
    handleSliderEnd();
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
                      }}
                      onSliderEnd={async () => {
                        try {
                          await apiService.updateSettings({ target_hum: targetHumidity });
                        } catch (error) {
                          console.error('Error updating target humidity:', error);
                        }
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
                      }}
                      onSliderEnd={async () => {
                        try {
                          await apiService.updateSettings({ target_temp: targetTemp });
                        } catch (error) {
                          console.error('Error updating target temperature:', error);
                        }
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
                      onSliderEnd={handleLightIntensitySliderEnd}
                      onValueChange={(newIntensity) => {
                        setLightIntensity(newIntensity);
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
