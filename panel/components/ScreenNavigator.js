import React, { useRef, useState } from 'react';
import { View, Animated, PanResponder, Dimensions } from 'react-native';

const screenWidth = Dimensions.get('window').width;

const ScreenNavigator = ({ screens = [], onScreenChange = () => {} }) => {
  const [currentScreen, setCurrentScreen] = useState(0);
  const xOffset = useRef(new Animated.Value(0)).current;
  
  // Powiadom parent o zmianie ekranu
  React.useEffect(() => {
    onScreenChange(currentScreen);
  }, [currentScreen]);
  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => false,
      onMoveShouldSetPanResponder: (evt, gestureState) => {
        // Tylko pan-y w kierunku horyzontalnym (swipe), ignoruj pionowe
        return Math.abs(gestureState.dx) > Math.abs(gestureState.dy) && Math.abs(gestureState.dx) > 10;
      },
      onPanResponderMove: (evt, gestureState) => {
        xOffset.setValue(gestureState.dx);
      },
      onPanResponderRelease: (evt, gestureState) => {
        const swipeThreshold = screenWidth * 0.5;

        let newScreen = currentScreen;

        if (gestureState.dx > swipeThreshold) {
          // Swipe right - go to previous screen (back)
          if (currentScreen > 0) {
            newScreen = currentScreen - 1;
          }
        } else if (gestureState.dx < -swipeThreshold) {
          // Swipe left - go to next screen (forward)
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
