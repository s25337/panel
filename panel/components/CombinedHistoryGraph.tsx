import * as React from "react";
import { ScrollView, StyleSheet, Text, View, Dimensions } from "react-native";
import Svg, { Defs, Line, Polyline, Stop } from "react-native-svg";
import { Border, Color, FontFamily, FontSize, Padding } from "../GlobalStyles";

const screenWidth = Dimensions.get('window').width;

const Y_AXIS_WIDTH = 35;
const Y_LABEL_HEIGHT = 12;

// Calculate graph width for 48 data points with padding
// Total screen: 1024px, Container padding: 60px*2 = 120px, Tile padding: 20px*2 = 40px
// Y-axis: 35px, Available for SVG: 1024 - 120 - 40 - 35 = 829px
// For 48 points: 829 / 48 ≈ 17px per point
const GRAPH_WIDTH = screenWidth - 120; // Container padding 60*2
const TILE_PADDING = 40; // Tile padding 20*2
const AVAILABLE_WIDTH = GRAPH_WIDTH - TILE_PADDING - Y_AXIS_WIDTH; // ~829px (excluding Y-axis)
const X_STEP = Math.floor(AVAILABLE_WIDTH / 48); // ~17px per point
const GRAPH_HEIGHT = 300; // Tall graph to fill height
const GRAPH_PADDING = Padding.padding_12;

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

  // Fixed width for exactly 7 days visible at once (no scroll needed)
  const contentWidth = AVAILABLE_WIDTH;
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
              const bottom = GRAPH_HEIGHT - y - Y_LABEL_HEIGHT / 2;

              return (
                <Text key={`tick-${tick}`} style={[styles.axisTick, { bottom }]}>
                  {tick}%
                </Text>
              );
            })}
          </View>
        </View>

        <View style={styles.graphCanvas}>
          <View style={styles.graphScrollContent}>
            <View style={{ width: contentWidth }}>
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
            </View>

            {/* X-axis labels */}
            <View style={styles.xAxisLabels}>
              {xLabels.map((label, idx) => (
                <Text key={`label-${idx}`} style={styles.xAxisTick}>
                  {label}
                </Text>
              ))}
            </View>
          </View>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  graphCard: {
    width: "100%",
    flex: 1,
    borderRadius: Border.br_16,
    backgroundColor: "transparent",
    paddingHorizontal: Padding.padding_16,
    paddingVertical: Padding.padding_16,
    elevation: 0,
    rowGap: Padding.padding_12,
    display: "flex",
    flexDirection: "column",
  },
  graphHeader: {
    flexDirection: "row",
    rowGap: Padding.padding_12,
    marginBottom: Padding.padding_8,
  },
  graphTitle: {
    fontSize: FontSize.size_16_medium,
    fontFamily: FontFamily.workSansMedium,
    color: "#ffffff",
  },
  legend: {
    gap: Padding.padding_40,
    flexWrap: "wrap",
  },
  legendItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: Padding.padding_8,
  },
  legendDot: {
    width: 12,
    height: 12,
    borderRadius: 2,
  },
  legendLabel: {
    fontSize: 15,
    fontFamily: FontFamily.workSansLight,
    color: "#ffffff",
  },
  graphBody: {
    flex: 1,
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
    justifyContent: "center",
  },
  xAxisLabels: {
    flexDirection: "row",
    justifyContent: "space-around",
    marginTop: Padding.padding_8,
    width: AVAILABLE_WIDTH,
    paddingHorizontal: GRAPH_PADDING,
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
    flex: 1,
  },
});

export default CombinedHistoryGraph;
