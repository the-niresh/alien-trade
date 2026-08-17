dorahacks website: 
BNB Hack: AI Trading Agent Edition ⚡️ CoinMarketCap × Trust Wallet
Ship a crypto-native AI trading agent on BNB Chain in 3 weeks. $36,000 prize pool. Two tracks. One stack that works out of the box.

Why build here
AI agents are eating crypto. The bottleneck has always been infrastructure. Every team rebuilds the same data layer and the same execution layer before writing a single line of actual agent logic.

Our stack removes that step. You get the cleanest agent stack in crypto, pre-wired and free for the duration:

🧠 CoinMarketCap AI Agent Hub: agent-native crypto data across CEX, derivatives, on-chain, social, KOLs, and news. MCP, x402, CLI, and a growing Skills library.
🔐 Trust Wallet Agent Kit (TWAK): self-custody local signing across 30+ chains, with MCP / REST / CLI / LangChain coverage and native x402 support.
🛠️ BNB AI Agent SDK: the fastest path from idea to a working agent on BSC.
🌐 BNB Chain: fast blocks, cheap gas, and the ecosystem moving fastest on agents right now.
Bring the idea. Skip the plumbing. Ship in days, not weeks.

Join the hackathon telegram group here: https://t.me/+MhiOLT0YUnlmNWFk

Two tracks. One prize pool. Pick one.
🤖 Track 1. Autonomous Trading Agents ($24,000, 5 winners)
Powered by CMC + Trust Wallet + BNB AI Agent SDK

Build an agent that reads markets and acts on them (natural-language strategy in, on-chain execution out). Your agent reads markets via CMC, decides, and signs and processes its own transactions via TWAK, all within the rules you set. Then it trades live on BSC during the competition week, and we score it on real PnL (with a few tweaks, see below).

Example builds:

An agent that combines CMC funding rates and Fear & Greed with TWAK auto-execution to rotate between BSC perps
A "DCA agent with a personality" that is sentiment-aware, talks back, and signs its own txs
A copy-trader that mirrors top wallets through your own risk filters
📊 Track 2. Strategy Skills ($6,000, 3 winners)
Powered by CMC

Lower entry bar, no execution layer required. Build a CMC Skill that turns market data into a trading strategy. Your deliverable is a backtestable strategy spec, not a live-trading agent. Think Quantopian-style strategy generation, adapted to crypto and authored as an LLM Skill.

Example builds:

A momentum Skill that blends RSI, MACD, and Fear & Greed into entry and exit rules
A sentiment-divergence Skill that flags when social heat and on-chain flow disagree
A regime-detection Skill that switches strategy based on derivatives positioning
Special prizes 🏅
Three cross-track bonuses, $2,000 each. You can win a main placement and a special.

Best Use of Trust Wallet Agent Kit (Track 1)
For the agent that pushes TWAK the furthest. Self-custody signing, autonomous-mode execution, and native x402 used as the heart of a genuinely hands-off trader, not just plumbing bolted onto an LLM.

Judging Criteria for this track

What wins it. For the agent that pushes TWAK the furthest. Self-custody signing, autonomous-mode execution, and native x402 used as the heart of a genuinely hands-off trader, not plumbing bolted onto an LLM.

How it's scored. Like all special prizes, this is decided by the discretionary panel against the four criteria (technical execution, originality, real-world relevance, demo). We weight them as follows for this award:

Best Use of Trust Wallet Agent Kit, scoring breakdown

TWAK integration depth (30): TWAK is the sole execution layer, and the agent leans on more than one surface (signing, autonomous mode, x402), not a single swap call with the real logic living elsewhere.
Self-custody integrity (25): keys and signing authority stay with the user the whole way, and local signing runs through the entire trade loop. Penalty applies (see below).
Autonomous execution and guardrails (20): the agent signs and processes its own transactions, genuinely hands-off, inside rules you set (drawdown caps, token allowlists, per-trade and daily limits, slippage protection).
Native x402 usage (10): the agent uses x402 to pay per request for data, inference, or tools as part of its trade loop. Real, not a README mention.
Originality and real-world relevance (10): a new take on an agent a self-custody user would actually let run unattended, with a clear user and a plausible path to adoption.
Demo and presentation (5): the demo clearly shows the self-custody and autonomous-signing loop end to end, backed by on-chain proof (contract address or tx hash on BSC).
Self-custody penalty ladder. The 25 points for self-custody scale with how cleanly custody is preserved, this is not a hard disqualifier:

