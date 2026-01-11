import React, { useRef } from "react";
import { PanResponder, StyleSheet, Text, View, ViewStyle, TextStyle } from "react-native";
import Svg, { Circle, G } from "react-native-svg";
import { Color, FontFamily, FontSize, Gap } from "../GlobalStyles";

type Mode = "temperature" | "humidity";

type Props = {
  mode: Mode;
  value: number;
  onChange: (v: number) => void;

  min?: number;
  max?: number;
  step?: number;

  size?: number;
  strokeWidth?: number;

  label?: string;
  unit?: string;

  /** 3-stop gradient around the arc (sweep-like). */
  gradientColors?: [string, string, string];

  containerStyle?: ViewStyle;
  valueTextStyle?: TextStyle;
  unitTextStyle?: TextStyle;
  labelTextStyle?: TextStyle;
};

const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));
const normalizeDeg = (deg: number) => ((deg % 360) + 360) % 360;

// Your current tuning
const SWEEP_ANGLE = 265;
const START_ANGLE = 270 - SWEEP_ANGLE / 2;

function defaultsForMode(mode: Mode) {
  if (mode === "humidity") {
    return {
      label: "Humidity",
      unit: "%",
      min: 0,
      max: 100,
      step: 1,
      gradient: ["#4A86E8", "#61b0ddff", "#3ec6b8ff"] as [string, string, string],
    };
  }
  return {
    label: "Temperature",
    unit: "°C",
    min: 0,
    max: 50,
    step: 1,
    gradient: ["#4A86E8", "#8A78C8", "#D06A6A"] as [string, string, string],
  };
}

export default function CirclePicker({
  mode,
  value,
  onChange,
  min,
  max,
  step,
  size = 280,
  strokeWidth = 6,
  label,
  unit,
  gradientColors,
  containerStyle,
  valueTextStyle,
  unitTextStyle,
  labelTextStyle,
}: Props) {
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
  const ringGap = 14;
  const innerSize = 215;
  const innerRadius = innerSize / 2;
  const r = innerRadius + ringGap + strokeWidth / 2;

  const circumference = 2 * Math.PI * r;
  const arcLen = (circumference * SWEEP_ANGLE) / 360;

  const clampedValue = clamp(value, MIN, MAX);
  const t = (clampedValue - MIN) / (MAX - MIN || 1);

  // touch only near the arc
  const ringHitSlop = Math.max(16, strokeWidth * 3.2);
  const isNearRing = (x: number, y: number) => {
    const dx = x - cx;
    const dy = y - cy;
    const dist = Math.sqrt(dx * dx + dy * dy);
    return Math.abs(dist - r) <= ringHitSlop;
  };

  const updateFromTouch = (x: number, y: number) => {
    if (!isNearRing(x, y)) return;

    const dx = x - cx;
    const dy = y - cy;

    let ang = (Math.atan2(dy, dx) * 180) / Math.PI;
    if (ang < 0) ang += 360;

    const rel = normalizeDeg(ang - START_ANGLE);
    const relClamped = Math.min(SWEEP_ANGLE, Math.max(0, rel));

    const next = MIN + (relClamped / SWEEP_ANGLE) * (MAX - MIN);
    const snapped = Math.round(next / STEP) * STEP;

    onChange(clamp(snapped, MIN, MAX));
  };

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: (e) =>
        updateFromTouch(e.nativeEvent.locationX, e.nativeEvent.locationY),
      onPanResponderMove: (e) =>
        updateFromTouch(e.nativeEvent.locationX, e.nativeEvent.locationY),
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

      {/* center white circle with shadow */}
      <View
        pointerEvents="none"
        style={[
          styles.centerCard,
          {
            width: innerSize,
            height: innerSize,
            borderRadius: innerSize / 2,
          },
        ]}
      />

      <View style={styles.textWrap} pointerEvents="none">
        <Text style={[styles.value, valueTextStyle]}>{Math.round(clampedValue)}</Text>
        <Text style={[styles.unit, unitTextStyle]}>{unit ?? UNIT}</Text>
        <Text style={[styles.label, labelTextStyle]}>{label ?? LABEL}</Text>
      </View>
    </View>
  );
}

/** p in [0,1] mapped across 3 hex colors */
function colorAt3Stops(p: number, a: string, b: string, c: string) {
  const t = Math.max(0, Math.min(1, p));
  if (t <= 0.55) return lerpHex(a, b, t / 0.55);
  return lerpHex(b, c, (t - 0.55) / (1 - 0.55));
}

function lerpHex(h1: string, h2: string, t: number) {
  const c1 = hexToRgb(h1);
  const c2 = hexToRgb(h2);
  const r = Math.round(c1.r + (c2.r - c1.r) * t);
  const g = Math.round(c1.g + (c2.g - c1.g) * t);
  const b = Math.round(c1.b + (c2.b - c1.b) * t);
  return `rgb(${r},${g},${b})`;
}

function hexToRgb(hex: string) {
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
    gap: Gap.gap_6,
  },

  value: {
    fontSize: FontSize.fs_72,
    fontFamily: FontFamily.workSansExtraLight,
    color: Color.textBlack,
    lineHeight: FontSize.fs_72,
    includeFontPadding: false,
  },
  unit: {
    fontSize: FontSize.fs_16,
    fontFamily: FontFamily.workSansLight,
    color: Color.colorDarkgray,
    lineHeight: FontSize.fs_16,
    includeFontPadding: false,
  },
  label: {
    fontSize: FontSize.fs_12,
    fontFamily: FontFamily.workSansRegular,
    color: Color.colorDarkgray,
    lineHeight: FontSize.fs_12,
    includeFontPadding: false,
  },
});