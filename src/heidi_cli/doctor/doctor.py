from __future__ import annotations

import ast
import importlib
import inspect
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
import subprocess
import json
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

@dataclass
class DoctorIssue:
    """Represents an issue found by the doctor."""
    severity: str  # "error", "warning", "info"
    category: str  # "imports", "functions", "dependencies", "tests", "docs"
    file_path: str
    line_number: Optional[int]
    message: str
    suggestion: Optional[str]

class HeidiDoctor:
    """Comprehensive code health checker for Heidi CLI."""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.issues: List[DoctorIssue] = []
        self.console = Console()
        
    def run_full_checkup(self) -> Dict[str, Any]:
        """Run comprehensive doctor checks."""
        console.print("[bold blue]🩺 Running Heidi CLI Health Check...[/bold blue]\n")
        
        results = {
            "total_issues": 0,
            "by_severity": {"error": 0, "warning": 0, "info": 0},
            "by_category": {},
            "checks_passed": [],
            "checks_failed": [],
            "recommendations": []
        }
        
        checks = [
            ("📦 Dependencies", self._check_dependencies),
            ("🔗 Imports", self._check_imports),
            ("📋 Functions", self._check_functions),
            ("🧪 Tests", self._check_tests),
            ("📚 Documentation", self._check_documentation),
            ("⚙️ Configuration", self._check_configuration),
            ("🔀 CLI Integration", self._check_cli_integration),
            ("🏗️ Architecture", self._check_architecture),
        ]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            for check_name, check_func in checks:
                task = progress.add_task(f"{check_name}...", total=None)
                try:
                    check_result = check_func()
                    if check_result["passed"]:
                        results["checks_passed"].append(check_name)
                        progress.update(task, description=f"✅ {check_name}")
                    else:
                        results["checks_failed"].append(check_name)
                        progress.update(task, description=f"❌ {check_name}")
                        self.issues.extend(check_result["issues"])
                except Exception as e:
                    results["checks_failed"].append(check_name)
                    self.issues.append(DoctorIssue(
                        severity="error",
                        category="system",
                        file_path="doctor.py",
                        line_number=None,
                        message=f"Check failed: {str(e)}",
                        suggestion="Review the check implementation"
                    ))
                    progress.update(task, description=f"💥 {check_name}")
        
        # Calculate statistics
        for issue in self.issues:
            results["total_issues"] += 1
            results["by_severity"][issue.severity] += 1
            results["by_category"][issue.category] = results["by_category"].get(issue.category, 0) + 1
        
        return results
    
    def _check_dependencies(self) -> Dict[str, Any]:
        """Check project dependencies and requirements."""
        issues = []
        
        # Check pyproject.toml
        pyproject_path = self.project_root / "pyproject.toml"
        if not pyproject_path.exists():
            issues.append(DoctorIssue(
                severity="error",
                category="dependencies",
                file_path="pyproject.toml",
                line_number=None,
                message="pyproject.toml not found",
                suggestion="Create pyproject.toml with project dependencies"
            ))
            return {"passed": False, "issues": issues}
        
        try:
            import toml
            with open(pyproject_path, 'r') as f:
                config = toml.load(f)
            
            deps = config.get("project", {}).get("dependencies", [])
            dev_deps = config.get("project", {}).get("optional-dependencies", {}).get("dev", [])
            
            # Check for critical dependencies
            critical_deps = ["typer", "fastapi", "pydantic", "rich"]
            for dep in critical_deps:
                if not any(dep in d for d in deps + dev_deps):
                    issues.append(DoctorIssue(
                        severity="error",
                        category="dependencies",
                        file_path="pyproject.toml",
                        line_number=None,
                        message=f"Critical dependency '{dep}' not found",
                        suggestion=f"Add {dep} to dependencies"
                    ))
            
            # Check for HuggingFace integration
            if not any("huggingface_hub" in d for d in deps + dev_deps):
                issues.append(DoctorIssue(
                    severity="warning",
                    category="dependencies",
                    file_path="pyproject.toml",
                    line_number=None,
                    message="huggingface_hub not found in dependencies",
                    suggestion="Add huggingface_hub>=0.20.0 for HuggingFace integration"
                ))
            
        except Exception as e:
            issues.append(DoctorIssue(
                severity="error",
                category="dependencies",
                file_path="pyproject.toml",
                line_number=None,
                message=f"Error parsing pyproject.toml: {str(e)}",
                suggestion="Check pyproject.toml syntax"
            ))
        
        return {"passed": len(issues) == 0, "issues": issues}
    
    def _check_imports(self) -> Dict[str, Any]:
        """Check import consistency and circular dependencies."""
        issues = []
        
        # Find all Python files
        python_files = list(self.project_root.rglob("src/**/*.py"))
        
        # Build import graph
        import_graph = {}
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                imports = []
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module)
                
                import_graph[str(file_path)] = imports
            except Exception as e:
                issues.append(DoctorIssue(
                    severity="warning",
                    category="imports",
                    file_path=str(file_path),
                    line_number=None,
                    message=f"Could not parse imports: {str(e)}",
                    suggestion="Check file syntax"
                ))
        
        # Check for circular dependencies
        visited = set()
        rec_stack = set()
        
        def has_cycle(file_path: str) -> bool:
            if file_path in rec_stack:
                return True
            if file_path in visited:
                return False
            
            visited.add(file_path)
            rec_stack.add(file_path)
            
            for import_name in import_graph.get(file_path, []):
                # Find imported file
                for other_file in import_graph:
                    if import_name in other_file and other_file != file_path:
                        if has_cycle(other_file):
                            return True
            
            rec_stack.remove(file_path)
            return False
        
        for file_path in import_graph:
            if has_cycle(file_path):
                issues.append(DoctorIssue(
                    severity="error",
                    category="imports",
                    file_path=file_path,
                    line_number=None,
                    message="Circular dependency detected",
                    suggestion="Refactor to break circular import"
                ))
        
        return {"passed": len(issues) == 0, "issues": issues}
    
    def _check_functions(self) -> Dict[str, Any]:
        """Check function definitions and signatures."""
        issues = []
        
        python_files = list(self.project_root.rglob("src/**/*.py"))
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Check for docstrings
                        if not ast.get_docstring(node):
                            issues.append(DoctorIssue(
                                severity="warning",
                                category="functions",
                                file_path=str(file_path),
                                line_number=node.lineno,
                                message=f"Function '{node.name}' missing docstring",
                                suggestion="Add docstring explaining function purpose"
                            ))
                        
                        # Check for type hints
                        if not node.returns:
                            issues.append(DoctorIssue(
                                severity="info",
                                category="functions",
                                file_path=str(file_path),
                                line_number=node.lineno,
                                message=f"Function '{node.name}' missing return type hint",
                                suggestion="Add return type annotation"
                            ))
                        
                        # Check argument types
                        for arg in node.args.args:
                            if arg.annotation is None and arg.arg != 'self':
                                issues.append(DoctorIssue(
                                    severity="info",
                                    category="functions",
                                    file_path=str(file_path),
                                    line_number=node.lineno,
                                    message=f"Argument '{arg.arg}' in function '{node.name}' missing type hint",
                                    suggestion="Add type annotation"
                                ))
                        
                        # Check for empty functions
                        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                            issues.append(DoctorIssue(
                                severity="warning",
                                category="functions",
                                file_path=str(file_path),
                                line_number=node.lineno,
                                message=f"Function '{node.name}' is empty",
                                suggestion="Implement function or remove placeholder"
                            ))
                        
            except Exception as e:
                issues.append(DoctorIssue(
                    severity="warning",
                    category="functions",
                    file_path=str(file_path),
                    line_number=None,
                    message=f"Could not analyze functions: {str(e)}",
                    suggestion="Check file syntax"
                ))
        
        return {"passed": len(issues) == 0, "issues": issues}
    
    def _check_tests(self) -> Dict[str, Any]:
        """Check test coverage and test quality."""
        issues = []
        
        # Find test files
        test_files = list(self.project_root.rglob("tests/**/*.py"))
        src_files = list(self.project_root.rglob("src/**/*.py"))
        
        if len(test_files) == 0:
            issues.append(DoctorIssue(
                severity="error",
                category="tests",
                file_path="tests/",
                line_number=None,
                message="No test files found",
                suggestion="Create tests for core functionality"
            ))
        
        # Check for test coverage
        src_modules = set()
        for src_file in src_files:
            if src_file.name != "__init__.py":
                module_name = src_file.relative_to(self.project_root / "src").with_suffix("")
                src_modules.add(str(module_name).replace(os.sep, "."))
        
        tested_modules = set()
        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module and any(module in node.module for module in src_modules):
                            tested_modules.add(node.module)
            except Exception:
                pass
        
        # Check for untested modules
        untested = src_modules - tested_modules
        for module in untested:
            issues.append(DoctorIssue(
                severity="warning",
                category="tests",
                file_path=f"src/{module.replace('.', os.sep)}.py",
                line_number=None,
                message=f"Module '{module}' not tested",
                suggestion="Add tests for this module"
            ))
        
        return {"passed": len(issues) == 0, "issues": issues}
    
    def _check_documentation(self) -> Dict[str, Any]:
        """Check documentation quality and completeness."""
        issues = []
        
        # Check README
        readme_path = self.project_root / "README.md"
        if not readme_path.exists():
            issues.append(DoctorIssue(
                severity="error",
                category="docs",
                file_path="README.md",
                line_number=None,
                message="README.md not found",
                suggestion="Create comprehensive README with installation and usage instructions"
            ))
        else:
            with open(readme_path, 'r', encoding='utf-8') as f:
                readme_content = f.read()
            
            # Check for key sections
            required_sections = ["Installation", "Usage", "Commands"]
            for section in required_sections:
                if section not in readme_content:
                    issues.append(DoctorIssue(
                        severity="warning",
                        category="docs",
                        file_path="README.md",
                        line_number=None,
                        message=f"Missing '{section}' section in README",
                        suggestion=f"Add {section} section to README"
                    ))
        
        # Check docstring coverage
        python_files = list(self.project_root.rglob("src/**/*.py"))
        total_functions = 0
        documented_functions = 0
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        total_functions += 1
                        if ast.get_docstring(node):
                            documented_functions += 1
            except Exception:
                pass
        
        if total_functions > 0:
            coverage = (documented_functions / total_functions) * 100
            if coverage < 80:
                issues.append(DoctorIssue(
                    severity="warning",
                    category="docs",
                    file_path="src/",
                    line_number=None,
                    message=f"Low docstring coverage: {coverage:.1f}%",
                    suggestion="Add docstrings to improve documentation coverage"
                ))
        
        return {"passed": len(issues) == 0, "issues": issues}
    
    def _check_configuration(self) -> Dict[str, Any]:
        """Check configuration files and settings."""
        issues = []
        
        # Check .gitignore
        gitignore_path = self.project_root / ".gitignore"
        if not gitignore_path.exists():
            issues.append(DoctorIssue(
                severity="warning",
                category="configuration",
                file_path=".gitignore",
                line_number=None,
                message=".gitignore not found",
                suggestion="Create .gitignore to exclude sensitive files"
            ))
        else:
            with open(gitignore_path, 'r') as f:
                gitignore_content = f.read()
            
            # Check for important ignores
            required_ignores = ["__pycache__", "*.pyc", ".venv", "venv", ".heidi/"]
            for ignore in required_ignores:
                if ignore not in gitignore_content:
                    issues.append(DoctorIssue(
                        severity="info",
                        category="configuration",
                        file_path=".gitignore",
                        line_number=None,
                        message=f"Missing '{ignore}' in .gitignore",
                        suggestion=f"Add {ignore} to .gitignore"
                    ))
        
        return {"passed": len(issues) == 0, "issues": issues}
    
    def _check_cli_integration(self) -> Dict[str, Any]:
        """Check CLI command integration and consistency."""
        issues = []
        
        # Check CLI file
        cli_path = self.project_root / "src" / "heidi_cli" / "cli.py"
        if not cli_path.exists():
            issues.append(DoctorIssue(
                severity="error",
                category="cli",
                file_path="src/heidi_cli/cli.py",
                line_number=None,
                message="CLI module not found",
                suggestion="Create CLI module with command definitions"
            ))
            return {"passed": False, "issues": issues}
        
        try:
            with open(cli_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Find all typer apps and commands
            apps = []
            commands = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.endswith("_app"):
                            apps.append(target.id)
                elif isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name) and decorator.id == "command":
                            commands.append(node.name)
            
            # Check for help text in commands
            if commands:
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name in commands:
                        if not ast.get_docstring(node):
                            issues.append(DoctorIssue(
                                severity="warning",
                                category="cli",
                                file_path=str(cli_path),
                                line_number=node.lineno,
                                message=f"CLI command '{node.name}' missing help text",
                                suggestion="Add docstring with command description"
                            ))
            
            # Check for HuggingFace integration
            if "hf_app" not in content:
                issues.append(DoctorIssue(
                    severity="warning",
                    category="cli",
                    file_path=str(cli_path),
                    line_number=None,
                    message="HuggingFace CLI integration not found",
                    suggestion="Add HuggingFace commands for model management"
                ))
            
        except Exception as e:
            issues.append(DoctorIssue(
                severity="error",
                category="cli",
                file_path=str(cli_path),
                line_number=None,
                message=f"Error analyzing CLI: {str(e)}",
                suggestion="Check CLI module syntax"
            ))
        
        return {"passed": len(issues) == 0, "issues": issues}
    
    def _check_architecture(self) -> Dict[str, Any]:
        """Check project architecture and module organization."""
        issues = []
        
        # Check for expected directory structure
        expected_dirs = [
            "src/heidi_cli",
            "src/heidi_cli/model_host",
            "src/heidi_cli/integrations",
            "tests"
        ]
        
        for dir_path in expected_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                issues.append(DoctorIssue(
                    severity="warning",
                    category="architecture",
                    file_path=dir_path,
                    line_number=None,
                    message=f"Expected directory '{dir_path}' not found",
                    suggestion=f"Create {dir_path} directory"
                ))
        
        # Check for __init__.py files
        src_dirs = list(self.project_root.rglob("src/*"))
        for dir_path in src_dirs:
            if dir_path.is_dir():
                init_file = dir_path / "__init__.py"
                if not init_file.exists():
                    issues.append(DoctorIssue(
                        severity="info",
                        category="architecture",
                        file_path=str(dir_path / "__init__.py"),
                        line_number=None,
                        message=f"Missing __init__.py in {dir_path.name}",
                        suggestion="Create __init__.py to make directory a Python package"
                    ))
        
        return {"passed": len(issues) == 0, "issues": issues}
    
    def print_report(self, results: Dict[str, Any]) -> None:
        """Print comprehensive doctor report."""
        console.print("\n" + "=" * 80)
        console.print("[bold blue]🩺 Heidi CLI Health Report[/bold blue]")
        console.print("=" * 80 + "\n")
        
        # Summary
        summary_table = Table(title="Summary")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")
        
        summary_table.add_row("Total Issues", str(results["total_issues"]))
        summary_table.add_row("Errors", f"[red]{results['by_severity']['error']}[/red]")
        summary_table.add_row("Warnings", f"[yellow]{results['by_severity']['warning']}[/yellow]")
        summary_table.add_row("Info", f"[blue]{results['by_severity']['info']}[/blue]")
        summary_table.add_row("Checks Passed", f"[green]{len(results['checks_passed'])}[/green]")
        summary_table.add_row("Checks Failed", f"[red]{len(results['checks_failed'])}[/red]")
        
        console.print(summary_table)
        console.print()
        
        # Issues by category
        if results["by_category"]:
            category_table = Table(title="Issues by Category")
            category_table.add_column("Category", style="cyan")
            category_table.add_column("Count", justify="right")
            
            for category, count in sorted(results["by_category"].items()):
                category_table.add_row(category, str(count))
            
            console.print(category_table)
            console.print()
        
        # Failed checks
        if results["checks_failed"]:
            console.print("[bold red]❌ Failed Checks:[/bold red]")
            for check in results["checks_failed"]:
                console.print(f"  • {check}")
            console.print()
        
        # Detailed issues
        if self.issues:
            # Group issues by severity
            errors = [i for i in self.issues if i.severity == "error"]
            warnings = [i for i in self.issues if i.severity == "warning"]
            info = [i for i in self.issues if i.severity == "info"]
            
            if errors:
                console.print("[bold red]🚨 Errors:[/bold red]")
                for issue in errors[:10]:  # Limit to 10 for readability
                    console.print(f"  • {issue.file_path}:{issue.line_number or '?'} - {issue.message}")
                    if issue.suggestion:
                        console.print(f"    💡 {issue.suggestion}")
                if len(errors) > 10:
                    console.print(f"  ... and {len(errors) - 10} more errors")
                console.print()
            
            if warnings:
                console.print("[bold yellow]⚠️  Warnings:[/bold yellow]")
                for issue in warnings[:10]:
                    console.print(f"  • {issue.file_path}:{issue.line_number or '?'} - {issue.message}")
                    if issue.suggestion:
                        console.print(f"    💡 {issue.suggestion}")
                if len(warnings) > 10:
                    console.print(f"  ... and {len(warnings) - 10} more warnings")
                console.print()
            
            if info:
                console.print("[bold blue]ℹ️  Info:[/bold blue]")
                for issue in info[:10]:
                    console.print(f"  • {issue.file_path}:{issue.line_number or '?'} - {issue.message}")
                    if issue.suggestion:
                        console.print(f"    💡 {issue.suggestion}")
                if len(info) > 10:
                    console.print(f"  ... and {len(info) - 10} more info items")
                console.print()
        
        # Recommendations
        console.print("[bold green]🎯 Recommendations:[/bold green]")
        
        if results["by_severity"]["error"] > 0:
            console.print("  • Fix all errors before proceeding with development")
        
        if results["by_severity"]["warning"] > 0:
            console.print("  • Address warnings to improve code quality")
        
        if results["by_severity"]["info"] > 0:
            console.print("  • Consider info items for best practices")
        
        if len(results["checks_passed"]) == len(results["checks_passed"]) + len(results["checks_failed"]):
            console.print("  • 🎉 All checks passed! Code is in excellent health!")
        
        console.print("\n" + "=" * 80)

def run_doctor(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Run the doctor checkup."""
    doctor = HeidiDoctor(project_root)
    results = doctor.run_full_checkup()
    doctor.print_report(results)
    return results
