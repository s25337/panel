import * as React from "react";
import { useMemo, memo, useState, useEffect } from "react";
import { Text, StyleSheet, View, GestureResponderEvent } from "react-native";
import {
  Width,
  Gap,
  FontSize,
  LetterSpacing,
  LineHeight,
  FontFamily,
  Color,
  Height,
  Border,
  Padding,
  ResponsiveSizes,
} from "../GlobalStyles";

export type ValueSliderType = {
  name1?: string;

  /** Initial or external value (number preferred, string tolerated) */
  value?: number | string;

  /** Range & step */
  min?: number;
  max?: number;
  step?: number;

  /** e.g. "%", "°C", "lx" */
  unit?: string;

  /** Custom formatter if you don't want default `${rounded}${unit}` */
  formatValue?: (value: number, unit?: string) => string;

  /** Style props */
  nameFontWeight?: string;
  nameFontFamily?: string;
  valueWidth?: number | string;

  /** Callback on value change (called on every move) */
  onValueChange?: (value: number) => void;

  /** Callback when sliding is complete (called only on release) */
  onSlidingComplete?: (value: number) => void;

  /** Lock swipe gestures when slider is active */
  onSliderStart?: () => void;
  onSliderEnd?: () => void;
};

const getStyleValue = (key: string, value: string | number | undefined) => {
  if (value === undefined) return;
  return { [key]: value === "unset" ? undefined : value };
};

// Safely convert to a number (handles "20°C", "55%", etc.)
const toNumeric = (raw: number | string | undefined, fallback: number) => {
  if (typeof raw === "number") {
    return Number.isNaN(raw) ? fallback : raw;
  }
  if (typeof raw === "string") {
    const cleaned = raw.replace(/[^0-9.\-]/g, "");
    const parsed = Number(cleaned);
    if (!Number.isNaN(parsed)) return parsed;
  }
  return fallback;
};

const applyStep = (value: number, min: number, step?: number) => {
  if (!step || step <= 0) return value;
  const steps = Math.round((value - min) / step);
  return min + steps * step;
};

const ValueSlider = memo(
  ({
    name1,
    nameFontWeight,
    nameFontFamily,
    value,
    valueWidth,
    min = 0,
    max = 100,
    step = 1,
    unit,
    formatValue,
    onValueChange,
    onSlidingComplete,
    onSliderStart,
    onSliderEnd,
  }: ValueSliderType) => {
    const nameStyle = useMemo(() => {
      return {
        ...getStyleValue("fontWeight", nameFontWeight),
        ...getStyleValue("fontFamily", nameFontFamily),
      };
    }, [nameFontWeight, nameFontFamily]);

    const valueStyle = useMemo(() => {
      return {
        ...getStyleValue("width", valueWidth),
      };
    }, [valueWidth]);

    const [trackWidth, setTrackWidth] = useState<number | null>(null);

    // internal slider state (always number)
    const [sliderValue, setSliderValue] = useState<number>(
      toNumeric(value, min)
    );

    // sync internal state when parent changes `value`
    useEffect(() => {
      setSliderValue(toNumeric(value, min));
    }, [value, min]);

    const progress =
      max === min
        ? 0
        : Math.min(1, Math.max(0, (sliderValue - min) / (max - min)));

    const displayValue = formatValue
      ? formatValue(sliderValue, unit)
      : `${Math.round(sliderValue)}${unit ?? ""}`;

    const handleMove = (e: GestureResponderEvent) => {
      if (!trackWidth) return;
      const x = e.nativeEvent.locationX;
      let ratio = x / trackWidth;
      ratio = Math.min(1, Math.max(0, ratio));
      let newVal = min + ratio * (max - min);
      newVal = applyStep(newVal, min, step);
      setSliderValue(newVal);
      onValueChange?.(newVal);
    };

    const handleResponderGrant = (e: GestureResponderEvent) => {
      onSliderStart?.();
      handleMove(e);
    };

    const handleResponderRelease = () => {
      onSliderEnd?.();
      onSlidingComplete?.(sliderValue);
    };

    return (
      <View style={styles.valueSlider}>
        <View
          style={styles.sliderTrack}
          onLayout={(e) => setTrackWidth(e.nativeEvent.layout.width)}
          onStartShouldSetResponder={() => true}
          onMoveShouldSetResponder={() => true}
          onResponderGrant={handleResponderGrant}
          onResponderMove={handleMove}
          onResponderRelease={handleResponderRelease}
        >
          <View
            style={[
              styles.sliderFill,
              trackWidth != null
                ? { width: `${progress * 100}%` } // procent szerokości track'a
                : { width: 0 },
            ]}
          />
          {/* Wartość na środku slidera */}
          <Text style={styles.sliderValue}>{displayValue}</Text>
        </View>
      </View>
    );
  }
);

const styles = StyleSheet.create({
  valueSlider: {
    width: Width.width_312,
    alignItems: "center",
    justifyContent: "center",
    gap: Gap.gap_8,
  },
  info: {
    alignSelf: "stretch",
    alignItems: "flex-start",
    justifyContent: "center",
  },
  nameParent: {
    alignSelf: "stretch",
    flexDirection: "row",
    alignItems: "flex-start",
    gap: Gap.gap_8,
  },
  name: {
    flex: 1,
    position: "relative",
    fontSize: FontSize.fs_12,
    letterSpacing: LetterSpacing.ls_0_1,
    lineHeight: LineHeight.lh_16,
    fontWeight: "500",
    fontFamily: FontFamily.workSansMedium,
    color: Color.textDark,
    textAlign: "left",
  },
  value: {
    height: Height.height_16,
    width: Width.width_32,
    position: "relative",
    fontSize: FontSize.fs_12,
    letterSpacing: LetterSpacing.ls_0_1,
    lineHeight: LineHeight.lh_16,
    fontFamily: FontFamily.workSansRegular,
    color: Color.textDark,
    textAlign: "right",
  },

  // Gray outer pill (krótszy i grubszy)
  sliderTrack: {
    width: ResponsiveSizes.sliderWidth,
    height: ResponsiveSizes.sliderHeight,
    borderRadius: ResponsiveSizes.sliderBorderRadius,
    backgroundColor: "#3a3a3a",
    overflow: "hidden",
    justifyContent: "center",
    alignItems: "center",
    position: "relative",
  },

  // Wartość na środku slidera
  sliderValue: {
    position: "absolute",
    fontSize: ResponsiveSizes.sliderFontSize,
    fontFamily: FontFamily.workSansMedium,
    color: "#FFFFFF", // biały tekst
    fontWeight: "500",
    zIndex: 10,
  },

  // Jasnożółty inner fill
  sliderFill: {
    position: "absolute",
    left: 0,
    top: 0,
    height: "100%",
    borderRadius: ResponsiveSizes.sliderBorderRadius,
    backgroundColor: Color.colorGoldenrod,
  },
});

export default ValueSlider;