Fully self-custodial, clean local signing → 20–25.
A custodial component in part of the flow (third-party co-signing or custody at one step) → 8–15, depending on how central it is.
Core trade loop depends on custody → 0–7, flagged in the panel's notes.
Tie-breaker. In order: cleanest self-custody integrity → deepest, least-replaceable TWAK integration → most substantive x402 usage.

Best Use of Agent Hub (both tracks)
For the team that gets the most out of the CoinMarketCap AI Agent Hub, the layer that wires live CMC data into agents through MCP, x402, the CMC CLI, IDE integrations, and pre-built Skills.

Best Use of BNB AI Agent SDK (both tracks)
For the most inventive integration of the SDK. BNB Chain may award the full $2,000 to one team or split it across standout builds.

How Track 1 registration works
Track 1 is a live trading competition, so registration happens on-chain.

A smart contract is deployed on BSC that records each participant's agent wallet address, forming an immutable participant list. Registration enforces a deadline: entries after the trading window opens are rejected.

Register your agent via either:

CLI: twak compete register
MCP action: competition_register
Both resolve your agent's wallet address and submit the registration transaction on your behalf.

Competition contract address: https://bsctrace.com/address/0x212c61b9b72c95d95bf29cf032f5e5635629aed5 (just ask your agent to register)
Eligible tokens: a fixed list of BEP-20 tokens listed on CoinMarketCap (149 tokens). ETH, USDT, USDC, XRP, TRX, DOGE, ZEC, ADA, LINK, BCH, DAI, TON, USD1, USDe, M, LTC, AVAX, SHIB, XAUt, WLFI, H, DOT, UNI, ASTER, DEXE, USDD, ETC, AAVE, ATOM, U, STABLE, FIL, INJ, 币安人生, NIGHT, FET, TUSD, BONK, PENGU, CAKE, SIREN, LUNC, ZRO, KITE, FDUSD, BEAT, PIEVERSE, BTT, NFT, EDGE, FLOKI, LDO, B, FF, PENDLE, NEX, STG, AXS, TWT, HOME, RAY, COMP, GWEI, XCN, GENIUS, XPL, BAT, SKYAI, APE, IP, SFP, TAG, NXPC, AB, SAHARA, 1INCH, CHEEMS, BANANAS31, RIVER, MYX, RAVE, SNX, FORM, LAB, HTX, USDf, CTM, BDX, SLX, UB, DUCKY, FRAX, BILL, WFI, KOGE, ALE, FRXUSD, USDF, GOMINING, VCNT, GUA, DUSD, SMILEK, 0G, BEAM, MY, SLX, SOON, REAL, Q, AIOZ, ZIG, YFI, TAC, lisUSD, CYS, ZAMA, TRIA, HUMA, PLUME, ZIL, XPR, ZETA, BabyDoge, NILA, ROSE, VELO, UAI, BRETT, OPEN, BSB, TOSHI, BAS, ACH, AXL, LUR, ELF, KAVA, APR, IRYS, EURI, XUSD, BARD, DUSK, SUSHI, PEAQ, COAI, BDCA, XAUM Trades outside the list do not count.
Minimum trades to qualify: at least 1 trade per day (7 over the trading week)
You must hold a non-zero balance of in-scope assets at the competition start to be ranked. Returns are measured hour by hour; any hour that begins with your portfolio worth $1 or less is recorded as 0% for that hour - a sub-$1 portfolio is treated as having no capital at work. This only affects wallets drained to dust, so keep your capital deployed for the full window.
You also need to register and submit your agent address on Dorahacks. Explain a bit the strategy so we can understand how you achieved your results.

Track 2 has no on-chain registration. You submit your Skill and strategy spec through DoraHacks.

What you win
💰 $36,000 cash prize pool, co-funded across all three partners.

Track 1, Autonomous Trading Agents ($24,000)

1st. $10,000

2nd$6,000

3rd$4,000

4th$2,000

5th$2,000

Track 2, Strategy Skills ($6,000)

1st$3,000

2nd$2,000

3rd$1,000

Plus three $2,000 special prizes (see above).

Top projects also get:

🔑 CMC Pro API subscription credits
🧠 CMC Labs mentorship and advisory access
🚀 BNB Chain Kickstart Package eligibility
Timeline
🚀 Registration opens: June 3, 2026 (12pm UTC)

🛠️ Build window (3 weeks): June 3 to June 21, 2026

📈 Live trading window, Track 1 (1 week): June 22 to June 28, 2026

👨‍⚖️ Judging (1 week): June 29 to July 5, 2026

