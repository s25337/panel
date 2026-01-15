import { StyleSheet } from 'react-native';
import { FontFamily, scale } from './GlobalStyles';

const RESPONSIVE_SIZES = {
  circularGaugeSize: Math.round(210 * scale),        // 210px on 1024x600
  gridPaddingHorizontal: Math.round(40 * scale),     // 40px horizontal padding
  gridPaddingVertical: Math.round(40 * scale),       // 40px vertical padding
  gridGap: Math.round(28 * scale),                   // 28px gap between items
  borderRadius: Math.round(24 * scale),              // 24px border radius
  componentPadding: Math.round(12 * scale),          // 12px component internal padding
  screensaverSliderWidth: Math.round(320 * scale),   // 320px on 1024x600
  screensaverSliderHeight: Math.round(90 * scale),   // 90px on 1024x600
  topLeftMargin: Math.round(24 * scale),             // 24px top/left margin
};

const styles = StyleSheet.create({
  fullBackground: {
    flex: 1,
    width: '100%',
    height: '100%',
  },
  screenContainer: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  container: {
    flex: 1,
    backgroundColor: 'transparent',
    fontFamily: FontFamily.workSansRegular,
  },
  contentWrapper: {
    flex: 1,
  },
  backgroundImage: {
    resizeMode: 'cover',
    flex: 1,
  },
  mainGrid: {
    flex: 1,
    flexDirection: 'column',
    paddingHorizontal: RESPONSIVE_SIZES.gridPaddingHorizontal,
    paddingVertical: RESPONSIVE_SIZES.gridPaddingVertical,
    gap: RESPONSIVE_SIZES.gridGap,
    justifyContent: 'space-between',
    marginTop: Math.round(50 * scale),  // Responsive margin for time/date area
  },
  rowWrapperTall: {
    flex: 1.2,
    flexDirection: 'row',
    gap: RESPONSIVE_SIZES.gridGap,
  },
  rowWrapperShort: {
    flex: 0.7,
    flexDirection: 'row',
    gap: RESPONSIVE_SIZES.gridGap,
  },
  gridItemTall: {
    flex: 1,
    backgroundColor: 'rgba(30, 30, 30, 0.7)',
    borderRadius: RESPONSIVE_SIZES.borderRadius,
    padding: RESPONSIVE_SIZES.componentPadding,
    justifyContent: 'center',
    alignItems: 'center',
    opacity: 0.7,
  },
  gridItemShort: {
    flex: 1,
    backgroundColor: 'rgba(30, 30, 30, 0.7)',
    borderRadius: RESPONSIVE_SIZES.borderRadius,
    padding: RESPONSIVE_SIZES.componentPadding,
    justifyContent: 'center',
    alignItems: 'center',
    opacity: 0.7,
  },
  gridLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#aaaaaa',
    marginBottom: 8,
    letterSpacing: 0.5,
  },
  currentValue: {
    fontSize: 18,
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  currentLabel: {
    fontSize: 12,
    color: '#888888',
    letterSpacing: 0.3,
  },
  currentValueContainer: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginTop: -20,
    justifyContent: 'center',
  },
  sensorLabel: {
    fontSize: 12,
    fontFamily: FontFamily.workSansRegular,
    color: '#888888',
    letterSpacing: 0.3,
    marginBottom: 4,
  },
  sensorValue: {
    fontSize: 36,
    fontFamily: FontFamily.workSansExtraLight,
    color: "#FFFFFF",
    letterSpacing: 0.5,
    fontWeight: '600',
  },
  headerBox: {
    justifyContent: 'center',
    alignItems: 'center',
    flex: 1,
  },
  leftColumn: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  rightColumn: {
    flex: 0.75,
    flexDirection: 'column',
    justifyContent: 'space-between',
    gap: 16,
  },
  leftColumnSmall: {
    flex: 0.5,
    justifyContent: 'flex-start',
    alignItems: 'stretch',
    paddingTop: 10,
  },
  rightColumnLarge: {
    flex: 1.5,
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
  },
  panelsColumn: {
    flex: 1,
    justifyContent: 'space-between',
    gap: 16,
  },
  gaugesColumn: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 40,
    alignItems: 'center',
  },
  sensorValues: {
    alignItems: 'center',
    marginBottom: 20,
  },
  screensaverContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#000000',
  },
  screensaverContent: {
    alignItems: 'center',
    gap: 40,
  },
  screensaverLabel: {
    fontSize: 32,
    fontFamily: FontFamily.workSansLight,
    color: '#ffffff',
    letterSpacing: 1,
  },
  screensaverValue: {
    fontSize: 72,
    fontFamily: FontFamily.workSansLight,
    color: '#ffffff',
    letterSpacing: 2,
  },
  topLeftTimeContainer: {
    position: 'absolute',
    top: RESPONSIVE_SIZES.topLeftMargin,
    left: RESPONSIVE_SIZES.topLeftMargin,
    right: RESPONSIVE_SIZES.topLeftMargin,
    zIndex: 100,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 16,
  },
  topLeftTime: {
    fontSize: 20,
    fontFamily: FontFamily.workSansLight,
    color: '#ffffff',
    letterSpacing: 1,
  },
  topLeftDate: {
    fontSize: 20,
    fontFamily: FontFamily.workSansLight,
    color: '#ffffff',
    letterSpacing: 0.5,
  },
  bluetoothImage: {
    width: 50,
    height: 50,
    marginBottom: 6,
    resizeMode: 'contain',
    tintColor: '#ffffff',
  },
  pairModulesButtonText: {
    fontSize: 17,
    fontFamily: FontFamily.workSansLight,
    fontWeight: '600',
    textAlign: 'center',
  },
  pairModulesButtonTextSuccess: {
    color: '#4CAF50',
  },
  pairModulesButtonTextError: {
    color: '#FF6B6B',
  },
  pairingButtonLoading: {
    opacity: 2,
  },
  pairingButtonSuccess: {
    backgroundColor: 'rgba(76, 175, 80, 0.2)',
    borderWidth: 2,
    borderColor: '#4CAF50',
  },
  pairingButtonError: {
    backgroundColor: 'rgba(255, 107, 107, 0.2)',
    borderWidth: 2,
    borderColor: '#FF6B6B',
  },
});

export { styles, RESPONSIVE_SIZES };