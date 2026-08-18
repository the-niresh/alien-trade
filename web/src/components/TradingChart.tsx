import { useEffect, useRef } from "react";
import {
  createChart,
  createSeriesMarkers,
  ColorType,
  LineStyle,
  AreaSeries,
  type UTCTimestamp,
} from "lightweight-charts";

type PriceTick = { timestamp_ms: number; price: number };
type TradeMarker = { timestamp_ms: number; side: "buy" | "sell" };

type Props = {
  ticks: PriceTick[];
  trades?: TradeMarker[];
  height?: number;
};

export function TradingChart({ ticks, trades = [], height = 480 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || ticks.length < 2) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#5f7d96",
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(120,160,190,0.06)", style: LineStyle.Dotted },
        horzLines: { color: "rgba(120,160,190,0.06)", style: LineStyle.Dotted },
      },
      crosshair: {
        vertLine: { color: "rgba(52,255,174,0.3)", labelBackgroundColor: "#050508" },
        horzLine: { color: "rgba(52,255,174,0.3)", labelBackgroundColor: "#050508" },
      },
      timeScale: {
        borderColor: "rgba(120,160,190,0.12)",
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time: UTCTimestamp) => {
          const d = new Date(time * 1000);
          return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
        },
      },
      rightPriceScale: { borderColor: "rgba(120,160,190,0.12)" },
      width: containerRef.current.clientWidth,
      height,
      handleScroll: true,
      handleScale: true,
    });

    const areaSeries = chart.addSeries(AreaSeries, {
      lineColor: "#34ffae",
      topColor: "rgba(52,255,174,0.20)",
      bottomColor: "rgba(52,255,174,0.01)",
      lineWidth: 2,
    });

    // lightweight-charts requires strictly ascending integer seconds.
    // Ticks from Convex may overlap on restarts or share the same second.
    // 1. Sort ascending by raw timestamp_ms.
    // 2. Convert to seconds (handles both ms and already-seconds storage).
    // 3. Final monotonic filter: drop any point not strictly > previous second.
    const toSec = (ms: number) => ms > 1e10 ? Math.floor(ms / 1000) : Math.floor(ms);
    const sorted = [...ticks].sort((a, b) => a.timestamp_ms - b.timestamp_ms);
    const chartData: Array<{ time: UTCTimestamp; value: number }> = [];
    for (const t of sorted) {
      const sec = toSec(t.timestamp_ms) as UTCTimestamp;
      if (chartData.length === 0 || sec > chartData[chartData.length - 1].time) {
        chartData.push({ time: sec, value: t.price });
      } else if (sec === chartData[chartData.length - 1].time) {
        chartData[chartData.length - 1].value = t.price; // same second - keep latest
      }
      // sec < prev.time: skip (clock skew / restart artifact)
    }
    areaSeries.setData(chartData);

    if (trades.length > 0) {
      const sortedTrades = [...trades].sort((a, b) => a.timestamp_ms - b.timestamp_ms);
      createSeriesMarkers(
        areaSeries,
        sortedTrades.map((tr) => ({
          time: Math.floor(tr.timestamp_ms / 1000) as UTCTimestamp,
          position: tr.side === "buy" ? ("belowBar" as const) : ("aboveBar" as const),
          color: tr.side === "buy" ? "#34ffae" : "#ff2d6e",
          shape: tr.side === "buy" ? ("arrowUp" as const) : ("arrowDown" as const),
          text: tr.side === "buy" ? "B" : "S",
          size: 1,
        }))
      );
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [ticks, trades, height]);

  if (ticks.length < 2) {
    return (
      <div
        className="flex items-center justify-center font-mono text-[12px] text-muted-fg"
        style={{ height }}
      >
        Waiting for price data…
      </div>
    );
  }

  return <div ref={containerRef} className="w-full" style={{ height }} />;
}