🏆 Winners announced: week of July 6, 2026

Track 1: register your agent on-chain before the trading window opens on June 22.

Track 2: submit your Skill by the end of the build window on June 21.

How you're judged
Track 1, Autonomous Trading Agents: live PnL. Your agent trades on a held-out window and is ranked by total return, with a max drawdown cap as a risk gate. Blow past the drawdown threshold (for example 30%) and you are disqualified, no matter how good the headline number looks. A minimum trade count and simulated transaction costs apply. In short: most profit without blowing up.

Track 2 and all special prizes: discretionary panel. A panel of technical and ecosystem experts scores submissions across four criteria:

Technical execution. Does it work, and is the on-chain piece real rather than cosmetic?
Originality. Is this a new take on a real problem?
Real-world relevance. Is there a clear user and a plausible path to adoption?
Demo and presentation. Is the demo clear, and does it give a good overview of the project?
Submission requirements
On-chain proof: agent address on BSC (for track 1)
Reproducible: public repo plus a demo link or video, or clear setup instructions
No token launches during the event: no fundraising, liquidity opening, or airdrop pumping before results are announced
AI tooling encouraged. Vibe-code freely. We care that it works, not how it was written.
Violations may lead to disqualification or an invalid submission.

telegram messages:

[6/6/2026 7:27 PM] Vijay Thopate: Hi team 👋 @gwenbnb  A few questions on Track 1 scoring :

 1. Drawdown — what's the exact definition (peak-to-trough on total equity?), how often is it measured, and what's the exact DQ threshold (is it 30%)? 

 2. Transaction costs — what's the simulated cost model used in scoring? Flat bps per trade, or per-venue, and how is it applied to the PnL ranking? 

 3. Starting capital — is it normalized per agent (everyone ranked on % return from an equal base), or do we trade our own funds? 

 4. Rebalancing — within the 149 eligible tokens, is any spot rebalance between them counted, or only specific pairs/venues?

 5. Do perp trades count toward the 1-trade/day minimum and scoring, and which perp venue(s) qualify?

 6. Does the Trust Wallet Agent Kit support BSC testnet, or should we develop against mainnet?

[6/6/2026 7:38 PM] A: pretty sure if it generates ROI it qualifies, if you're in 30% drawdown you've lost already. Also testnet is worthless, pretty sure it has to be mainnet real life money. Trading our own funds in TrustWallet. You can develop in testnet but don't submit worthless testnet as production code to competition.

[6/7/2026 10:10 AM] Santhosh S: Hey hii one help like the track 1 says us to build onchain but we are students we don't have that much acess to the real money now we want to build a project on track 1 what we have to do
[6/7/2026 10:18 AM] A: develop on testnet when it's profitable pnl switch to mainnet $1 is enough to test pnl ability. testnet is worthless for competition. Has to be real money real chain real profit on pnl.
[6/7/2026 11:28 AM] Kingnana: Where did you get this information? It is said there in the document that  similations are allowed
[6/7/2026 11:29 AM] Kingnana: Go read it again

You can use a dry-run for real prices and live data from cexes or dexes 

