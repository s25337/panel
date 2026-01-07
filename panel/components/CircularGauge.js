import React, { useRef, useState } from 'react';
import { View, StyleSheet, Text } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';

const CircularGauge = ({ value, maxValue, unit, label, color, size = 200, onValueChange }) => {
  const [isInteracting, setIsInteracting] = useState(false);
  const containerRef = useRef(null);

  const radius = (size - 30) / 2;
  const progress = (value / maxValue);
  
  // Create arc path
  const startAngle = -90;
  const endAngle = startAngle + (progress * 360);
  
  const startRad = (startAngle * Math.PI) / 180;
  const endRad = (endAngle * Math.PI) / 180;
  
  const x1 = size / 2 + radius * Math.cos(startRad);
  const y1 = size / 2 + radius * Math.sin(startRad);
  const x2 = size / 2 + radius * Math.cos(endRad);
  const y2 = size / 2 + radius * Math.sin(endRad);
  
  const largeArc = progress * 360 > 180 ? 1 : 0;
  const arcPath = `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`;

  const handleInteraction = (e) => {
    if (!containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect?.();
    if (!rect) return;

    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    
    const clientX = e.clientX !== undefined ? e.clientX : e.touches?.[0]?.clientX;
    const clientY = e.clientY !== undefined ? e.clientY : e.touches?.[0]?.clientY;

    if (clientX === undefined || clientY === undefined) return;

    const x = clientX - centerX;
    const y = clientY - centerY;

    // Oblicz kąt od środka
    let angle = Math.atan2(y, x) * (180 / Math.PI);
    
    // Konwertuj do zakresu 0-360
    angle = (angle + 90 + 360) % 360;

    // Clamp między 0 i 360
    angle = Math.max(0, Math.min(360, angle));

    const newProgress = angle / 360;
    const newValue = Math.round(newProgress * maxValue);

    if (onValueChange) {
      onValueChange(Math.max(0, Math.min(maxValue, newValue)));
    }
  };

  const handleMouseDown = (e) => {
    setIsInteracting(true);
    handleInteraction(e);
  };

  const handleTouchStart = (e) => {
    setIsInteracting(true);
    handleInteraction(e);
  };

  const handleMouseMove = (e) => {
    if (isInteracting) {
      handleInteraction(e);
    }
  };

  const handleTouchMove = (e) => {
    if (isInteracting) {
      handleInteraction(e);
    }
  };

  const handleMouseUp = () => {
    setIsInteracting(false);
  };

  const handleTouchEnd = () => {
    setIsInteracting(false);
  };

  React.useEffect(() => {
    if (isInteracting) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.addEventListener('touchmove', handleTouchMove);
      document.addEventListener('touchend', handleTouchEnd);

      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.removeEventListener('touchmove', handleTouchMove);
        document.removeEventListener('touchend', handleTouchEnd);
      };
    }
  }, [isInteracting]);

  return (
    <View
      ref={containerRef}
      style={[styles.container, { width: size, height: size }]}
      onMouseDown={handleMouseDown}
      onTouchStart={handleTouchStart}
    >
      <Svg 
        width={size} 
        height={size} 
        viewBox={`0 0 ${size} ${size}`}
        style={styles.svg}
        pointerEvents="none"
      >
        {/* Background circle */}
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="#333333"
          strokeWidth="6"
          fill="none"
        />
        
        {/* Progress arc */}
        <Path
          d={arcPath}
          stroke={color}
          strokeWidth="6"
          fill="none"
          strokeLinecap="round"
        />
      </Svg>
      
      {/* Value text - centered absolutely */}
      <View style={styles.textContainer}>
        <Text style={styles.value}>{value}</Text>
        <Text style={styles.unit}>{unit}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#252525',
    borderRadius: 16,
    overflow: 'hidden',
    position: 'relative',
    cursor: 'pointer',
  },
  svg: {
    position: 'absolute',
    top: 0,
    left: 0,
    pointerEvents: 'none',
  },
  textContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
    pointerEvents: 'none',
  },
  value: {
    fontSize: 42,
    fontWeight: '300',
    color: '#ffffff',
    letterSpacing: 1,
  },
  unit: {
    fontSize: 12,
    color: '#999999',
    marginTop: 2,
  },
});

export default CircularGauge;
