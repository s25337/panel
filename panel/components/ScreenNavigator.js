import React, { useRef, useState } from 'react';
import { View, Animated, PanResponder, Dimensions } from 'react-native';

const screenWidth = Dimensions.get('window').width;

const ScreenNavigator = ({ screens = [], onScreenChange = () => {}, isSliderActive = false }) => {
  const [currentScreen, setCurrentScreen] = useState(0);
  const xOffset = useRef(new Animated.Value(0)).current;
  const isSliderActiveRef = useRef(isSliderActive);
  
  // Zsynchronizuj ref z prop
  React.useEffect(() => {
    isSliderActiveRef.current = isSliderActive;
  }, [isSliderActive]);
  
  // Powiadom parent o zmianie ekranu
  React.useEffect(() => {
    onScreenChange(currentScreen);
  }, [currentScreen]);
  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: (evt, gestureState) => {
        // Jeśli slider aktywny, nie bierz kontroli na starcie
        if (isSliderActiveRef.current) return false;
        return Math.abs(gestureState.dx) > 10;
      },
      onMoveShouldSetPanResponder: (evt, gestureState) => {
        // Jeśli slider aktywny, nie bierz kontroli podczas ruchu
        if (isSliderActiveRef.current) return false;
        const isHorizontalSwipe = Math.abs(gestureState.dx) > Math.abs(gestureState.dy) * 2;
        const isLargeMovement = Math.abs(gestureState.dx) > 5;
        return isHorizontalSwipe && isLargeMovement;
      },
      onPanResponderTerminationRequest: () => {
        // Jeśli slider aktywny, oddaj mu kontrolę
        if (isSliderActiveRef.current) return true;
        return false;
      },
      onPanResponderMove: (evt, gestureState) => {
        if (Math.abs(gestureState.dx) > 5) {
          xOffset.setValue(gestureState.dx);
        }
      },
      onPanResponderRelease: (evt, gestureState) => {
        const swipeThreshold = screenWidth * 0.2;
        let newScreen = currentScreen;

        if (gestureState.dx > swipeThreshold) {
          if (currentScreen > 0) {
            newScreen = currentScreen - 1;
          }
        } else if (gestureState.dx < -swipeThreshold) {
          if (currentScreen < screens.length - 1) {
            newScreen = currentScreen + 1;
          }
        }

        setCurrentScreen(newScreen);

        Animated.spring(xOffset, {
          toValue: 0,
          useNativeDriver: false,
        }).start();
      },
    })
  ).current;

  return (
    <View style={{ flex: 1 }} {...panResponder.panHandlers}>
      <Animated.View
        style={[
          { flex: 1 },
          {
            transform: [{ translateX: xOffset }],
          },
        ]}
      >
        {screens[currentScreen]}
      </Animated.View>
    </View>
  );
};

export default ScreenNavigator;
