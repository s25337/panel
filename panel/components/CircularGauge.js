import React, { useRef } from "react";
import { PanResponder, StyleSheet, Text, View } from "react-native";
import Svg, { Circle, G } from "react-native-svg";
import { Color, FontFamily, FontSize, Gap } from "../GlobalStyles";

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const normalizeDeg = (deg) => ((deg % 360) + 360) % 360;

const SWEEP_ANGLE = 265;
const START_ANGLE = 270 - SWEEP_ANGLE / 2;

function defaultsForMode(mode) {
  if (mode === "humidity") {
    return {
      label: "Humidity",
      unit: "%",
      min: 0,
      max: 100,
      step: 1,
      gradient: ["#5556A7", "#5556A7", "#44B89D"],
    };
  }
  return {
    label: "Temperature",
    unit: "°C",
    min: 0,
    max: 50,
    step: 1,
    gradient: ["#4A86E8", "#8A78C8", "#D06A6A"],
  };
}

/**
 * CircularGauge - Interactive circular slider component
 */
export default function CircularGauge({
  mode = "temperature",
  value,
  onValueChange,
  onChange,
  onChangeComplete,
  min,
  max,
  step,
  size = 120,
  strokeWidth = 6,
  label,
  unit,
  gradientColors,
  containerStyle,
  valueTextStyle,
  unitTextStyle,
  labelTextStyle,
  // Legacy props support
  maxValue,
  color,
  ...rest
}) {
  // Handle legacy props - priority: onChange > onValueChange > rest
  const onValueChangeFn = onChange || onValueChange || rest.onChange || rest.onValueChange;
  const onChangeCompleteFn = onChangeComplete || rest.onChangeComplete;
  
  if (maxValue !== undefined && !max) {
    max = maxValue;
  }

  const d = defaultsForMode(mode);
  const MIN = min ?? d.min;
  const MAX = max ?? d.max;
  const STEP = step ?? d.step;
  const LABEL = label ?? d.label;
  const UNIT = unit ?? d.unit;

  const [c0, c1, c2] = gradientColors ?? d.gradient;

  const cx = size / 2;
  const cy = size / 2;

  // space between arc and center circle
  const ringGap = Math.max(8, size * 0.08);  // Scale with size
  const innerSize = size * 0.6;  // Inner circle proportional to size
  const innerRadius = innerSize / 2;
  const r = innerRadius + ringGap + strokeWidth / 2;

  const circumference = 2 * Math.PI * r;
  const arcLen = (circumference * SWEEP_ANGLE) / 360;

  const clampedValue = clamp(value, MIN, MAX);
  const t = (clampedValue - MIN) / (MAX - MIN || 1);

  // touch only near the arc
  const ringHitSlop = Math.max(16, strokeWidth * 3.2);
  const isNearRing = (x, y) => {
    const dx = x - cx;
    const dy = y - cy;
    const dist = Math.sqrt(dx * dx + dy * dy);
    return Math.abs(dist - r) <= ringHitSlop;
  };

  const updateFromTouch = (x, y) => {
    if (!isNearRing(x, y)) return;

    const dx = x - cx;
    const dy = y - cy;

    let ang = (Math.atan2(dy, dx) * 180) / Math.PI;
    if (ang < 0) ang += 360;

    const rel = normalizeDeg(ang - START_ANGLE);
    const relClamped = Math.min(SWEEP_ANGLE, Math.max(0, rel));

    const next = MIN + (relClamped / SWEEP_ANGLE) * (MAX - MIN);
    const snapped = Math.round(next / STEP) * STEP;

    if (onValueChangeFn) {
      onValueChangeFn(clamp(snapped, MIN, MAX));
    }
    return clamp(snapped, MIN, MAX);
  };

  const lastValueRef = useRef(value);

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: (e) => {
        const newVal = updateFromTouch(e.nativeEvent.locationX, e.nativeEvent.locationY);
        if (newVal !== undefined) lastValueRef.current = newVal;
      },
      onPanResponderMove: (e) => {
        const newVal = updateFromTouch(e.nativeEvent.locationX, e.nativeEvent.locationY);
        if (newVal !== undefined) lastValueRef.current = newVal;
      },
      onPanResponderRelease: () => {
        if (onChangeCompleteFn && lastValueRef.current !== undefined) {
          onChangeCompleteFn(lastValueRef.current);
        }
      },
      onPanResponderTerminationRequest: () => false,
      onShouldBlockNativeResponder: () => true,
    })
  ).current;

  // segmented sweep gradient
  const SEGMENTS = 90;
  const segLen = arcLen / SEGMENTS;
  const trackDashArray = `${arcLen} ${circumference}`;

  return (
    <View
      style={[styles.container, { width: size, height: size }, containerStyle]}
      {...panResponder.panHandlers}
    >
      <Svg width={size} height={size}>
        <G rotation={START_ANGLE} origin={`${cx}, ${cy}`}>
          {/* Track */}
          <Circle
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke={Color.colorGainsboro}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={trackDashArray}
          />

          {/* Gradient progress (only up to current value) */}
          {(() => {
            const filled = Math.max(0, Math.min(SEGMENTS, Math.round(t * SEGMENTS)));
            return Array.from({ length: filled }).map((_, i) => {
              const p = i / Math.max(1, SEGMENTS - 1);
              const stroke = colorAt3Stops(p, c0, c1, c2);
              const dashOffset = -i * segLen;

              const isFirst = i === 0;
              const isLast = i === filled - 1;

              return (
                <Circle
                  key={i}
                  cx={cx}
                  cy={cy}
                  r={r}
                  fill="none"
                  stroke={stroke}
                  strokeWidth={strokeWidth}
                  strokeLinecap={isFirst || isLast ? "round" : "butt"}
                  strokeDasharray={`${segLen} ${circumference}`}
                  strokeDashoffset={dashOffset}
                />
              );
            });
          })()}
        </G>
      </Svg>

      <View style={styles.textWrap} pointerEvents="none">
        <Text style={[styles.value, valueTextStyle]}>{Math.round(clampedValue)}</Text>
        <Text style={[styles.unit, unitTextStyle]}>{UNIT}</Text>
        <Text style={[styles.label, labelTextStyle]}>{LABEL}</Text>
      </View>
    </View>
  );
}

