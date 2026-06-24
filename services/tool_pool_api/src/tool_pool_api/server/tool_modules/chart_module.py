# tool_pool_api/server/tool_modules/chart_module.py
"""
Chart Module — generates self-contained HTML charts using Chart.js.

No external runtime dependencies: the Chart.js library is loaded from CDN
inside the HTML, so the output is a single file the user can open in any
browser or embed in a Google Doc as a link.

Tools registered:
  - generate_chart_html
"""

import logging
import json
import tempfile
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP

from tool_pool_api.server.tool_modules import register_module

logger = logging.getLogger(__name__)

_CHART_TEMPLATE = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #f8f9fa; display: flex; justify-content: center;
            align-items: center; min-height: 100vh; padding: 24px; }}
    .card {{ background: #fff; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,.1);
             padding: 32px; max-width: 860px; width: 100%; }}
    h1 {{ font-size: 1.25rem; font-weight: 600; color: #1a1a2e; margin-bottom: 24px;
          text-align: center; }}
    canvas {{ max-height: 420px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{title}</h1>
    <canvas id="chart"></canvas>
  </div>
  <script>
    const ctx = document.getElementById("chart").getContext("2d");
    new Chart(ctx, {{
      type: "{chart_type}",
      data: {data_json},
      options: {{
        responsive: true,
        plugins: {{
          legend: {{ position: "top" }},
          tooltip: {{ mode: "index", intersect: false }}
        }},
        scales: {scales_json}
      }}
    }});
  </script>
</body>
</html>
"""

# Default colour palette — cycles if more datasets are supplied
_PALETTE = [
    "rgba(54, 162, 235, 0.8)",
    "rgba(255, 99, 132, 0.8)",
    "rgba(75, 192, 192, 0.8)",
    "rgba(255, 206, 86, 0.8)",
    "rgba(153, 102, 255, 0.8)",
    "rgba(255, 159, 64, 0.8)",
    "rgba(231, 233, 237, 0.8)",
]

_PALETTE_BORDER = [c.replace("0.8", "1") for c in _PALETTE]


def _build_chart_data(chart_type: str, labels: list, datasets: list) -> dict:
    """Normalise raw datasets into Chart.js dataset objects."""
    result = []
    pie_types = {"pie", "doughnut"}
    for i, ds in enumerate(datasets):
        colour = _PALETTE[i % len(_PALETTE)]
        border = _PALETTE_BORDER[i % len(_PALETTE_BORDER)]

        if chart_type in pie_types:
            # pie/doughnut: each segment gets its own colour
            colours = [_PALETTE[j % len(_PALETTE)] for j in range(len(labels))]
            borders = [_PALETTE_BORDER[j % len(_PALETTE_BORDER)] for j in range(len(labels))]
            obj = {
                "label": ds.get("label", f"Dataset {i+1}"),
                "data": ds["data"],
                "backgroundColor": colours,
                "borderColor": borders,
                "borderWidth": 1,
            }
        else:
            obj = {
                "label": ds.get("label", f"Dataset {i+1}"),
                "data": ds["data"],
                "backgroundColor": colour,
                "borderColor": border,
                "borderWidth": 2,
                "fill": ds.get("fill", False),
                "tension": 0.35,
            }
        result.append(obj)

    return {"labels": labels, "datasets": result}


def _scales_for(chart_type: str) -> dict:
    if chart_type in {"pie", "doughnut", "radar"}:
        return {}
    return {
        "x": {"grid": {"display": False}},
        "y": {"beginAtZero": True, "grid": {"color": "rgba(0,0,0,0.05)"}},
    }


@register_module
def register_tools(mcp: FastMCP) -> list[str]:

    @mcp.tool(name="generate_chart_html")
    def generate_chart_html(
        chart_type: Literal["bar", "line", "pie", "doughnut"],
        title: str,
        labels: list[str],
        datasets: list[dict],
    ) -> dict:
        """
        Generate a self-contained HTML chart file using Chart.js.

        Args:
            chart_type: One of "bar", "line", "pie", "doughnut".
            title: Chart title displayed at the top.
            labels: X-axis labels (or slice labels for pie/doughnut).
            datasets: List of dataset objects. Each must have:
                        - "label" (str): series name
                        - "data" (list[float]): values — length must match labels
                      Optional per-dataset keys: "fill" (bool, line charts only).
            Returns:
                {
                  "file_path": "/tmp/blu_charts/<title_slug>.html",
                  "chart_type": "bar",
                  "title": "...",
                  "dataset_count": 2,
                  "label_count": 6,
                  "preview_tip": "Open the file_path in any browser to view the chart."
                }
        """
        # Validate
        if not labels:
            return {"error": "labels cannot be empty"}
        if not datasets:
            return {"error": "datasets cannot be empty"}
        for ds in datasets:
            if "data" not in ds:
                return {"error": f"Dataset missing 'data' key: {ds}"}
            if len(ds["data"]) != len(labels):
                return {
                    "error": (
                        f"Dataset '{ds.get('label', '?')}' has {len(ds['data'])} values "
                        f"but {len(labels)} labels were supplied."
                    )
                }

        chart_data = _build_chart_data(chart_type, labels, datasets)
        scales = _scales_for(chart_type)

        html = _CHART_TEMPLATE.format(
            title=title,
            chart_type=chart_type,
            data_json=json.dumps(chart_data, ensure_ascii=False),
            scales_json=json.dumps(scales, ensure_ascii=False),
        )

        # Persist to /tmp/blu_charts/
        out_dir = Path(tempfile.gettempdir()) / "blu_charts"
        out_dir.mkdir(exist_ok=True)
        slug = "".join(c if c.isalnum() else "_" for c in title).strip("_")[:60] or "chart"
        file_path = out_dir / f"{slug}.html"
        file_path.write_text(html, encoding="utf-8")

        logger.info(f"[chart_module] generated {chart_type} chart → {file_path}")

        return {
            "file_path": str(file_path),
            "chart_type": chart_type,
            "title": title,
            "dataset_count": len(datasets),
            "label_count": len(labels),
            "preview_tip": "Open file_path in any browser to view the chart.",
        }

    return ["generate_chart_html"]
