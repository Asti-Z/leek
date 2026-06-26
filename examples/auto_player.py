#!/usr/bin/env python3
"""
Minimal auto-play loop for leek.py.
A simple "buy and hold" strategy to demonstrate autonomous trading.

Run: python3 examples/auto_player.py

The AI (or this script) makes decisions based purely on market data,
just like a real trader looking at their screen.
"""

import leek
import time

def auto_trader(seed=None, max_turns=50):
    """Simple rule-based strategy: buy sector leaders, hold through dips."""

    if seed:
        print(leek.cmd(f"new_game {seed}"))
    else:
        print(leek.cmd("new_game"))

    stats = {"buys": 0, "sells": 0, "crashes": 0}

    for turn in range(max_turns):
        response = leek.cmd("status")
        print(f"\n--- Turn {turn+1} ---")

        # Parse the JSON status line to get current state
        try:
            status_line = [l for l in response.split("\n") if l.startswith("📊")][0]
            # Extract key fields (crude but functional)
            if "nw" in status_line:
                nw_str = status_line.split('"nw":')[1].split(",")[0].strip()
                net_worth = float(nw_str)
        except:
            net_worth = 1000

        # Strategy: buy the cheapest tech stock if we have cash
        market = leek.cmd("market")
        if "cash" in response:
            cash_str = [l for l in response.split("\n") if "资金" in l]
            if cash_str:
                try:
                    cash = float(cash_str[0].replace("资金：", "").replace("元", "").strip())
                except:
                    cash = 0
            else:
                cash = 0

            if cash > 200:
                # pick a stock from the board (read market output)
                print(leek.cmd("buy nebula 5"))
                stats["buys"] += 1

        # Check if there's a crash
        if "💥" in response or "崩盘" in response:
            stats["crashes"] += 1

        # Wait 5 trading days
        wait_result = leek.cmd("wait 5")
        print(wait_result[:200] + "...")  # preview

    # Final summary
    print("\n=== Session Over ===")
    print(leek.cmd("history"))
    print(f"\nStats: {stats['buys']} buys, {stats['sells']} sells, {stats['crashes']} crashes seen")

if __name__ == "__main__":
    import sys
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else None
    auto_trader(seed=seed)
