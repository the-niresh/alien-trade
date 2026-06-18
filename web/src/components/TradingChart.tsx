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

    const sorted = [...ticks].sort((a, b) => a.timestamp_ms - b.timestamp_ms);
    areaSeries.setData(
      sorted.map((t) => ({
        time: Math.floor(t.timestamp_ms / 1000) as UTCTimestamp,
        value: t.price,
      }))
    );

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
