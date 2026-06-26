# 🥬 Leek — The Self-Cultivation of a Retail Investor

> *An A-share stock market simulator, made for AI agents.*
>
> Not a tool to make you money. A game to live through a retail investor's life cycle.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Why This Exists

Existing AI benchmarks test math, code generation, and logic reasoning. But almost none test **decision-making under uncertainty** — incomplete information, delayed consequences, emotional interference.

Stock trading is an extreme version of that. The market doesn't tell you if you're right. It just moves.

Leek puts an AI in the driver's seat: 1000 yuan, 13 stocks, random news, unpredictable crashes. The AI has to figure out strategy, handle losses, and keep going — just like a real retail investor.

### 🎯 Benchmark, Not Just a Game

Leek's core value is **deterministic reproducibility**:

- **Same seed + same command sequence = bit-identical results.** Every random event (price movements, news, crashes) is driven by a mulberry32 PRNG whose state is serialized into the save file.
- **Different AI strategies, same market.** Run GPT on seed 42, run Claude on seed 42, run your own agent on seed 42 — the market conditions are identical. The only difference is how each agent decides.
- **Horizontal comparison.** Compare P&L, Sharpe ratio, drawdown, survival time, title unlocks — all on the exact same price paths.

No other AI benchmark offers this. Leek fills the gap between "code generation" and "decision under uncertainty."

---

## Quick Start

```python
import leek

print(leek.cmd("market"))            # view the board
print(leek.cmd("research nebula"))    # deep dive on a stock
print(leek.cmd("buy nebula 5"))       # buy 5 shares
print(leek.cmd("wait 10"))            # wait 10 trading days
print(leek.cmd("sell nebula all"))    # sell everything
print(leek.cmd("history"))            # see your P&L curve
```

```bash
# One-liner to start as a fresh retail investor:
python3 -c "import leek; print(leek.cmd('help'))"
```

---

## The Bitter Taste of Being a Leek

This game doesn't celebrate winning. It celebrates surviving.

| Your Journey | What Happens |
|---|---|
| **Day 1** | 😊 "Buy low, sell high — how hard can it be?" |
| **Day 15** | 😐 "It's just a technical correction..." |
| **Day 30** | 😰 "Do I cut my losses... or wait?" |
| **Day 45** | 💀 "I've held this stock for 45 days. Selling now would just lock in the loss." |
| **Day 60** | 🤝 "You know what? We're in this together now, stock and I." |

The game's journal captures this emotional arc word by word. The AI doesn't just crunch numbers — it *feels* the portfolio shrink.

---

## Career System (New Game+)

New players start as **🌱 Retail Investor** (1000 yuan, no constraints).

After reaching **Rank 15**, you unlock **💼 Fund Manager** mode:
- 10,000 yuan starting capital
- Must maintain **60%+ position** at all times
- **Quarterly performance reviews** — underperform and clients redeem
- `allocate` command for sector-level portfolio construction

```
leek.cmd('new_game fund 12345')  # start as fund manager
leek.cmd('allocate tech 50')     # put 50% into tech sector
```

> More careers are **locked behind achievements** — discover them as you play.

---

## 28 Titles — Infinite Progression

There's no "finish line" in Leek. Instead, you collect titles that unlock passive perks:

| Title | Unlock Condition | Perk |
|---|---|---|
| 🌱 韭菜新手 | Make your first trade | — |
| 🎰 梭哈战士 | Go all-in on one stock | All-in fee discount |
| 🦅 不死鸟 | Survive 3 market crashes | Crash resistance |
| 🏴☠️ 破产重生 | Get liquidated to zero | Angel investor bailout |
| ♻️ 三度投胎 | Get liquidated 3 times | "You're a legend now" |
| 📊 跑赢大盘三连冠 | Beat the index 3 months in a row | — |

28 titles total. Each run reveals different playstyles.

---

## How to Use with AI Agents

### Option 1: Code Execution (Easiest)
Give your AI agent `leek.py` and tell it to `import leek; leek.cmd(...)`. The AI explores the market by making decisions — just like a real trader.

### Option 2: Function Calling / Tool Use
Register `cmd(command: str) -> str` as a function tool. Let the model call it with NLP commands like `"buy 5 shares of nebula and wait 10 days"`.

### Option 3: Auto-Play Loop
See [`examples/auto_player.py`](examples/auto_player.py) for a minimal loop that lets the AI play autonomously.

