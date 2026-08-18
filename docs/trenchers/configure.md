Configuration

Spend limit: 0.2000 SOL
Unsaved

Per-trade size

How much SOL to spend on each buy.
0.500SOL

Min size

0.001

Max size

0.500

Buy slippage

Price movement tolerated when entering.
50.00%

Tight

0%

Loose

50%

Sell slippage

Price movement tolerated when exiting.
5.00%

Tight

0%

Loose

50%

Min holders

Require at least this many holders before buying.
50

Any

0

Strict

200
Take-profit & stops

Drag the rungs to set where the bot sells, and the floors where it cuts losses.

Each tier sells a percentage of the position when price reaches its multiple. Sum of percentages should be ≤ 100.
mult
sell %
slip (bps)
mult
sell %
slip (bps)
Sum: 150%
Stop-lossexit at this multiple of entry
×
Max-losshard floor below stop
×
Hard capforce-close ceiling
×

Advanced

Fine-grained gates and safety nets. Most traders can leave these as-is.

Min bonding-curve %

Skip tokens below this curve completion.
10%

Max bonding-curve %

Skip tokens past this curve completion.
40%

Min unique wallets

Require at least this many distinct buyers.

Min buy trades

Require this many recent buys before entry.

Min buy / sell ratio

2× = at least twice as many buys as sells.
×

Max dev holding %

Reject if the creator holds more than this.
10%

Max dev buy

Reject if the creator bought more than this.
1.500
1.500 SOL

Max top-10 holders %

Reject if the top 10 wallets hold over this. 0 = off.
25%

Single-wallet dominance

0.5 = reject if one wallet drives over 50% of trades.
×

Min trades to evaluate

Skip the wash check below this trade count.

Min buy time-spread

Reject if all early buys cluster in this window.
10s

Min buy-size variety

Lower = more uniform sizes (bot signal).
×

Min recent-buy ratio

Required share of recent buys.
×

Recent window (trades)

How many trades back 'recent' is measured.

Max first-window volume

0.5 = max 50% of volume in the first window.
×

First window length

Duration of the early-volume concentration check.
5s

Trailing activation

Trailing stop arms once price hits this multiple.
×

Trailing drawdown

0.2 = exit on a 20% pullback from the peak.
×

Curve-drop exit

Exit if the curve retreats this fraction from peak.
×

Near-completion exit %

Exit as the curve nears migration congestion.
95%

Hold timeout

Force exit after holding this long.
2m

No-volume timeout

Exit after this long with no volume on the mint.
30s

Stale min multiple

Below this multiple at timeout = exit.
×

Dev-dump tripwire %

Exit instantly if dev holdings drop over this %.
2%

Max open positions

Most positions the bot will hold at once.

Buy slippage ceiling

Upper limit, reached only when retrying.
40.00%

Buy retries

Attempts before giving up on a buy.

Sell retries

Attempts before giving up on a sell.

Priority fee

Slot-priority bid; the remainder is forwarded as a Jito tip.
0.000
0.000 SOL

Entry priority

High fires immediately; normal adds 0-200ms jitter.