/** p in [0,1] mapped across 3 hex colors */
function colorAt3Stops(p, a, b, c) {
  const t = Math.max(0, Math.min(1, p));
  if (t <= 0.55) return lerpHex(a, b, t / 0.55);
  return lerpHex(b, c, (t - 0.55) / (1 - 0.55));
}

function lerpHex(h1, h2, t) {
  const c1 = hexToRgb(h1);
  const c2 = hexToRgb(h2);
  const r = Math.round(c1.r + (c2.r - c1.r) * t);
  const g = Math.round(c1.g + (c2.g - c1.g) * t);
  const b = Math.round(c1.b + (c2.b - c1.b) * t);
  return `rgb(${r},${g},${b})`;
}

function hexToRgb(hex) {
  const h = hex.replace("#", "").trim();
  const full = h.length === 3 ? h.split("").map((x) => x + x).join("") : h;
  const n = parseInt(full, 16);
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
}

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    justifyContent: "center",
  },

  centerCard: {
    position: "absolute",
    backgroundColor: Color.neutralLightLightest,
    shadowColor: Color.textBlack,
    shadowOpacity: 0.12,
    shadowRadius: 13,
    shadowOffset: { width: 0, height: 0 },
    elevation: 6,
  },

  textWrap: {
    position: "absolute",
    alignItems: "center",
    justifyContent: "center",
  },

  value: {
    fontSize: 70,
    fontFamily: FontFamily.workSansExtraLight,
    color: "#FFFFFF",
    lineHeight: 70,
    includeFontPadding: false,
    marginTop: 20,
  },
  unit: {
    fontSize: 15,
    fontFamily: FontFamily.workSansLight,
    color: "#FFFFFF",
    lineHeight: 15,
    includeFontPadding: false,
    opacity: 0.5,
    marginTop: 8,
  },
  label: {
    fontSize: 14,
    fontFamily: FontFamily.workSansRegular,
    color: "#FFFFFF",
    lineHeight: 14,
    includeFontPadding: false,
    opacity: 0.5,
    marginTop: 15,
  },
});
