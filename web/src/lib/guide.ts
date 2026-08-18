/**
 * Answers for visitors, held locally.
 *
 * The real Co-Pilot calls a model through `copilot.ask`, which needs the operator's
 * control token and spends real money per question. Neither is appropriate for a
 * stranger who has just opened the page - but "read the dashboard and work it out"
 * is how you lose them in ten seconds.
 *
 * So this is a small, honest fallback: fixed answers to the questions people actually
 * ask first, matched on keywords, no network call and no cost. It says plainly that it
 * is canned rather than pretending to be the live agent.
 *
 * Every number here is stated in docs/results/EVALUATION.md. If those change, change
 * these - `guide.test.ts` checks the claims stay consistent with each other, but it
 * cannot know what the backtest printed.
 */

export interface GuideAnswer {
  /** Lowercase keywords; a question matching any of them selects this answer. */
  keywords: string[];
  /** Shown as a suggested question chip. Phrased the way a person would ask it. */
  question: string;
  answer: string;
  /** Optional view to send them to after answering. */
  goTo?: string;
}

export const GUIDE_INTRO =
  "I'm a small built-in guide, not the live AI co-pilot - I give fixed answers to " +
  "common questions so you can look around without needing a token. Ask me one of " +
  "these, or type your own.";

export const GUIDE_ANSWERS: GuideAnswer[] = [
  {
    question: "What am I looking at?",
    keywords: ["what is this", "what am i looking", "what does this do", "explain", "about"],
    answer:
      "A dashboard for a crypto trading bot that ran on its own. Once an hour it read " +
      "the market, decided whether to buy or sell, and signed its own transaction - no " +
      "human pressing a button.\n\n" +
      "The trading loop is switched off now, so what you see is the last state it " +
      "recorded rather than live movement. Start with Overview, then Pipeline to watch " +
      "one decision go through step by step.",
    goTo: "overview",
  },
  {
    question: "Did it make money?",
    keywords: ["make money", "made money", "profit", "returns", "pnl", "performance", "did it work"],
    answer:
      "No, and that is the honest headline.\n\n" +
      "It was tested across 40 setups - four strategies, five tokens, risk controls on " +
      "and off - over 540 days of real hourly prices with real trading costs charged. " +
      "All 40 lost money. Holding cash and doing nothing beat every single one.\n\n" +
      "It also traded real funds for a few days in June 2026: 4 trades, 44 cents lost, " +
      "almost all of it network fees. So the safety limits did their job - a strategy " +
      "with no edge cost 44 cents instead of the account.",
  },
  {
    question: "If it loses money, why publish it?",
    keywords: ["why publish", "why show", "point of", "why keep", "why bother"],
    answer:
      "Because the measuring was the hard part, and it works.\n\n" +
      "Three bugs were found in the backtest itself, and all three made the results " +
      "look better than reality. The worst one let the simulator credit money for " +
      "selling more than it owned - $46,814 of imaginary cash, which turned a losing " +
      "strategy into a reported +452% gain with almost no drawdown. Nothing failed; no " +
      "test went red.\n\n" +
      "A tool that measures your idea has to be more trustworthy than the idea. Finding " +
      "out mine was not, and fixing it, is the part worth showing.",
  },
  {
    question: "Where does the AI actually come in?",
    keywords: ["ai", "llm", "model", "claude", "language model", "agents", "machine learning"],
    answer:
      "Deliberately not in the trade decision. Buying and selling is plain Python that " +
      "returns the same answer for the same input - which is the only reason a backtest " +
      "means anything.\n\n" +
      "The model layer does four jobs, all of which can fail without stopping trading: " +
      "describe the market in words, reflect on a finished trade, check whether a " +
      "similar setup has lost before, and answer operator questions. It picks the " +
      "cheapest model that can do each job, caches repeats, and records what every call " +
      "cost. The Agents and Intel screens show that side.",
    goTo: "agents",
  },
  {
    question: "How did it keep the loss so small?",
    keywords: ["risk", "safe", "safety", "loss", "protect", "drawdown", "limits", "kill switch"],
    answer:
      "By holding cash unless a setup cleared its threshold, and capping everything else.\n\n" +
      "There is a kill switch that stops trading within one cycle, a floor that halts it " +
      "if the account drops too far, a cap on total exposure so a run of individually " +
      "legal buys cannot pile up, and a fixed list of five tokens it is allowed to touch " +
      "- the only five it was ever tested on.\n\n" +
      "In the backtest those controls cut the worst case from losing the whole account " +
      "to a few percent. They cannot create an edge, only limit the cost of not having " +
      "one. Controls shows the settings.",
    goTo: "controls",
  },
  {
    question: "Can I try it with my own money?",
    keywords: ["try it", "use it", "my money", "run it", "install", "my own", "can i trade"],
    answer:
      "You can run the code - it is open source, and paper mode needs no wallet at all. " +
      "But given every tested setup lost money, please do not point it at real funds.\n\n" +
      "Live trading needs you to supply your own wallet credentials and switch the mode " +
      "on deliberately. There is no shared token and nothing here can move anyone " +
      "else's money.",
  },
  {
    question: "Why can't I click anything?",
    keywords: [
      "cant click", "cannot click", "click anything", "nothing happens",
      "disabled", "read-only", "readonly", "greyed", "grayed", "control token", "pair",
    ],
    answer:
      "You are in read-only mode, which is the default for a visitor. Reading data " +
      "needs no permission; changing anything needs the operator's control token.\n\n" +
      "That token belongs to whoever runs their own copy - it is not shared, and it is " +
      "not in this page. It used to be hardcoded here so demo judges could tap once to " +
      "get control, which meant it was public to everyone. That has been removed.",
  },
  {
    question: "Where should I look first?",
    keywords: ["where", "look first", "start", "tour", "guide", "show me", "what should i"],
    answer:
      "Three screens, in this order:\n\n" +
      "1. Overview - account value and what the agent's stance was.\n" +
      "2. Pipeline - one decision end to end: the data it read, the gates it passed, " +
      "and which rule stopped it.\n" +
      "3. History - every trade it actually made. It is a short list.\n\n" +
      "Hover any icon in the left rail for a one-line description of that screen.",
    goTo: "pipeline",
  },
];