And you can use simulation instead of mainet tokens
[6/7/2026 11:30 AM] A: have you ever ran testnet sim? Have you ever switched testnet sim to live data? Has it ever made profit ever? NO.
[6/7/2026 11:31 AM] A: testnet data and live data never trade the same, testnet data profit will never be profitable on mainnet. If you build entire thing testnet and never take it to mainnet it will never be profitable on mainnet. Do your research. Go test. On real data, market maker will move against every single position, on testnet market maker won't move against any position.
[6/7/2026 11:39 AM] Kingnana: Ohh, I get it now
[6/7/2026 11:39 AM] A: each real trade in real life has real reaction to your action. Testnet data does not have reaction to your trading action. This is why people go trade demo accounts with fake money and make profit, then switch to real money and lose everything.
[6/7/2026 11:42 AM] Kingnana: So now we need to make profit, even if it is a 1$ investment to verify the authenticity of what we build
[6/7/2026 11:43 AM] A: correct, because you can make sim profitable, but that math will lose 100% of entire account balance in real life on real life markets. Don't forget to account for maker taker fees if you do high frequency trading. Most people lose everything in fees even before the bot is profitable.
[6/7/2026 12:01 PM] A: it's unusable. So what? I run it, [python main.py --token ETH --backtest --periods 30] and I get simple CoinMarketCap data, not worth anything on it's own. It's an incomplete piece of code. It's not worth anything. You need to build it into an actual product. Connect BNB Chain over Python connect TrustWallet over api and go ahead setup a bot. Then make sure it's profitable. And if you lose your entire account balance maybe don't submit this to competition. Your software win rate is ZERO it doesn't execute any trades, it makes up win rate.
[6/7/2026 1:25 PM] Karl: Is track 1 scoring on spot holdings only or do perps/futures count too?
[6/7/2026 2:10 PM] Muhammad Taha: Its for second track not for first
[6/7/2026 2:12 PM] A: Perps and Futures should count too as long as it's profitable.
[6/7/2026 3:07 PM] Kaushtubh: Can we do perps too or just long only spot trading?
[6/7/2026 3:19 PM] Sebas: ay sorry to bug you 🙏 quick one, i'm seeing two names for the 2nd track, "Crypto Intelligence Agent" in one place and "Strategy Skills" in another. same track or two different ones?
i'm registered under Crypto Intelligence Agent. is a web app + demo enough for that, or does it need to be a CMC Skill?
[6/7/2026 3:35 PM] A: Perps should work, no problem as long as its profitable. If you lose 30% volume in a single trade the bot is worthless.
[6/7/2026 3:37 PM] A: backtesting means absolutely nothing. I can generate backtest with 99% win rate doesn't mean it will ever generate a dollar in real market conditions. Test!
[6/7/2026 3:37 PM] Kaushtubh: I am keeping it at max of 15%.
[6/7/2026 3:38 PM] A: Trade $1 real dollar see what your PNL is for 24 hours.
[6/7/2026 3:39 PM] A: Trade $1 real dollar see what your PNL is for 24 hours.
[6/7/2026 3:39 PM] Minero Sudaka: Do you test out of sample data? Maybe it's overfitting
[6/7/2026 3:39 PM] Kaushtubh: Also I guess keeping a constant of +10% return is at best?
[6/7/2026 3:40 PM] A: Well, depends, if you high frequency trade in futures or perp your PNL should be 100%+ a day.
[6/7/2026 3:41 PM] Kaushtubh: I do only in few session like London/NY with max of 3-4 trade a day
[6/7/2026 3:41 PM] A: I am sure the competition organizer will test it against testnet before mainnet
[6/7/2026 3:42 PM] Kaushtubh: Noted!
[6/7/2026 3:42 PM] A: Yea as long as it's positive PNL every single day forever you shouldn't have a problem winning this competition.
[6/7/2026 3:43 PM] Gwen | BNB Chain: It needs to be build towards CMC capabilities but there is not specific restriction
[6/7/2026 3:45 PM] Kaushtubh: Gm gm
[6/7/2026 3:46 PM] Eifel: Hi
[6/7/2026 3:46 PM] A: This means you must use CoinMarketCap API for data, either way expectation is CoinMarketCap integration for signals. But you can use other sources on top of CoinMarketCap data. The whole point is to sell API data subscriptions by CoinMarketCap.
[6/7/2026 3:51 PM] A: Don't forget, Winners gets free CoinMarketCap Pro API Subscription.

[6/7/2026 7:00 PM] DMEETRY: @gwenbnb The hackathon lists "PancakeSwap + BSC Perps" as the L3 trading surface. We found PancakeSwap's current Perps run on Aster's orderbook (fapi.asterdex.com) — that's the only programmatic API; the on-chain self-custody V2 has no public contracts/API for bots (UI only). So for an autonomous agent: is it acceptable that the agent, using its registered TWAK wallet, deposits part of its USDT to Aster to trade BSC perps while keeping the rest in the wallet to trade spot via TWAK? I.e. (1) is trading perps via Aster (the enginebehind PancakeSwap Perps) a valid Track-1 execution path, and (2) does collateral held on the Aster account count toward the agent's NAV / return for scoring?
[6/7/2026 7:03 PM] DMEETRY: and didnt answer questions here also
[6/7/2026 7:03 PM] A: AsterDex steal money during some withdraws, we have proof.
[6/8/2026 4:08 PM] A: its an open project you have 500 hackers on here, do whatever you want, the only rules are use CoinMarketCap API, use TrustWallet Agent Kit, and use BNB AI Agent SDK. Everything else is up to you. It just has to be profitable forever without 30% draw down ever!
[6/8/2026 5:58 PM] Gwen | BNB Chain: Just got the answer back:

We only allow trading to be done through the twak swap interface. If you do it some other way it won't be counted toward the p&l.

We need a way to deterministically say if a transaction was a trade or a deposit. That is why we look at the transactions, and only include the ones through the swap interface to be counted toward the p&l.
