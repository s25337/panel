import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import Svg, { Defs, LinearGradient, Line, Path, Polyline, Stop } from 'react-native-svg';
import { Border, BoxShadow, Color, FontFamily, FontSize, Padding, Height, Width } from '../GlobalStyles';

const GRAPH_HEIGHT = Height.height_140;
const GRAPH_PADDING = Padding.padding_8;
const Y_AXIS_WIDTH = Width.width_22;
const Y_LABEL_HEIGHT = Height.height_12;
const X_STEP = Width.width_28;

const HistoryGraph = ({
  title,
  labels,
  series,
  yMin,
  yMax,
  yTicks,
  color = Color.lightGreen,
  disabled = false,
}) => {
  const [graphWidth, setGraphWidth] = React.useState(0);
  const labelsScrollRef = React.useRef(null);

  const contentWidth = Math.max(graphWidth, labels.length * X_STEP + X_STEP);

  const points = React.useMemo(() => {
    if (contentWidth <= 0 || series.length === 0) return [];
    const innerWidth = Math.max(1, contentWidth - GRAPH_PADDING * 2);
    const innerHeight = Math.max(1, GRAPH_HEIGHT - GRAPH_PADDING * 2);
    const range = yMax - yMin || 1;

    return series.map((value, index) => {
      const x = GRAPH_PADDING + innerWidth * (series.length === 1 ? 0 : index / (series.length - 1));
      const y = GRAPH_PADDING + innerHeight - ((value - yMin) / range) * innerHeight;
      return { x, y };
    });
  }, [contentWidth, series, yMin, yMax]);

  const polylinePoints = points.map((p) => `${p.x},${p.y}`).join(' ');

  const areaPath = React.useMemo(() => {
    if (points.length === 0) return '';
    const baseY = GRAPH_HEIGHT - GRAPH_PADDING;
    const first = points[0];
    const last = points[points.length - 1];
    const linePath = points.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
    return `${linePath} L ${last.x} ${baseY} L ${first.x} ${baseY} Z`;
  }, [points]);

  return (
    <View style={styles.graphCard}>
      <View style={styles.graphHeader}>
        <Text style={styles.graphTitle}>{title}</Text>
      </View>

      <View style={styles.graphBody}>
        <View style={styles.yAxis}>
          <View style={styles.yAxisScale}>
            {[...yTicks].reverse().map((tick, idx) => {
              const range = yMax - yMin || 1;
              const ratio = (tick - yMin) / range;
              const y = GRAPH_PADDING + (GRAPH_HEIGHT - GRAPH_PADDING * 2) * (1 - ratio);
              const top = Math.max(0, Math.min(GRAPH_HEIGHT - Y_LABEL_HEIGHT, y - Y_LABEL_HEIGHT));

              return (
                <Text key={`${title}-tick-${idx}`} style={[styles.axisTick, { top }]}>
                  {Math.round(tick)}
                </Text>
              );
            })}
          </View>
        </View>

        <View style={styles.graphCanvas} onLayout={(e) => setGraphWidth(e.nativeEvent.layout.width)}>
          <View style={styles.graphScrollContent}>
            <ScrollView
              horizontal
              nestedScrollEnabled
              showsHorizontalScrollIndicator={false}
              scrollEnabled={!disabled}
              contentContainerStyle={{ width: contentWidth }}
              keyboardShouldPersistTaps="handled"
              scrollEventThrottle={16}
              onScroll={(e) => {
                labelsScrollRef.current?.scrollTo({
                  x: e.nativeEvent.contentOffset.x,
                  animated: false,
                });
              }}
            >
              <Svg width={contentWidth} height={GRAPH_HEIGHT}>
                <Defs>
                  <LinearGradient id="graphFill" x1="0" y1="0" x2="0" y2="1">
                    <Stop offset="0" stopColor={color} stopOpacity="0.35" />
                    <Stop offset="1" stopColor={color} stopOpacity="0" />
                  </LinearGradient>
                </Defs>

                {yTicks.map((tick) => {
                  const range = yMax - yMin || 1;
                  const ratio = (tick - yMin) / range;
                  const y = GRAPH_PADDING + (GRAPH_HEIGHT - GRAPH_PADDING * 2) * (1 - ratio);
                  return (
                    <Line
                      key={`grid-${tick}`}
                      x1={GRAPH_PADDING}
                      y1={y}
                      x2={contentWidth - GRAPH_PADDING}
                      y2={y}
                      stroke="#E5E5E5"
                      strokeWidth={1}
                    />
                  );
                })}

                {areaPath.length > 0 && <Path d={areaPath} fill="url(#graphFill)" />}
                {polylinePoints.length > 0 && (
                  <Polyline points={polylinePoints} fill="none" stroke={color} strokeWidth={2} />
                )}
              </Svg>
            </ScrollView>

            <ScrollView
              ref={labelsScrollRef}
              horizontal
              nestedScrollEnabled
              showsHorizontalScrollIndicator={false}
              scrollEnabled={false}
              contentContainerStyle={{ width: contentWidth }}
            >
              <View style={styles.xAxisLabels}>
                {labels.map((label, idx) => (
                  <Text key={`${title}-label-${idx}`} style={styles.xAxisTick}>
                    {label}
                  </Text>
                ))}
              </View>
            </ScrollView>
          </View>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  graphCard: {
    width: '100%',
    minHeight: Height.height_220,
    borderRadius: Border.br_16,
    backgroundColor: Color.neutralLightLightest,
    paddingHorizontal: Padding.padding_16,
    paddingVertical: Padding.padding_16,
    boxShadow: BoxShadow.cardShadow,
    elevation: 6,
    rowGap: Padding.padding_8,
  },
  graphHeader: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
  },
  graphTitle: {
    fontSize: FontSize.fs_12,
    fontFamily: FontFamily.workSansMedium,
    color: Color.colorsLightModeStaticStatic900,
  },
  graphBody: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    width: '100%',
    justifyContent: 'center',
    columnGap: Padding.padding_4,
  },
  yAxis: { width: Y_AXIS_WIDTH, alignItems: 'center', justifyContent: 'flex-start' },
  yAxisScale: { width: '100%', height: GRAPH_HEIGHT, position: 'relative', alignItems: 'flex-end' },
  graphCanvas: { flex: 1, alignSelf: 'center', height: GRAPH_HEIGHT + Height.height_28 },
  graphScrollContent: { flex: 1, alignItems: 'center' },
  xAxisLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: Padding.padding_4,
    columnGap: Padding.padding_8,
    paddingHorizontal: Padding.padding_4,
    paddingRight: Padding.padding_12,
    width: '100%',
  },
  axisTick: {
    fontSize: FontSize.fs_10,
    fontFamily: FontFamily.workSansRegular,
    color: Color.colorDarkgray,
    textAlign: 'center',
    position: 'absolute',
    right: 0,
  },
  xAxisTick: {
    fontSize: FontSize.fs_10,
    fontFamily: FontFamily.workSansRegular,
    color: Color.colorDarkgray,
    textAlign: 'center',
  },
});

export default HistoryGraph;
