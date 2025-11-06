#!/usr/bin/env python3
"""
Documentation Coverage Analyzer

Extracts features from test files and checks their presence in:
- README.md
- docs/
- notebooks/

Output: doc-coverage.json

Usage:
    python check_doc_coverage.py
    python check_doc_coverage.py --output custom-output.json
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple


class Feature:
    """Represents a tested feature"""

    def __init__(self, name: str, test_class: str, test_count: int, test_names: List[str], test_file: str = "", test_line: int = 0):
        self.name = name
        self.test_class = test_class
        self.test_count = test_count
        self.test_names = test_names
        self.test_file = test_file  # Path to test file
        self.test_line = test_line  # Line number of test class
        self.in_readme = False
        self.in_docs = False
        self.in_notebooks = False
        self.has_test_link = False  # Does doc have [test](...) link?
        self.readme_locations = []
        self.docs_locations = []
        self.notebook_locations = []
        self.test_link_locations = []  # Where [test] links were found
        self.keywords = self._extract_keywords()

    def _extract_keywords(self) -> Set[str]:
        """Extract searchable keywords from feature name"""
        # Convert test class name to keywords
        # TestPrefixBasedAutoNaming → ["prefix", "based", "auto", "naming"]
        words = re.findall(r'[A-Z][a-z]+', self.test_class)
        keywords = {w.lower() for w in words if len(w) > 2}  # Skip short words

        # Add feature name variations
        keywords.add(self.name.lower())
        name_spaced = self.name.replace('_', ' ').lower()
        keywords.add(name_spaced)

        # Add individual words from feature name
        for word in self.name.split('_'):
            if len(word) > 2:
                keywords.add(word.lower())

        return keywords

    @property
    def status(self) -> str:
        """Determine documentation status"""
        # Good = documented in README + docs + has [test] link
        if self.in_readme and self.in_docs and self.has_test_link:
            return "good"
        # Partial = documented but missing [test] link
        elif (self.in_readme or self.in_docs or self.in_notebooks) and not self.has_test_link:
            return "partial"
        # Also partial if has link but not in both README and docs
        elif self.has_test_link and not (self.in_readme and self.in_docs):
            return "partial"
        else:
            return "missing"

    @property
    def priority(self) -> str:
        """Determine priority based on test count and status"""
        if self.status != "missing":
            return "none"

        # Features with more tests are higher priority
        if self.test_count >= 5:
            return "high"
        elif self.test_count >= 3:
            return "medium"
        else:
            return "low"

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export"""
        return {
            "name": self.name,
            "test_class": self.test_class,
            "test_count": self.test_count,
            "test_names": self.test_names,
            "test_file": self.test_file,
            "test_line": self.test_line,
            "keywords": list(self.keywords),
            "in_readme": self.in_readme,
            "in_docs": self.in_docs,
            "in_notebooks": self.in_notebooks,
            "has_test_link": self.has_test_link,
            "readme_locations": self.readme_locations,
            "docs_locations": self.docs_locations,
            "notebook_locations": self.notebook_locations,
            "test_link_locations": self.test_link_locations,
            "status": self.status,
            "priority": self.priority
        }


def extract_features_from_tests(test_dir: Path) -> List[Feature]:
    """Extract features from test files"""
    features = []

    if not test_dir.exists():
        print(f"⚠️  Test directory not found: {test_dir}")
        return features

    # Find all test files
    test_files = list(test_dir.glob("test_*.py"))
    print(f"   Found {len(test_files)} test file(s)")

    for test_file in test_files:
        content = test_file.read_text()

        # Find test classes
        class_pattern = r'class (Test\w+):\s*\n\s*"""([^"]*?)"""'
        classes = re.findall(class_pattern, content)

        for class_name, class_doc in classes:
            # Find all test methods in this class
            # Match class definition to end of class or file
            class_pattern = rf'class {class_name}:.*?(?=\nclass |\Z)'
            class_match = re.search(class_pattern, content, re.DOTALL)

            if class_match:
                class_content = class_match.group()
                test_methods = re.findall(r'def (test_\w+)', class_content)
                test_count = len(test_methods)

                # Find line number of class definition
                lines = content.split('\n')
                test_line = 0
                for i, line in enumerate(lines, 1):
                    if f'class {class_name}:' in line:
                        test_line = i
                        break

                # Derive feature name from class name
                feature_name = class_name.replace('Test', '')
                # Convert CamelCase to snake_case
                feature_name = re.sub(r'(?<!^)(?=[A-Z])', '_', feature_name).lower()

                # Relative path to test file from project root
                rel_test_file = test_file.relative_to(test_dir.parent)

                feature = Feature(
                    feature_name,
                    class_name,
                    test_count,
                    test_methods,
                    test_file=str(rel_test_file),
                    test_line=test_line
                )
                features.append(feature)

    print(f"   Extracted {len(features)} feature(s)")
    return features


