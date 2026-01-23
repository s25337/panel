import React, { useState, useEffect, useRef } from 'react';
import { View, ScrollView, Dimensions, SafeAreaView, Text, Animated, ImageBackground, Image, TouchableOpacity, ActivityIndicator } from 'react-native';
import * as Font from 'expo-font';
import { StatusBar } from 'expo-status-bar';
import { FontFamily, Color, scale } from './GlobalStyles';
import { styles, RESPONSIVE_SIZES } from './styles';
import CircularGauge from './components/CircularGauge';
import ValueSlider from './components/ValueSlider';
import WateringPanel from './components/WateringPanel';
import ControlPanel from './components/ControlPanel';
import ScreenNavigator from './components/ScreenNavigator';
import LogModal from './components/LogModal';
import apiService from './services/apiService';

const { width, height } = Dimensions.get('window');
const cachedSettings = { target_temp: 25, target_hum: 60, light_intensity: 50 };

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
    setManualMode(data.manual_mode || false);
  };

  const fetchLightIntensity = async () => {
    try {
      const settings = await apiService.getSettings();
      if (settings.light_intensity !== undefined && settings.light_intensity !== null) {
      setLightIntensity(settings.light_intensity);
    }
    } catch (error) {
      console.error('Error fetching light intensity:', error);
      setLightIntensity((prev) => prev || cachedSettings.light_intensity);
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
    setTargetTemp((prev) => prev || cachedSettings.target_temp);
    setTargetHumidity((prev) => prev || cachedSettings.target_hum);
  }
};
  const fetchWateringTimer = async () => {
    const data = await apiService.getWateringTimer();
    if (data && data.time_remaining !== undefined && data.time_remaining !== null) {
      setWateringInterval(data.time_remaining);
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
      fetchSettings();
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
    setShowLogModal(true);
  };

  const formatTime = () => {
    return time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (!fontsLoaded) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#000' }}>
        <Text style={{ color: '#fff', fontSize: 16 }}>Loading...</Text>
      </View>
    );
  }

  return (
    <ImageBackground
      source={require('./assets/wallpaper.png')}
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
              {/* Temperature with screensaver-heating image */}
              <View style={styles.screensaverImageContainer}>
                <Image 
                  source={require('./assets/screensaver-heating.png')} 
                  style={styles.screensaverImage}
                  resizeMode="contain"
                />
                <View style={styles.screensaverOverlay}>
                  <Text style={styles.screensaverValue}>{temperature.toFixed(1)}°C</Text>
                </View>
              </View>
              {/* Humidity with screensaver-humidity image */}
              <View style={styles.screensaverImageContainer}>
                <Image 
                  source={require('./assets/screensaver-humidity.png')} 
                  style={styles.screensaverImage}
                  resizeMode="contain"
                />
                <View style={styles.screensaverOverlay}>
                  <Text style={styles.screensaverValue}>{humidity.toFixed(0)}%</Text>
                </View>
              </View>
              {/* Watering days countdown with screensaver-watering image */}
              <View style={styles.screensaverImageContainer}>
                <Image 
                  source={require('./assets/screensaver-watering.png')} 
                  style={styles.screensaverImage}
                  resizeMode="contain"
                />
                <View style={styles.screensaverOverlay}>
                  <Text style={styles.screensaverValue}>
                    {wateringInterval ? Math.ceil(wateringInterval / 86400) : 0}
                  </Text>
                </View>
              </View>
            </View>
          </View>
        ) : (
          <ImageBackground
            source={require('./assets/wallpaper.png')}
            style={styles.fullBackground}
            resizeMode="cover"
          >
            <ScreenNavigator
              currentScreen={currentScreen}
              onScreenChange={setCurrentScreen}
              isSliderActive={isSliderActive}
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
                      onChangeComplete={(newHum) => {
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
                      }}
                      onChangeComplete={(newTemp) => {
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
                      }}
                      onSlidingComplete={(newIntensity) => {
                        if (manualMode) {
                          // W manual mode wysyłaj bezpośrednio do control endpoint
                          apiService.toggleDevice('light', newIntensity);
                        } else {
                          // W auto mode ustawiaj settings
                          apiService.updateSettings({ light_intensity: newIntensity/100 });
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
            ]}
            />
          </ImageBackground>
        )}
        </View>
      </SafeAreaView>
      <LogModal visible={showLogModal} onClose={() => setShowLogModal(false)} setPairingStatus={setPairingStatus} />
    </ImageBackground>
  );
}
