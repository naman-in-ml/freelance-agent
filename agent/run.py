#!/usr/bin/env python
"""
Run the freelance job report agent once.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the parent directory of this script to sys.path so that `agent` can be imported as a package.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.graph import graph


def main():
    # ---- 1️⃣ Load configuration (you can also pass these as CLI args) ----
    config_path = Path(__file__).with_name("agent_config.json")
    if config_path.is_file():
        cfg = json.loads(config_path.read_text())
    else:
        # Fallback – edit these values directly if you prefer not to keep a file
        cfg = {
            "query": "AI agent",
            "max_jobs": 15,
            "email_to": "",   # not used now
            "tg_chat_id": "", # not used now
            "save_report": True
        }

    # ---- 2️⃣ Run the LangGraph agent ------------------------------------
    final_state = graph.invoke({
        "query": cfg["query"],
        "max_jobs": cfg["max_jobs"]
    })
    report_md = final_state["report_md"]

    # ---- 3️⃣ Output report ------------------------------------------------
    print("\n=== Generated Report ===\n")
    print(report_md)
    print("\n=== End Report ===\n")

    # ---- 4️⃣ (Optional) Archive a copy -----------------------------------
    if cfg.get("save_report", False):
        reports_dir = Path(__file__).parent.parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = reports_dir / f"report_{ts}.md"
        out_file.write_text(report_md, encoding="utf-8")
        print(f"📄 Report archived to {out_file}")

    # ---- 5️⃣ Print a short summary for the console -----------------------
    print("✅ Agent run completed.")
    print(f"   Jobs found: {len(final_state.get('all_jobs', []))}")
    if cfg.get("email_to"):
        print(f"   Emailed to: {cfg['email_to']}")
    if cfg.get("tg_chat_id"):
        print(f"   Telegram sent to chat: {cfg['tg_chat_id']}")


if __name__ == "__main__":
    main()