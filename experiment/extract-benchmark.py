#!/usr/bin/env python3
"""
E8 — Extractor: Langfuse Results → Benchmark Consolidado.

Usage:
    # From experiment results directory
    python experiment/extract-benchmark.py experiments/<nome>

    # Specify output path
    python experiment/extract-benchmark.py experiments/<nome> --output experiments/<nome>/benchmark.json
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def load_results(results_dir: Path) -> dict:
    """Load all config results from the results directory."""
    configs = {}
    if not results_dir.exists():
        return configs

    for config_dir in sorted(results_dir.iterdir()):
        if not config_dir.is_dir():
            continue

        config_id = config_dir.name
        summary_path = config_dir / "summary.json"
        timing_path = config_dir / "timing.json"
        run_id_path = config_dir / "run-id.txt"
        langfuse_url_path = config_dir / "langfuse-url.txt"

        config_data = {"config_id": config_id}

        if summary_path.exists():
            with open(summary_path) as f:
                config_data["summary"] = json.load(f)

        if timing_path.exists():
            with open(timing_path) as f:
                config_data["timing"] = json.load(f)

        if run_id_path.exists():
            config_data["run_id"] = run_id_path.read_text().strip()

        if langfuse_url_path.exists():
            config_data["langfuse_url"] = langfuse_url_path.read_text().strip()

        configs[config_id] = config_data

    return configs


def load_variation_report(exp_dir: Path) -> dict:
    """Parse variation-report.md for human-readable descriptions."""
    report_path = exp_dir / "variation-report.md"
    variations = {}
    if not report_path.exists():
        return variations

    current_id = None
    current_data = {}

    for line in report_path.read_text().splitlines():
        if line.startswith("## "):
            if current_id and current_data:
                variations[current_id] = current_data
            vname = line.strip("# ").strip()
            current_id = vname.lower().replace(" ", "-")
            current_data = {"name": vname}
        elif line.startswith("- **") and current_id:
            key_end = line.find("**", 4)
            if key_end > 0:
                key = line[4:key_end].strip().lower().replace(" ", "_")
                val_sep = line.find(":", key_end)
                if val_sep > 0:
                    val = line[val_sep + 1 :].strip()
                    current_data[key] = val

    if current_id and current_data:
        variations[current_id] = current_data

    return variations


def compute_benchmark(configs: dict[str, dict], variations: dict, exp_name: str = "unknown") -> dict:
    """Compute benchmark from loaded results."""
    configurations = {}
    baseline_key = None

    # Identify baseline
    for cid in configs:
        if cid == "baseline" or cid.startswith("baseline"):
            baseline_key = cid
            break
    if not baseline_key and configs:
        baseline_key = list(configs.keys())[0]

    # Build per-config metrics
    for cid, cdata in configs.items():
        summary = cdata.get("summary", {})
        timing = cdata.get("timing", {})
        var_info = variations.get(cid, {})

        cfg = {
            "name": var_info.get("name", cdata.get("config_id", cid)),
            "description": var_info.get("system_prompt", ""),
            "axis": var_info.get("eixo", ""),
            "hypothesis": var_info.get("hipotese", ""),
        }

        # Metrics from summary.json
        if summary:
            rates = [summary.get("tool_assertion_rate"), summary.get("contains_assertion_rate")]
            rates = [r for r in rates if r is not None]
            cfg["pass_rate"] = {
                "mean": round(sum(rates) / len(rates), 2) if rates else 0.0,
            }
            cfg["tool_assertion_rate"] = {
                "mean": summary.get("tool_assertion_rate", 0.0),
            }
            cfg["contains_assertion_rate"] = {
                "mean": summary.get("contains_assertion_rate", 0.0),
            }
            cfg["total_items"] = summary.get("total_items", 0)
        else:
            cfg["pass_rate"] = {"mean": 0.0}

        # Timing
        cfg["time_seconds"] = {"mean": timing.get("duration_seconds", 0)}
        cfg["status"] = cdata.get("summary", {}).get("status", "unknown")

        # Run info
        cfg["run_id"] = cdata.get("run_id", "")
        cfg["langfuse_url"] = cdata.get("langfuse_url", "")

        configurations[cid] = cfg

    # Compute baseline stats
    baseline = configurations.get(baseline_key)
    if baseline:
        base_pass = baseline.get("pass_rate", {}).get("mean", 0.0)
        base_time = baseline.get("time_seconds", {}).get("mean", 0.0)

        for cid, cfg in configurations.items():
            if cid == baseline_key:
                cfg["delta"] = {"pass_rate": "—", "time_seconds": "—"}
            else:
                p = cfg.get("pass_rate", {}).get("mean", 0.0)
                t = cfg.get("time_seconds", {}).get("mean", 0.0)
                cfg["delta"] = {
                    "pass_rate": f"+{p - base_pass:.2f}" if p >= base_pass else f"{p - base_pass:.2f}",
                    "time_seconds": f"+{t - base_time:.1f}s" if t >= base_time else f"{t - base_time:.1f}s",
                }

    # Summary
    best = max(configurations.items(), key=lambda x: x[1].get("pass_rate", {}).get("mean", 0))
    fastest = min(configurations.items(), key=lambda x: x[1].get("time_seconds", {}).get("mean", 999))

    return {
        "experiment_name": exp_name,
        "timestamp": datetime.utcnow().isoformat(),
        "configurations": configurations,
        "baseline_config": baseline_key,
        "summary": {
            "total_configs": len(configurations),
            "best_pass_rate": best[0],
            "lowest_latency": fastest[0],
        },
        "analyst_notes": [],
    }


def generate_markdown(benchmark: dict) -> str:
    """Generate human-readable markdown from benchmark data."""
    name = benchmark["experiment_name"]
    configs = benchmark["configurations"]
    baseline = benchmark["baseline_config"]
    summary = benchmark["summary"]

    md = [f"# Benchmark: {name}", f"Gerado em: {benchmark['timestamp']}", ""]

    if summary["total_configs"] == 0:
        md.append("Nenhum resultado encontrado.")
        return "\n".join(md) + "\n"

    # Table
    md.append("## Tabela Comparativa")
    md.append("")
    md.append(
        "| Config | pass_rate | time_sec | delta_pass | delta_time | items | status |"
    )
    md.append(
        "|:-------|:---------:|:--------:|:----------:|:----------:|:-----:|:------:|"
    )

    sorted_configs = sorted(configs.items(), key=lambda x: (0 if x[0] == baseline else 1, x[0]))

    for cid, cfg in sorted_configs:
        name_str = f"**{cid}**" if cid == baseline else cid
        pr = cfg.get("pass_rate", {}).get("mean", "?")
        ts = cfg.get("time_seconds", {}).get("mean", "?")
        delta = cfg.get("delta", {})
        dp = delta.get("pass_rate", "—")
        dt = delta.get("time_seconds", "—")
        items = cfg.get("total_items", "?")
        status = cfg.get("status", "?")
        md.append(f"| {name_str} | {pr} | {ts}s | {dp} | {dt} | {items} | {status} |")

    md.append("")

    # Best config
    best = summary["best_pass_rate"]
    fastest = summary["lowest_latency"]
    md.append(f"**Melhor pass_rate:** {best}")
    md.append(f"**Menor latencia:** {fastest}")

    if best == fastest:
        md.append(f"\n✅ Recomendacao: **{best}** — melhor qualidade E menor latencia.")
    elif best != baseline:
        md.append(f"\n💡 **{best}** tem a melhor qualidade. Verificar trade-off de latencia.")
    else:
        md.append(
            f"\n⚠️ A configuracao atual ({baseline}) tem a melhor qualidade. Nenhuma melhoria significativa."
        )

    md.append("")
    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(
        description="E8 — Extractor: Experiment Results → Benchmark Consolidado"
    )
    parser.add_argument("experiment_dir", help="Path to experiment directory")
    parser.add_argument(
        "--output",
        default=None,
        help="Output path for benchmark.json (default: <experiment_dir>/benchmark.json)",
    )
    parser.add_argument(
        "--markdown",
        default=None,
        help="Output path for benchmark.md (default: <experiment_dir>/benchmark.md)",
    )
    args = parser.parse_args()

    exp_dir = Path(args.experiment_dir)
    if not exp_dir.exists():
        print(f"Erro: Diretorio nao encontrado: {exp_dir}", file=sys.stderr)
        sys.exit(1)

    results_dir = exp_dir / "results"
    if not results_dir.exists():
        print(f"Erro: Diretorio de resultados nao encontrado: {results_dir}", file=sys.stderr)
        print("Execute o experiment-runner primeiro para gerar resultados.")
        sys.exit(1)

    # Load data
    configs = load_results(results_dir)
    variations = load_variation_report(exp_dir)
    benchmark = compute_benchmark(configs, variations, exp_name=exp_dir.name)

    # Add analyst notes from variation descriptions
    for cid, cfg in benchmark["configurations"].items():
        if cfg.get("hypothesis"):
            benchmark["analyst_notes"].append(
                f"{cid}: {cfg['hypothesis']}"
            )

    # Output JSON
    output_path = args.output or str(exp_dir / "benchmark.json")
    with open(output_path, "w") as f:
        json.dump(benchmark, f, indent=2, ensure_ascii=False)
    print(f"✅ Benchmark escrito: {output_path}")
    print(f"   Configuracoes: {benchmark['summary']['total_configs']}")
    print(f"   Melhor pass_rate: {benchmark['summary']['best_pass_rate']}")
    print(f"   Menor latencia: {benchmark['summary']['lowest_latency']}")

    # Output Markdown
    md_path = args.markdown or str(exp_dir / "benchmark.md")
    md_content = generate_markdown(benchmark)
    with open(md_path, "w") as f:
        f.write(md_content)
    print(f"✅ Benchmark MD escrito: {md_path}")


if __name__ == "__main__":
    main()
