#!/usr/bin/env python3
"""
Documentation Coverage Report Generator

Reads doc-coverage.json and generates reports in various formats.

Usage:
    python generate_report.py --format md
    python generate_report.py --format html
    python generate_report.py --format md --input custom.json --output report.md
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def load_coverage_data(input_path: Path) -> Dict:
    """Load coverage data from JSON"""
    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        sys.exit(1)

    try:
        return json.loads(input_path.read_text())
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {input_path}: {e}")
        sys.exit(1)


def generate_markdown_report(data: Dict) -> str:
    """Generate Markdown report"""
    meta = data['metadata']
    cov = data['coverage']
    features = data['features']

    # Group features by status
    good = [f for f in features if f['status'] == 'good']
    partial = [f for f in features if f['status'] == 'partial']
    missing = [f for f in features if f['status'] == 'missing']

    # Group missing by priority
    high_pri = [f for f in missing if f['priority'] == 'high']
    medium_pri = [f for f in missing if f['priority'] == 'medium']
    low_pri = [f for f in missing if f['priority'] == 'low']

    md = f"""# Documentation Coverage Report

**Project**: {meta['project']}
**Generated**: {datetime.fromisoformat(meta['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}
**Tool**: {meta['tool']} v{meta['version']}

---

## 📊 Coverage Summary

| Metric | Value | Status |
|--------|-------|--------|
| **Total Features** | {cov['total_features']} | - |
| **Documented** | {cov['documented']} | {'✅' if cov['coverage_percent'] >= 80 else '⚠️' if cov['coverage_percent'] >= 60 else '❌'} |
| **Coverage** | **{cov['coverage_percent']}%** | {'✅' if cov['coverage_percent'] >= 80 else '⚠️' if cov['coverage_percent'] >= 60 else '❌'} |
| **Gap** | {cov['gap']} features | - |

### By Status

- ✅ **Good** (README + Docs): {cov['by_status']['good']}
- ⚠️ **Partial** (README only): {cov['by_status']['partial']}
- ❌ **Missing**: {cov['by_status']['missing']}

### By Location

- 📖 **In README**: {cov['by_location']['readme']}
- 📚 **In Docs**: {cov['by_location']['docs']}
- 📓 **In Notebooks**: {cov['by_location']['notebooks']}

---

## ✅ Fully Documented Features ({len(good)})

"""

    for f in good:
        md += f"### {f['name']} ({f['test_count']} tests)\n\n"
        md += f"- **Test Class**: `{f['test_class']}`\n"
        md += f"- **Test Source**: [{f['test_file']}:{f['test_line']}]({f['test_file']}#L{f['test_line']})\n"
        if f['readme_locations']:
            md += f"- **README**: {f['readme_locations'][0]}\n"
        if f['docs_locations']:
            md += f"- **Docs**: {', '.join(f['docs_locations'])}\n"
        if f['test_link_locations']:
            md += f"- **Test Links**: {', '.join(f['test_link_locations'])}\n"
        md += "\n"

    md += "---\n\n"

    if partial:
        md += f"## ⚠️ Partially Documented Features ({len(partial)})\n\n"
        md += "*These features are documented but missing **[test]** links in documentation titles.*\n\n"
        for f in partial:
            md += f"### {f['name']} ({f['test_count']} tests)\n\n"
            md += f"- **Test Class**: `{f['test_class']}`\n"
            md += f"- **Test Source**: [{f['test_file']}:{f['test_line']}]({f['test_file']}#L{f['test_line']})\n"
            md += f"- **README**: {'✅' if f['in_readme'] else '❌'}\n"
            md += f"- **Docs**: {'✅' if f['in_docs'] else '❌'}\n"
            md += f"- **Test Link**: {'✅' if f['has_test_link'] else '❌ **MISSING**'}\n"

            # Show where to add the link
            if not f['has_test_link']:
                md += f"\n**📝 Action Required**: Add `[test]({f['test_file']}#L{f['test_line']})` to section titles in:\n"
                if f['readme_locations']:
                    md += f"- README.md near line {f['readme_locations'][0].split('(')[1].split(')')[0].split(':')[1].split(',')[0]}\n"
                if f['docs_locations']:
                    first_doc = f['docs_locations'][0].split(' (')[0]
                    md += f"- {first_doc}\n"

            md += "\n"
        md += "---\n\n"

    if missing:
        md += f"## ❌ Missing Documentation ({len(missing)})\n\n"

        if high_pri:
            md += f"### 🔴 High Priority ({len(high_pri)})\n\n"
            md += "*Features with 5+ tests - likely important for users.*\n\n"
            for f in high_pri:
                md += f"#### {f['name']}\n\n"
                md += f"- **Test Class**: `{f['test_class']}`\n"
                md += f"- **Tests**: {f['test_count']}\n"
                md += f"- **Keywords**: {', '.join(f['keywords'][:5])}\n"
                md += f"- **Test Methods**:\n"
                for test in f['test_names'][:5]:
                    md += f"  - `{test}`\n"
                md += "\n"

        if medium_pri:
            md += f"### 🟡 Medium Priority ({len(medium_pri)})\n\n"
            for f in medium_pri:
                md += f"#### {f['name']}\n\n"
                md += f"- **Test Class**: `{f['test_class']}`\n"
                md += f"- **Tests**: {f['test_count']}\n"
                md += f"- **Keywords**: {', '.join(f['keywords'][:5])}\n\n"

        if low_pri:
            md += f"### 🟢 Low Priority ({len(low_pri)})\n\n"
            for f in low_pri:
                md += f"- **{f['name']}** ({f['test_count']} tests) - `{f['test_class']}`\n"

    md += "\n---\n\n"
    md += "## 🎯 Recommendations\n\n"

    # Count features missing test links
    missing_links = [f for f in features if not f['has_test_link'] and (f['in_readme'] or f['in_docs'])]

    if missing_links:
        md += f"### 📌 Add Test Links ({len(missing_links)} features)\n\n"
        md += "All documented features should have `[test](...)` links in their documentation titles.\n\n"
        md += "**Pattern to use**:\n```markdown\n"
        md += "## Feature Name [test](tests/test_file.py#L123)\n```\n\n"
        md += "Or with emoji:\n```markdown\n"
        md += "## Feature Name [🧪 test](tests/test_file.py#L123)\n```\n\n"

    if high_pri:
        md += f"### 🔴 Immediate Action ({len(high_pri)} features)\n\n"
        for f in high_pri:
            md += f"1. Document **{f['name']}** - {f['test_count']} tests indicate this is a major feature\n"
        md += "\n"

    if medium_pri:
        md += f"### 🟡 Next Steps ({len(medium_pri)} features)\n\n"
        md += "These features should be documented in the next release.\n\n"

    md += "---\n\n"
    md += f"*Report generated by {meta['tool']} on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*\n"

    return md


def generate_html_report(data: Dict) -> str:
    """Generate HTML report with interactive features"""
    meta = data['metadata']
    cov = data['coverage']
    features = data['features']

    # Group features
    good = [f for f in features if f['status'] == 'good']
    partial = [f for f in features if f['status'] == 'partial']
    missing = [f for f in features if f['status'] == 'missing']
    high_pri = [f for f in missing if f['priority'] == 'high']
    medium_pri = [f for f in missing if f['priority'] == 'medium']
    low_pri = [f for f in missing if f['priority'] == 'low']

    # Calculate percentages for progress bars
    good_pct = (cov['by_status']['good'] / cov['total_features'] * 100) if cov['total_features'] > 0 else 0
    partial_pct = (cov['by_status']['partial'] / cov['total_features'] * 100) if cov['total_features'] > 0 else 0
    missing_pct = (cov['by_status']['missing'] / cov['total_features'] * 100) if cov['total_features'] > 0 else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documentation Coverage Report - {meta['project']}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 40px;
        }}
        h1 {{ color: #2c3e50; margin-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 40px; margin-bottom: 20px; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }}
        h3 {{ color: #7f8c8d; margin-top: 20px; }}
        .meta {{ color: #95a5a6; margin-bottom: 40px; }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .summary-card {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .summary-card h3 {{ margin: 0; font-size: 2em; color: #2c3e50; }}
        .summary-card p {{ margin: 5px 0 0; color: #7f8c8d; }}
        .coverage-bar {{
            width: 100%;
            height: 30px;
            background: #ecf0f1;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
        }}
        .coverage-fill {{
            height: 100%;
            background: linear-gradient(90deg, #27ae60, #2ecc71);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: bold;
            margin-left: 10px;
        }}
        .badge-good {{ background: #27ae60; color: white; }}
        .badge-partial {{ background: #f39c12; color: white; }}
        .badge-missing {{ background: #e74c3c; color: white; }}
        .feature-card {{
            background: #f9f9f9;
            padding: 15px;
            margin: 15px 0;
            border-radius: 6px;
            border-left: 4px solid #3498db;
        }}
        .feature-card h4 {{ margin-bottom: 10px; color: #2c3e50; }}
        .feature-meta {{ color: #7f8c8d; font-size: 0.9em; margin: 5px 0; }}
        .priority-high {{ border-left-color: #e74c3c; }}
        .priority-medium {{ border-left-color: #f39c12; }}
        .priority-low {{ border-left-color: #95a5a6; }}
        .keyword-list {{ color: #7f8c8d; font-size: 0.85em; margin-top: 8px; }}
        .keyword {{ background: #ecf0f1; padding: 2px 8px; border-radius: 3px; margin-right: 5px; }}
        footer {{ margin-top: 60px; text-align: center; color: #95a5a6; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Documentation Coverage Report</h1>
        <div class="meta">
            <strong>Project:</strong> {meta['project']}<br>
            <strong>Generated:</strong> {datetime.fromisoformat(meta['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}<br>
            <strong>Tool:</strong> {meta['tool']} v{meta['version']}
        </div>

        <h2>Coverage Summary</h2>
        <div class="coverage-bar">
            <div class="coverage-fill" style="width: {cov['coverage_percent']}%">
                {cov['coverage_percent']}%
            </div>
        </div>

        <div class="summary-grid">
            <div class="summary-card">
                <h3>{cov['total_features']}</h3>
                <p>Total Features</p>
            </div>
            <div class="summary-card">
                <h3>{cov['documented']}</h3>
                <p>Documented</p>
            </div>
            <div class="summary-card">
                <h3>{cov['gap']}</h3>
                <p>Missing Docs</p>
            </div>
            <div class="summary-card">
                <h3>{cov['by_status']['good']}</h3>
                <p>Fully Documented</p>
            </div>
        </div>

        <h2>✅ Fully Documented Features ({len(good)})</h2>
"""

    for f in good:
        html += f"""
        <div class="feature-card">
            <h4>{f['name']} <span class="status-badge badge-good">GOOD</span></h4>
            <div class="feature-meta">
                <strong>Tests:</strong> {f['test_count']} |
                <strong>Class:</strong> {f['test_class']}
            </div>
        </div>
"""

    if partial:
        html += f"""
        <h2>⚠️ Partially Documented Features ({len(partial)})</h2>
"""
        for f in partial:
            html += f"""
        <div class="feature-card">
            <h4>{f['name']} <span class="status-badge badge-partial">PARTIAL</span></h4>
            <div class="feature-meta">
                <strong>Tests:</strong> {f['test_count']} |
                <strong>README:</strong> {'✅' if f['in_readme'] else '❌'} |
                <strong>Docs:</strong> {'✅' if f['in_docs'] else '❌'}
            </div>
        </div>
"""

    if missing:
        html += f"""
        <h2>❌ Missing Documentation ({len(missing)})</h2>
"""
        if high_pri:
            html += f"<h3>🔴 High Priority ({len(high_pri)})</h3>"
            for f in high_pri:
                keywords_html = ' '.join([f'<span class="keyword">{kw}</span>' for kw in f['keywords'][:5]])
                html += f"""
        <div class="feature-card priority-high">
            <h4>{f['name']} <span class="status-badge badge-missing">MISSING</span></h4>
            <div class="feature-meta">
                <strong>Tests:</strong> {f['test_count']} |
                <strong>Class:</strong> {f['test_class']}
            </div>
            <div class="keyword-list">
                <strong>Keywords:</strong> {keywords_html}
            </div>
        </div>
"""

        if medium_pri:
            html += f"<h3>🟡 Medium Priority ({len(medium_pri)})</h3>"
            for f in medium_pri:
                keywords_html = ' '.join([f'<span class="keyword">{kw}</span>' for kw in f['keywords'][:5]])
                html += f"""
        <div class="feature-card priority-medium">
            <h4>{f['name']} <span class="status-badge badge-missing">MISSING</span></h4>
            <div class="feature-meta">
                <strong>Tests:</strong> {f['test_count']} |
                <strong>Class:</strong> {f['test_class']}
            </div>
            <div class="keyword-list">
                <strong>Keywords:</strong> {keywords_html}
            </div>
        </div>
"""

    html += f"""
        <footer>
            Report generated by {meta['tool']} on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}
        </footer>
    </div>
</body>
</html>
"""

    return html


def main():
    parser = argparse.ArgumentParser(
        description='Generate documentation coverage reports'
    )
    parser.add_argument(
        '--format',
        choices=['md', 'html'],
        required=True,
        help='Output format'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='doc-coverage.json',
        help='Input JSON file (default: doc-coverage.json)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path (default: auto-generated)'
    )
    args = parser.parse_args()

    # Load data
    input_path = Path(args.input)
    print(f"📖 Loading coverage data from {input_path}...")
    data = load_coverage_data(input_path)

    # Generate report
    if args.format == 'md':
        print("📝 Generating Markdown report...")
        content = generate_markdown_report(data)
        default_output = 'doc-coverage-report.md'
    else:  # html
        print("🌐 Generating HTML report...")
        content = generate_html_report(data)
        default_output = 'htmlcov/doc-coverage.html'

    # Write output
    output_path = Path(args.output if args.output else default_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)

    print(f"✅ Report generated: {output_path}")
    print(f"   Coverage: {data['coverage']['coverage_percent']}%")
    print(f"   Format: {args.format.upper()}")


if __name__ == '__main__':
    main()
