// GlobalStyles.js - Dark Theme
import { StyleSheet, Dimensions } from "react-native";

// Responsive scaling for 1024x600 resolution
const { width, height } = Dimensions.get('window');
const DESIGN_WIDTH = 1024;
const DESIGN_HEIGHT = 600;
export const scale = Math.min(width / DESIGN_WIDTH, height / DESIGN_HEIGHT);

/* Responsive component sizes optimized for 1024x600 */
export const ResponsiveSizes = {
  sliderWidth: Math.round(280 * scale),         // 280px on 1024x600
  sliderHeight: Math.round(60 * scale),         // 60px on 1024x600
  sliderBorderRadius: Math.round(30 * scale),   // 30px border radius
  sliderFontSize: Math.round(13 * scale),       // 13px font on slider
};

/* Fonts */
export const FontFamily = {
  workSansMedium: "WorkSans-Medium",
  workSansRegular: "WorkSans-Regular",
  workSansLight: "WorkSans-Light",
  workSansExtraLight: "WorkSans-ExtraLight",
};

/* Font sizes */
export const FontSize = {
  fs_10: 10,
  fs_12: 12,
  fs_14: 14,
  fs_16: 16,
  fs_20: 20,
  fs_24: 24,
  fs_72: 72,
};

/* Colors - Dark Theme */
export const Color = {
  // Grays - Dark Mode
  colorDarkgray: "#989898",
  colorMidgray: "#7A7A7A",
  
  // Accent colors
  colorDarkgreen: "#216607",
  colorDarkseagreen: "rgba(126, 166, 111, 0.51)",
  colorDanger: "#d64045",
  colorGoldenrod: "#f6ae41",
  colorLightskyblue: "#65b5e1",
  lightGreen: "#7ea66f",
  
  // Neutral - Dark Mode
  colorGainsboro: "#333333",
  colorLavender: "#2a2a3e",
  lightGrey: "#1a1a1a",
  neutralLightLightest: "#ffffff",
  neutralDarkDarkest: "#0a0a0a",
  neutralDarkLight: "#303030",
  
  // Text
  textBlack: "#ffffff",
  textDark: "#e0e0e0",
  textUnchecked: "#606060",
  highlightDarkest: "#006ffd",
};

/* Gaps */
export const Gap = {
  gap_2: 2,
  gap_4: 4,
  gap_6: 6,
  gap_8: 8,
  gap_10: 10,
  gap_12: 12,
  gap_16: 16,
  gap_20: 20,
  gap_24: 24,
  gap_32: 32,
};

/* Paddings */
export const Padding = {
  padding_0: 0,
  padding_2: 2,
  padding_3: 3,
  padding_4: 4,
  padding_6: 6,
  padding_8: 8,
  padding_10: 10,
  padding_12: 12,
  padding_13: 13,
  padding_14: 14,
  padding_16: 16,
  padding_22: 22,
  padding_23: 23,
  padding_24: 24,
  padding_36: 36,
  padding_48: 48,
};

/* Border Radiuses */
export const Border = {
  br_2: 2,
  br_8: 8,
  br_12: 12,
  br_14: 14,
  br_16: 16,
  br_20: 20,
  br_22: 22,
  br_24: 24,
  br_26: 26,
  br_32: 32,
};

/* Box Shadows */
export const BoxShadow = {
  cardShadow: "0px 0px 13px 1px rgba(0, 0, 0, 0.3)",
  cardShadowActive: "0px 0px 16px 2px rgba(33, 102, 7, 0.35)",
};

/* Width */
export const Width = {
  width_8: 8,
  width_12: 12,
  width_14: 14,
  width_16: 16,
  width_18: 18,
  width_20: 20,
  width_21: 21,
  width_22: 22,
  width_24: 24,
  width_25: 25,
  width_28: 28,
  width_30: 30,
  width_32: 32,
  width_36: 36,
  width_38: 38,
  width_40: 40,
  width_42: 42,
  width_43: 43,
  width_47: 47,
  width_48: 48,
  width_49: 49,
  width_50: 50,
  width_51: 51,
  width_52: 52,
  width_56: 56,
  width_60: 60,
  width_63: 63,
  width_64: 64,
  width_70: 70,
  width_72: 72,
  width_80: 80,
  width_85: 85,
  width_90: 90,
  width_128: 128,
  width_121: 121,
  width_268: 268,
  width_312: 312,
  width_360: 360,
  width_55: 55,
};

/* Height */
export const Height = {
  height_4: 4,
  height_8: 8,
  height_12: 12,
  height_14: 14,
  height_15: 15,
  height_16: 16,
  height_18: 18,
  height_20: 20,
  height_21: 21,
  height_22: 22,
  height_23_57: 23.57,
  height_24: 24,
  height_28: 28,
  height_30: 30,
  height_36: 36,
  height_38: 38,
  height_40: 40,
  height_42: 42,
  height_43: 43,
  height_47: 47,
  height_51: 51,
  height_52: 52,
  height_56: 56,
  height_62: 62,
  height_64: 64,
  height_72: 72,
  height_74: 74,
  height_80: 80,
  height_97: 97,
  height_120: 120,
  height_140: 140,
  height_148: 148,
  height_220: 220,
  height_240: 240,
  height_242: 242,
  height_800: 800,
};

/* Max Width */
export const MaxWidth = {
  max_w_360: 360,
};

/* Line Height */
export const LineHeight = {
  lh_12: 12,
  lh_16: 16,
  lh_20: 20,
  lh_22: 22,
  lh_24: 24,
  lh_32: 32,
};

/* Letter Spacing */
export const LetterSpacing = {
  ls_0_1: 0.1,
  ls_0_2: 0.2,
  ls_0_5: 0.5,
  ls_1: 1,
};

/* Header */
export const Header = {
  paddingHorizontal: Padding.padding_24,
  paddingTop: Padding.padding_8,
  paddingBottom: Padding.padding_16,
  titleSize: FontSize.fs_24,
  titleLetterSpacing: LetterSpacing.ls_1,
  titleFontFamily: FontFamily.workSansMedium,
};