def check_file_for_keywords(file_path: Path, keywords: Set[str]) -> Tuple[bool, List[str], List[int]]:
    """
    Check if keywords appear in file

    Returns:
        (is_found, found_keywords, line_numbers)
    """
    try:
        content = file_path.read_text()
        lines = content.split('\n')

        found_keywords = []
        line_numbers = []

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            for keyword in keywords:
                if keyword in line_lower and keyword not in found_keywords:
                    found_keywords.append(keyword)
                    line_numbers.append(i)

        # Consider documented if at least 2 keywords found OR 30% of keywords
        threshold = max(2, len(keywords) * 0.3)
        is_documented = len(found_keywords) >= threshold

        return is_documented, found_keywords, line_numbers
    except Exception as e:
        print(f"   ⚠️  Error reading {file_path}: {e}")
        return False, [], []


def check_test_links_in_file(file_path: Path, feature: Feature) -> Tuple[bool, List[int]]:
    """
    Check if file contains [test](...) link in section titles for this feature.

    Pattern: ## Some Title [test](../tests/test_file.py#L123)
    or:      ## Some Title [🧪 test](../tests/test_file.py#L123)

    Returns:
        (has_link, line_numbers)
    """
    try:
        content = file_path.read_text()
        lines = content.split('\n')

        found_lines = []

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()

            # Check if this is a heading line
            if not line.startswith('#'):
                continue

            # Check if line contains any feature keywords
            has_keyword = any(kw in line_lower for kw in feature.keywords)
            if not has_keyword:
                continue

            # Check if line contains [test](...) or [🧪 test](...)
            test_link_pattern = r'\[(?:🧪\s*)?test\]\([^)]+\)'
            if re.search(test_link_pattern, line, re.IGNORECASE):
                found_lines.append(i)

        return len(found_lines) > 0, found_lines
    except Exception as e:
        print(f"   ⚠️  Error reading {file_path}: {e}")
        return False, []


def check_readme_coverage(features: List[Feature], readme_path: Path) -> None:
    """Check which features are mentioned in README"""
    if not readme_path.exists():
        print(f"   ⚠️  README not found: {readme_path}")
        return

    for feature in features:
        is_found, keywords, lines = check_file_for_keywords(readme_path, feature.keywords)
        feature.in_readme = is_found
        if is_found:
            location = f"README.md (lines: {','.join(map(str, lines[:3]))})"
            feature.readme_locations.append(location)

        # Check for [test] links in README
        has_link, link_lines = check_test_links_in_file(readme_path, feature)
        if has_link:
            feature.has_test_link = True
            location = f"README.md (lines: {','.join(map(str, link_lines))})"
            feature.test_link_locations.append(location)


def check_docs_coverage(features: List[Feature], docs_dir: Path) -> None:
    """Check which features are documented in docs/"""
    if not docs_dir.exists():
        print(f"   ⚠️  Docs directory not found: {docs_dir}")
        return

    # Find all markdown files in docs
    doc_files = list(docs_dir.glob("**/*.md"))
    print(f"   Found {len(doc_files)} doc file(s)")

    for feature in features:
        for doc_file in doc_files:
            is_found, keywords, lines = check_file_for_keywords(doc_file, feature.keywords)
            if is_found:
                feature.in_docs = True
                rel_path = doc_file.relative_to(docs_dir.parent)
                location = f"{rel_path} (lines: {','.join(map(str, lines[:3]))})"
                feature.docs_locations.append(location)

            # Check for [test] links in docs
            has_link, link_lines = check_test_links_in_file(doc_file, feature)
            if has_link:
                feature.has_test_link = True
                rel_path = doc_file.relative_to(docs_dir.parent)
                location = f"{rel_path} (lines: {','.join(map(str, link_lines))})"
                feature.test_link_locations.append(location)


