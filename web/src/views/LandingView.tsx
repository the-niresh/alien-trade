import { Button } from "@/components/ui/button";
import { ArrowRight, Bot, Eye, ShieldCheck } from "lucide-react";

/**
 * The first screen a stranger sees.
 *
 * It used to lead with "Track-1: live 7-day risk-adjusted PnL · TWAK self-custody ·
 * CMC x402 · BNB AI Agent SDK" and then a grid of twenty-odd control cards. Every
 * word of that is meaningful only if you already know the project, and the one action
 * a visitor could actually take - look around without a token - was a small underlined
 * link at the bottom.
 *
 * So: say what it is in one sentence, say what happened including the part that did
 * not work, and make "look around" the obvious button.
 */

const WHAT_IT_DOES = [
  {
    icon: Bot,
    title: "It decides on its own",
    body: "Once an hour it reads the market, decides whether to buy or sell, and signs its own transaction. Nobody presses a button.",
  },
  {
    icon: ShieldCheck,
    title: "The language model never places a trade",
    body: "Buy and sell decisions are plain Python that gives the same answer for the same input. The model only explains, reflects and answers questions.",
  },
  {
    icon: Eye,
    title: "Everything it did is on the record",
    body: "Each cycle is stored end to end: what it saw, what it decided, which safety rule stopped it. That is what these screens show.",
  },
];

export function LandingView({
  onConnect,
  onObserve,
}: {
  onConnect: () => void;
  onObserve?: () => void;
}) {
  return (
    <div className="min-h-screen bg-[#000] flex flex-col">
      <div className="flex flex-col items-center pt-20 pb-12 px-6 text-center">
        <img
          src="/logo.png"
          alt="Alien-Trade"
          className="w-24 h-24 rounded-full object-contain mb-5"
          style={{ mixBlendMode: "screen" }}
        />
        <h1
          className="font-display text-[44px] max-sm:text-[32px] font-bold text-green tracking-[0.12em] mb-4"
          style={{ textShadow: "0 0 40px rgba(74,222,128,0.4)" }}
        >
          ALIEN·TRADE
        </h1>

        <p className="text-[17px] max-sm:text-[15px] text-text/90 max-w-xl leading-relaxed mb-4">
          A crypto trading bot that runs itself - and the dashboard its operator watches
          it through.
        </p>

        {/* The honest headline. A visitor who reads only one thing should read this. */}
        <div className="max-w-xl w-full rounded-xl border border-yellow/25 bg-yellow/[0.06] px-5 py-4 mb-8 text-left">
          <p className="font-mono text-[10px] tracking-[0.18em] uppercase text-yellow mb-2">
            Before you look around
          </p>
          <p className="text-[13px] text-text/85 leading-relaxed">
            The engineering works. <span className="text-text font-semibold">The trading
            strategy does not.</span> Tested across 40 setups on 540 days of real prices,
            every one lost money - holding cash beat all of them. It traded real funds for
            a few days and lost 44 cents, almost all of it network fees.
          </p>
          <p className="text-[13px] text-muted-fg leading-relaxed mt-2">
            It is published as an engineering record, not as something to trade with. The
            trading loop is switched off, so these screens show the last state it recorded.
          </p>
        </div>

        <div className="flex items-center gap-3 max-sm:flex-col max-sm:w-full">
          {onObserve && (
            <Button
              className="bg-green text-[#04140c] font-bold text-[15px] px-7 py-3 h-auto hover:bg-green/80 cursor-pointer max-sm:w-full"
              onClick={onObserve}
            >
              Look around <ArrowRight className="w-4 h-4 ml-1.5" />
            </Button>
          )}
          <Button
            variant="outline"
            className="border-border bg-elevated text-text font-semibold text-[14px] px-6 py-3 h-auto hover:bg-border/40 cursor-pointer max-sm:w-full"
            onClick={onConnect}
          >
            I have a control token
          </Button>
        </div>
        <p className="font-mono text-[11px] text-muted-fg mt-3 max-w-sm leading-relaxed">
          Looking around needs nothing. The token is only for running your own copy, and
          it is yours alone - there is no shared demo token.
        </p>
      </div>

      {/* Three things, in plain words. */}
      <div className="max-w-4xl mx-auto px-6 pb-14 w-full">
        <div className="grid grid-cols-3 gap-4 max-md:grid-cols-1">
          {WHAT_IT_DOES.map(({ icon: Icon, title, body }) => (
            <div
              key={title}
              className="border border-border rounded-xl p-5 bg-elevated/40 flex flex-col gap-2.5"
            >
              <Icon className="w-5 h-5 text-cyan" />
              <h2 className="font-display text-[14px] font-bold text-text leading-snug">
                {title}
              </h2>
              <p className="text-[12.5px] text-muted-fg leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 pb-20 w-full text-center">
        <p className="text-[12px] text-muted-fg leading-relaxed">
          Source, the full result table, and a write-up of the three bugs that were
          inflating its own backtest:{" "}
          <a
            href="https://github.com/the-niresh/alien-trade"
            target="_blank"
            rel="noopener noreferrer"
            className="text-cyan hover:underline underline-offset-4"
          >
            github.com/the-niresh/alien-trade
          </a>
        </p>
      </div>
    </div>
  );
}
