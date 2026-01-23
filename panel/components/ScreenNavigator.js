import React, { useRef, useEffect, useMemo } from 'react';
import { View, Animated, PanResponder, Dimensions } from 'react-native';

const screenWidth = Dimensions.get('window').width;

const ScreenNavigator = ({ screens = [], currentScreen = 0, onScreenChange = () => {}, isSliderActive = false }) => {
  const xOffset = useRef(new Animated.Value(0)).current;
  const isSliderActiveRef = useRef(isSliderActive);
  const currentScreenRef = useRef(currentScreen);
  
  // Zsynchronizuj ref z prop
  useEffect(() => {
    isSliderActiveRef.current = isSliderActive;
  }, [isSliderActive]);

  // Zsynchronizuj ref z prop
  useEffect(() => {
    currentScreenRef.current = currentScreen;
  }, [currentScreen]);

  // Utwórz PanResponder za każdym razem gdy zmienia się currentScreen
  const panResponder = useMemo(() => {
    return PanResponder.create({
      onStartShouldSetPanResponder: () => false,
      onStartShouldSetPanResponderCapture: (evt, gestureState) => {
        if (isSliderActiveRef.current) return false;
        return Math.abs(gestureState.dx) > 10;
      },
      onMoveShouldSetPanResponder: () => false,
      onMoveShouldSetPanResponderCapture: (evt, gestureState) => {
        if (isSliderActiveRef.current) return false;
        const isHorizontalSwipe = Math.abs(gestureState.dx) > Math.abs(gestureState.dy) * 2;
        const isLargeMovement = Math.abs(gestureState.dx) > 5;
        return isHorizontalSwipe && isLargeMovement;
      },
      onPanResponderTerminationRequest: () => {
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
        let newScreen = currentScreenRef.current;

        if (gestureState.dx > swipeThreshold) {
          if (currentScreenRef.current > 0) {
            newScreen = currentScreenRef.current - 1;
          }
        } else if (gestureState.dx < -swipeThreshold) {
          if (currentScreenRef.current < screens.length - 1) {
            newScreen = currentScreenRef.current + 1;
          }
        }
        if (newScreen !== currentScreenRef.current) {
          Animated.spring(xOffset, {
            toValue: 0,
            useNativeDriver: true,
          }).start();
          onScreenChange(newScreen);
        } else {
          Animated.spring(xOffset, {
            toValue: 0,
            useNativeDriver: true,
          }).start();
        }
      },
    });
  }, [screens.length]);

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
