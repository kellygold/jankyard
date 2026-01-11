"""
Generate simulation reports in JSON and Markdown formats
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from .models import SimulationReport


def save_json_report(report: SimulationReport, output_dir: str) -> Path:
    """Save report as JSON"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    filename = f"{report.challenge}_{report.difficulty}_{report.timestamp.strftime('%Y-%m-%d_%H%M%S')}.json"
    filepath = output_path / filename
    
    with open(filepath, 'w') as f:
        json.dump(report.to_dict(), f, indent=2)
    
    return filepath


def save_markdown_report(report: SimulationReport, output_dir: str) -> Path:
    """Save report as Markdown"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    filename = f"{report.challenge}_{report.difficulty}_{report.timestamp.strftime('%Y-%m-%d_%H%M%S')}.md"
    filepath = output_path / filename
    
    md = generate_markdown(report)
    
    with open(filepath, 'w') as f:
        f.write(md)
    
    return filepath


def generate_markdown(report: SimulationReport) -> str:
    """Generate markdown report content"""
    lines = [
        f"# {report.challenge.title()} Challenge Simulation Report",
        "",
        f"**Date:** {report.timestamp.strftime('%Y-%m-%d %H:%M')} | "
        f"**Difficulty:** {report.difficulty} | "
        f"**Duration:** {report.duration_seconds:.1f}s",
        "",
        f"**Cost:** ${report.total_cost_usd:.4f} | "
        f"**Tokens:** {report.total_tokens:,} | "
        f"**Runs:** {report.total_runs:,}",
        "",
        "---",
        "",
        "## Summary",
        "",
        f"- ✅ **{report.prompts_within_tolerance}** prompts within tolerance",
        f"- ⚠️ **{report.prompts_outside_tolerance}** prompts outside tolerance",
        f"- 📊 Success rate: **{report.success_rate:.0%}**",
        "",
    ]
    
    # Group results by category
    categories = {}
    for result in report.prompt_results:
        if result.category not in categories:
            categories[result.category] = []
        categories[result.category].append(result)
    
    # Results by category
    lines.append("## Results by Category")
    lines.append("")
    
    for category, results in categories.items():
        lines.append(f"### {category.replace('_', ' ').title()}")
        lines.append("")
        lines.append("| Prompt | Expected | Actual | Runs | Status |")
        lines.append("|--------|----------|--------|------|--------|")
        
        for r in results:
            lines.append(
                f"| {r.prompt_name} | {r.expected_win_rate:.0%} | "
                f"{r.actual_win_rate:.0%} | {r.total_runs} | {r.status} |"
            )
        
        lines.append("")
    
    # Anomalies
    if report.anomalies:
        lines.append("## ⚠️ Anomalies to Investigate")
        lines.append("")
        
        for i, anomaly in enumerate(report.anomalies, 1):
            lines.append(f"### {i}. {anomaly['prompt']}")
            lines.append("")
            lines.append(f"- **Category:** {anomaly['category']}")
            lines.append(f"- **Expected:** {anomaly['expected']:.0%}")
            lines.append(f"- **Actual:** {anomaly['actual']:.0%}")
            lines.append(f"- **Deviation:** {anomaly['deviation']:.0%}")
            
            if anomaly.get('sample_response'):
                lines.append(f"- **Sample response:** `{anomaly['sample_response'][:100]}...`")
            
            lines.append("")
    
    return "\n".join(lines)


def save_report(report: SimulationReport, output_dir: Optional[str] = None) -> tuple:
    """Save both JSON and Markdown reports"""
    output_dir = output_dir or report.challenge
    output_dir = f"tests/simulation_results/{output_dir}"
    
    json_path = save_json_report(report, output_dir)
    md_path = save_markdown_report(report, output_dir)
    
    return json_path, md_path