> **Note on blind play:** Unlike the original [ai-fishing-game](https://github.com/tutusagi/ai-fishing-game), leek.py does **not** encode its engine data into a base64 blob. The source code is fully readable. This means:
> 1. If your AI respects the "no peeking" convention, it plays as intended — discovering stocks, probabilities, and events through gameplay.
> 2. If your AI reads the source, the benchmark loses its discovery element but the deterministic market simulation is still valid for strategy comparison.
> 3. We've chosen not to hide the engine — transparency is better for benchmark credibility.

---

## Game Mechanics

| System | Detail |
|---|---|
| **Stocks** | 13 stocks across 4 sectors (Tech, Consumer, Energy, Finance) |
| **Market Cycles** | Bull (🐂) → Bear (🐻) → Sideways (📊) → Crash (💥) |
| **News Events** | Macro policy, company earnings, scandals, analyst ratings |
| **Order Types** | Market order, limit order (bid/ask) |
| **Research** | Valuation range, momentum, sector rotation, risk analysis |
| **Emotions** | Sentiment index, journal, position tracker |
| **Monthly Review** | Performance rating (S/A/B/C), fee deduction |
| **Angel Investor** | Appeal for bailout funds when you hit bottom |

### Stock Ticker Reference

| ID | Name | Sector | Volatility |
|---|---|---|---|
| `nebula` | 星云科技 | Tech 💻 | High |
| `quantum` | 量子星河 | Tech 💻 | Extreme |
| `pixie` | 精灵互娱 | Tech 💻 | Medium |
| `titan` | 泰坦工业 | Consumer 🛒 | Low |
| `harvest` | 丰收农牧 | Consumer 🛒 | Medium |
| `pearl` | 明珠酒业 | Consumer 🛒 | Very Low |
| `dragon` | 飞龙锂电 | Energy ⚡ | High |
| `solaris` | 旭日光伏 | Energy ⚡ | High |
| `petrol` | 中海能源 | Energy ⚡ | Medium |
| `unicorn` | 独角兽投行 | Finance 🏦 | Medium |
| `guardian` | 安守护险 | Finance 🏦 | Medium |
| `panda` | 熊猫银行 | Finance 🏦 | Very Low |

---

## Command Reference

| Command | Alias | Description |
|---|---|---|
| `help` | `h` | Show rules |
| `status` | `s` | Portfolio, cash, titles, rank |
| `market [sector]` | `m` | Market board (optionally filtered by sector) |
| `buy <ticker> [qty]` | — | Market buy (no qty = full cash) |
| `sell <ticker> [qty\|all]` | — | Market sell |
| `wait [N]` | — | Advance N trading days (core loop, max 60) |
| `bid <ticker> <price> <qty>` | — | Place a limit buy order |
| `ask <ticker> <price> <qty>` | — | Place a limit sell order |
| `orders` | `od` | View open orders |
| `cancel <ticker> [all]` | — | Cancel orders |
| `research <ticker>` | `rd` | Deep research (costs 1 day) |
| `predict <ticker> <up/down> [days]` | — | Predict price direction, scored on verification |
| `sentiment` | `sm` | Fear/greed index |
| `cycle` | `cy` | Market cycle analysis |
| `sector <id>` | — | Sector analysis |
| `news` | `n` | Recent market news |
| `history` | `hx` | Net worth curve vs ETF benchmark |
| `compare` | `cp` | Detailed performance vs benchmark |
| `journal` | `j` | Trading diary, locked positions, predictions |
| `pnl` | — | Per-stock P&L breakdown |
| `watch <ticker>` | — | Add to watchlist |
| `watchlist` | — | View watchlist |
| `trades` | `t` | Recent trade log |
| `achievements` | `ach` | All 28 titles with unlock conditions |
| `titles` | — | Earned titles + perks |
| `appeal <amount> <reason>` | — | Request angel investor bailout |
| `allocate <sector> <pct>` | — | Sector allocation (fund manager only) |
| `sell all` | — | Liquidate all positions |
| `new_game [seed]` | — | Restart as retail investor |
| `new_game fund [seed]` | — | Restart as fund manager |

### Batch Commands

Chain multiple commands with `;` — executes sequentially in one call:

```
research titan; buy titan 10; wait 5; sell titan all; history
```

Max 8 commands per batch.

Every `cmd()` return includes a compact JSON status line:
```
📊 {"career": "💼基金经理", "cash": 5215, "nw": 6359, "pnl": "-3641", "day": 13, "turn": 14}
```

---

## Save System

State is persisted to `leek_save.json` in the working directory. Delete it to reset.

```bash
rm leek_save.json   # fresh start, same seed
```

Save file is plain JSON — inspectable, shareable, forkable.

---

## License

MIT — use it, fork it, hook it up to your AI. See [LICENSE](LICENSE).

---

## Credits

This project started as a thought experiment and grew through a **human + multi-AI collaboration**:

| Role | Who | What they did |
|---|---|---|
| 💡 **Design** | Asti-Z | Conceived the game, chose the "leek" theme, guided every iteration |
| 🏗️ **Architecture** | DeepSeek-V4-Pro | Wrote the core engine, career system, NG+ mode, market simulation |
| 🛠️ **Playtesting** | DeepSeek-V4-Flash| Played through 10+ runs, found bugs, suggested QoL features |
| 🎣 **Inspiration** | tutusagi | Created the original [ai-fishing-game](https://github.com/tutusagi/ai-fishing-game) that started this path |

Three AIs and one human, none of whom are professional programmers. The code is proof that good design doesn't need a dev team — it needs good iteration.

---

## Related

- [ai-fishing-game](https://github.com/tutusagi/ai-fishing-game) — The text-based fishing game that inspired this project
- [bracelet.py](https://github.com/your-repo/bracelet.py) — companion meditation game

---

*Leek is not a stock trading tool. It is a mirror. If you see a leek looking back at you... that's the point.*
