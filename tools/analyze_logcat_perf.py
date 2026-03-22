import re
import statistics
import subprocess


RE_END = re.compile(
    r"LLM_GENERATION_END id=([^\]]+)\](\d+) msg=([0-9a-f]+) "
    r"elapsed_ms=([0-9.]+) ttft_ms=([^ ]+) finish=([^ ]+) "
    r"prompt_t=([^ ]+) comp_t=([^ ]+) total_t=([^ ]+) "
    r"cpu_c=([^ ]+)->([^ ]+) batt_c=([^ ]+)->([^ ]+) thermal=([^ ]+)"
)


def _to_float(x):
    try:
        return float(x)
    except Exception:
        return None


def _to_int(x):
    try:
        return int(float(x))
    except Exception:
        return None


def _summarize(name, rows):
    print(f"{name}: n={len(rows)}")
    if not rows:
        return
    elapsed = [r["elapsed_s"] for r in rows]
    ttft = [r["ttft_s"] for r in rows if r["ttft_s"] is not None]
    print(
        "  elapsed_s avg/med/min/max=",
        round(statistics.mean(elapsed), 2),
        round(statistics.median(elapsed), 2),
        round(min(elapsed), 2),
        round(max(elapsed), 2),
    )
    if ttft:
        print(
            "  ttft_s   avg/med/min/max=",
            round(statistics.mean(ttft), 2),
            round(statistics.median(ttft), 2),
            round(min(ttft), 2),
            round(max(ttft), 2),
        )
    thermals = sorted({r["thermal"] for r in rows})
    print("  thermal counts=", {k: sum(1 for r in rows if r["thermal"] == k) for k in thermals})


def main():
    try:
        proc = subprocess.run(
            ["adb", "logcat", "-d", "-v", "time"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="ignore",
        )
    except Exception as e:
        raise SystemExit(f"Failed to run adb logcat: {e}")

    lines = proc.stdout.splitlines()
    rows = []
    for ln in lines:
        m = RE_END.search(ln)
        if not m:
            continue
        (
            gen_id,
            _ts,
            msg,
            elapsed_ms,
            ttft_ms,
            finish,
            prompt_t,
            comp_t,
            total_t,
            cpu0,
            cpu1,
            batt0,
            batt1,
            thermal,
        ) = m.groups()

        ttft = _to_float(ttft_ms)
        rows.append(
            {
                "id": gen_id,
                "msg": msg,
                "elapsed_s": float(elapsed_ms) / 1000.0,
                "ttft_s": (ttft / 1000.0) if ttft is not None else None,
                "finish": finish,
                "prompt_t": _to_int(prompt_t),
                "comp_t": _to_int(comp_t),
                "total_t": _to_int(total_t),
                "cpu0": _to_float(cpu0),
                "cpu1": _to_float(cpu1),
                "batt0": _to_float(batt0),
                "batt1": _to_float(batt1),
                "thermal": thermal,
            }
        )

    chat = [r for r in rows if not r["id"].startswith("BENCHMARK_SESSION")]
    bench = [r for r in rows if r["id"].startswith("BENCHMARK_SESSION")]

    _summarize("CHAT", chat)
    _summarize("BENCH", bench)

    if chat:
        print("\nLast chat generations:")
        for r in chat[-8:]:
            ttft_str = "?"
            if r["ttft_s"] is not None:
                ttft_str = f"{r['ttft_s']:.2f}s"
            print(
                f"- id={r['id'][:24]} elapsed={r['elapsed_s']:.2f}s ttft="
                f"{ttft_str} "
                f"prompt_t={r['prompt_t']} comp_t={r['comp_t']} finish={r['finish']} "
                f"thermal={r['thermal']} cpu={r['cpu0']}->{r['cpu1']}"
            )


if __name__ == "__main__":
    main()