def check_notebooks_coverage(features: List[Feature], project_root: Path) -> None:
    """Check which features are in Jupyter notebooks"""
    # Look for notebooks in common locations
    notebook_dirs = [
        project_root / "notebooks",
        project_root / "examples",
        project_root / "docs" / "notebooks"
    ]

    notebook_files = []
    for nb_dir in notebook_dirs:
        if nb_dir.exists():
            notebook_files.extend(nb_dir.glob("**/*.ipynb"))

    if not notebook_files:
        print(f"   ℹ️  No notebooks found")
        return

    print(f"   Found {len(notebook_files)} notebook(s)")

    for feature in features:
        for nb_file in notebook_files:
            try:
                # Parse notebook JSON
                nb_content = json.loads(nb_file.read_text())

                # Extract text from cells
                text_content = []
                for cell in nb_content.get('cells', []):
                    if cell.get('cell_type') in ['code', 'markdown']:
                        source = cell.get('source', [])
                        if isinstance(source, list):
                            text_content.extend(source)
                        else:
                            text_content.append(source)

                full_text = '\n'.join(text_content).lower()

                # Check for keywords
                found_keywords = [kw for kw in feature.keywords if kw in full_text]
                threshold = max(2, len(feature.keywords) * 0.3)

                if len(found_keywords) >= threshold:
                    feature.in_notebooks = True
                    rel_path = nb_file.relative_to(project_root)
                    location = f"{rel_path} (keywords: {','.join(found_keywords[:3])})"
                    feature.notebook_locations.append(location)
            except Exception as e:
                print(f"   ⚠️  Error reading notebook {nb_file}: {e}")


def calculate_statistics(features: List[Feature]) -> Dict:
    """Calculate coverage statistics"""
    total = len(features)

    # Count by status
    good = sum(1 for f in features if f.status == "good")
    partial = sum(1 for f in features if f.status == "partial")
    missing = sum(1 for f in features if f.status == "missing")

    # Count by location
    in_readme = sum(1 for f in features if f.in_readme)
    in_docs = sum(1 for f in features if f.in_docs)
    in_notebooks = sum(1 for f in features if f.in_notebooks)

    # Documented = good + partial
    documented = good + partial

    # Count by priority
    high_priority_gaps = sum(1 for f in features if f.priority == "high")
    medium_priority_gaps = sum(1 for f in features if f.priority == "medium")
    low_priority_gaps = sum(1 for f in features if f.priority == "low")

    return {
        "total_features": total,
        "documented": documented,
        "coverage_percent": round((documented / total * 100) if total > 0 else 0, 1),
        "gap": missing,
        "by_status": {
            "good": good,
            "partial": partial,
            "missing": missing
        },
        "by_location": {
            "readme": in_readme,
            "docs": in_docs,
            "notebooks": in_notebooks
        },
        "by_priority": {
            "high": high_priority_gaps,
            "medium": medium_priority_gaps,
            "low": low_priority_gaps
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description='Analyze documentation coverage from tests'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='doc-coverage.json',
        help='Output JSON file path (default: doc-coverage.json)'
    )
    args = parser.parse_args()

    # Paths
    project_root = Path(__file__).parent.parent
    test_dir = project_root / 'tests'
    readme_path = project_root / 'README.md'
    docs_dir = project_root / 'docs'

    print("\n" + "=" * 70)
    print("📊 DOCUMENTATION COVERAGE ANALYZER")
    print("=" * 70 + "\n")

    # Step 1: Extract features from tests
    print("🔍 Step 1: Analyzing test files...")
    features = extract_features_from_tests(test_dir)

    if not features:
        print("❌ No features found in tests!")
        sys.exit(1)

    # Step 2: Check README
    print("\n📖 Step 2: Checking README.md...")
    check_readme_coverage(features, readme_path)

    # Step 3: Check docs
    print("\n📚 Step 3: Checking docs/...")
    check_docs_coverage(features, docs_dir)

    # Step 4: Check notebooks
    print("\n📓 Step 4: Checking notebooks...")
    check_notebooks_coverage(features, project_root)

    # Step 5: Calculate statistics
    print("\n📊 Step 5: Calculating statistics...")
    stats = calculate_statistics(features)

    # Build output JSON
    output = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "project": project_root.name,
            "tool": "check_doc_coverage.py",
            "version": "1.0.0"
        },
        "coverage": stats,
        "features": [f.to_dict() for f in features]
    }

    # Write JSON
    output_path = Path(args.output)
    output_path.write_text(json.dumps(output, indent=2))

    print(f"\n💾 Results saved to: {output_path}")
    print("\n" + "=" * 70)
    print("📈 SUMMARY")
    print("=" * 70)
    print(f"Total features:        {stats['total_features']}")
    print(f"Documented:            {stats['documented']}")
    print(f"Coverage:              {stats['coverage_percent']}%")
    print(f"Gap:                   {stats['gap']} features")
    print("\nBy Status:")
    print(f"  ✅ Good:             {stats['by_status']['good']}")
    print(f"  ⚠️  Partial:          {stats['by_status']['partial']}")
    print(f"  ❌ Missing:          {stats['by_status']['missing']}")
    print("\nGap Priority:")
    print(f"  🔴 High:             {stats['by_priority']['high']}")
    print(f"  🟡 Medium:           {stats['by_priority']['medium']}")
    print(f"  🟢 Low:              {stats['by_priority']['low']}")
    print("=" * 70 + "\n")

    # Success
    sys.exit(0)


if __name__ == '__main__':
    main()