export const GUIDE_FALLBACK =
  "I only have fixed answers, so I don't have a good one for that. The live AI " +
  "co-pilot can answer freely, but it needs the operator's control token and spends " +
  "real credits per question, so it is off for visitors.\n\n" +
  "Try one of the suggested questions, or read the full write-up on GitHub - it covers " +
  "the results, the architecture, and the known weaknesses.";

/**
 * Fold a question down to something keywords can match.
 *
 * Two things break naive `includes`: apostrophes (a browser or phone keyboard may send
 * a curly ’ where the keyword has a straight ') and filler words wedged into the middle
 * of a phrase - "why can't I click anything" does not contain "can't click", because
 * there is an "I" in the way. So strip apostrophes and drop the filler.
 */
const FILLER = new Set([
  "i", "me", "my", "we", "you", "the", "a", "an", "is", "it", "this", "that",
  "do", "does", "did", "can", "could", "would", "should", "to", "of", "at",
  "on", "in", "for", "any", "some", "please", "just", "actually", "really",
]);

/** Lowercase, drop apostrophes and punctuation. Filler words are kept. */
function loose(input: string): string {
  return input
    .toLowerCase()
    .replace(/[’']/g, "")
    .replace(/[^a-z0-9\s-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** As `loose`, with filler words dropped so words wedged mid-phrase stop blocking. */
function tight(input: string): string {
  return loose(input)
    .split(" ")
    .filter((w) => w && !FILLER.has(w))
    .join(" ");
}

/**
 * Pick the best canned answer, or null when nothing matches well enough.
 *
 * Scoring is longest-keyword-wins, tried twice: once with filler intact, once with it
 * removed. The filler-free pass is what lets "why can't I click anything" reach the
 * "cant click" keyword - but it is only allowed for keywords that still carry two or
 * more real words afterwards. Without that floor, a keyword like "what does this do"
 * collapses to the single word "what" and swallows every unrelated question.
 */
export function matchGuideAnswer(input: string): GuideAnswer | null {
  if (!input.trim()) return null;
  const qLoose = loose(input);
  const qTight = tight(input);
  if (!qLoose) return null;

  let best: { entry: GuideAnswer; score: number } | null = null;
  for (const entry of GUIDE_ANSWERS) {
    if (qTight && qTight === tight(entry.question)) return entry;

    let score = 0;
    for (const kw of entry.keywords) {
      const kLoose = loose(kw);
      if (kLoose && qLoose.includes(kLoose)) score = Math.max(score, kLoose.length);

      const kTight = tight(kw);
      if (kTight.includes(" ") && qTight.includes(kTight)) {
        score = Math.max(score, kTight.length);
      }
    }
    if (score > 0 && (best === null || score > best.score)) best = { entry, score };
  }
  return best?.entry ?? null;
}
