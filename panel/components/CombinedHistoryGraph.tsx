import * as React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import Svg, { Defs, Line, Polyline, Stop } from "react-native-svg";
import { Border, Color, FontFamily, FontSize, Padding } from "../GlobalStyles";

const GRAPH_HEIGHT = 250;
const GRAPH_PADDING = Padding.padding_12;
const Y_AXIS_WIDTH = 30;
const Y_LABEL_HEIGHT = 12;
const X_STEP = 35;

type SeriesData = {
  label: string;
  data: number[];
  color: string;
};

type CombinedHistoryGraphProps = {
  xLabels: string[];  // Days of week: Sun, Mon, Tue, etc.
  series: SeriesData[];  // Multiple data series: temp, humidity, light
  title?: string;
};

const CombinedHistoryGraph = ({
  xLabels,
  series,
  title = "24h History",
}: CombinedHistoryGraphProps) => {
  const [graphWidth, setGraphWidth] = React.useState(0);
  const labelsScrollRef = React.useRef<ScrollView | null>(null);

  const contentWidth = Math.max(graphWidth, xLabels.length * X_STEP + X_STEP);
  const yMin = 0;
  const yMax = 100;
  const yTicks = [0, 25, 50, 75, 100];

  // Calculate points for all series
  const allPoints = React.useMemo(() => {
    if (contentWidth <= 0) return {};
    
    const innerWidth = Math.max(1, contentWidth - GRAPH_PADDING * 2);
    const innerHeight = Math.max(1, GRAPH_HEIGHT - GRAPH_PADDING * 2);
    const range = yMax - yMin || 1;

    const result: Record<string, Array<{ x: number; y: number }>> = {};

    series.forEach((s) => {
      result[s.label] = s.data.map((value, index) => {
        const x = GRAPH_PADDING + innerWidth * (s.data.length === 1 ? 0 : index / (s.data.length - 1));
        const y = GRAPH_PADDING + innerHeight - ((value - yMin) / range) * innerHeight;
        return { x, y };
      });
    });

    return result;
  }, [contentWidth, series, yMin, yMax]);

  return (
    <View style={styles.graphCard}>
      <View style={styles.graphHeader}>
        <Text style={styles.graphTitle}>{title}</Text>
        <View style={styles.legend}>
          {series.map((s) => (
            <View key={s.label} style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: s.color }]} />
              <Text style={styles.legendLabel}>{s.label}</Text>
            </View>
          ))}
        </View>
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
                <Text key={`tick-${tick}`} style={[styles.axisTick, { top }]}>
                  {tick}%
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
                  {series.map((s) => (
                    <Stop
                      key={`stop-${s.label}`}
                      offset="0"
                      stopColor={s.color}
                      stopOpacity="0.1"
                    />
                  ))}
                </Defs>

                {/* Grid lines */}
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
                      stroke="#333333"
                      strokeWidth={1}
                    />
                  );
                })}

                {/* Draw all series lines */}
                {series.map((s) => {
                  const points = allPoints[s.label];
                  if (!points || points.length === 0) return null;
                  
                  const polylinePoints = points.map((p) => `${p.x},${p.y}`).join(" ");
                  
                  return (
                    <Polyline
                      key={`line-${s.label}`}
                      points={polylinePoints}
                      fill="none"
                      stroke={s.color}
                      strokeWidth={2.5}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  );
                })}
              </Svg>
            </ScrollView>

            {/* X-axis labels */}
            <ScrollView
              ref={labelsScrollRef}
              horizontal
              nestedScrollEnabled
              showsHorizontalScrollIndicator={false}
              scrollEnabled={false}
              contentContainerStyle={{ width: contentWidth }}
            >
              <View style={styles.xAxisLabels}>
                {xLabels.map((label, idx) => (
                  <Text key={`label-${idx}`} style={styles.xAxisTick}>
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
    width: "100%",
    minHeight: 320,
    borderRadius: Border.br_16,
    backgroundColor: "rgba(0, 0, 0, 0.7)",
    paddingHorizontal: Padding.padding_16,
    paddingVertical: Padding.padding_16,
    elevation: 6,
    rowGap: Padding.padding_12,
  },
  graphHeader: {
    flexDirection: "column",
    rowGap: Padding.padding_8,
  },
  graphTitle: {
    fontSize: FontSize.size_16_medium,
    fontFamily: FontFamily.workSansMedium,
    color: "#ffffff",
  },
  legend: {
    flexDirection: "row",
    gap: Padding.padding_16,
    flexWrap: "wrap",
  },
  legendItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: Padding.padding_6,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 2,
  },
  legendLabel: {
    fontSize: FontSize.size_12_regular,
    fontFamily: FontFamily.workSansRegular,
    color: "#cccccc",
  },
  graphBody: {
    flexDirection: "row",
    alignItems: "flex-start",
    width: "100%",
    justifyContent: "center",
    columnGap: Padding.padding_8,
  },
  yAxis: {
    width: Y_AXIS_WIDTH,
    alignItems: "center",
    justifyContent: "flex-start",
  },
  yAxisScale: {
    width: "100%",
    height: GRAPH_HEIGHT,
    position: "relative",
    alignItems: "flex-end",
  },
  graphCanvas: {
    flex: 1,
    alignSelf: "center",
    height: GRAPH_HEIGHT + 40,
  },
  graphScrollContent: {
    flex: 1,
    alignItems: "center",
  },
  xAxisLabels: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: Padding.padding_8,
    columnGap: Padding.padding_8,
    paddingHorizontal: Padding.padding_4,
    paddingRight: Padding.padding_12,
    width: "100%",
  },
  axisTick: {
    fontSize: FontSize.size_11_regular,
    fontFamily: FontFamily.workSansRegular,
    color: "#888888",
    textAlign: "center",
    position: "absolute",
    right: 0,
  },
  xAxisTick: {
    fontSize: FontSize.size_11_regular,
    fontFamily: FontFamily.workSansRegular,
    color: "#888888",
    textAlign: "center",
    minWidth: X_STEP,
  },
});

export default CombinedHistoryGraph;
