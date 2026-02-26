#!/usr/bin/env python3
"""
Release Preparation Script for SmartAP

This script automates the release preparation process:
1. Validates version format
2. Updates version numbers across files
3. Generates changelog preview
4. Creates release branch (optional)
5. Validates release readiness

Usage:
    python scripts/prepare_release.py 3.1.0
    python scripts/prepare_release.py 3.1.0 --dry-run
    python scripts/prepare_release.py 3.1.0 --create-branch
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class ReleasePreparation:
    """Handle release preparation tasks."""

    def __init__(self, version: str, dry_run: bool = False):
        self.version = version
        self.dry_run = dry_run
        self.root_dir = Path(__file__).parent.parent
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate_version(self) -> bool:
        """Validate semantic version format."""
        pattern = r'^(\d+)\.(\d+)\.(\d+)(-[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*)?$'
        if not re.match(pattern, self.version):
            self.errors.append(f"Invalid version format: {self.version}")
            return False
        return True

    def check_git_status(self) -> bool:
        """Ensure working directory is clean."""
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            cwd=self.root_dir
        )
        if result.stdout.strip():
            self.warnings.append("Working directory has uncommitted changes")
            return False
        return True

    def check_branch(self) -> bool:
        """Ensure we're on main branch."""
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True,
            text=True,
            cwd=self.root_dir
        )
        branch = result.stdout.strip()
        if branch != 'main':
            self.warnings.append(f"Not on main branch (current: {branch})")
            return False
        return True

    def update_backend_version(self) -> bool:
        """Update version in backend config."""
        config_file = self.root_dir / 'backend' / 'src' / 'config.py'
        if not config_file.exists():
            self.warnings.append("Backend config.py not found")
            return False

        content = config_file.read_text(encoding='utf-8')
        
        # Update app_version field
        new_content = re.sub(
            r'app_version:\s*str\s*=\s*["\'][^"\']*["\']',
            f'app_version: str = "{self.version}"',
            content
        )

        if new_content == content:
            self.warnings.append("Could not find app_version in config.py")
            return False

        if not self.dry_run:
            config_file.write_text(new_content, encoding='utf-8')
        
        print(f"  ✓ Updated backend/src/config.py")
        return True

    def update_frontend_version(self) -> bool:
        """Update version in frontend package.json."""
        package_file = self.root_dir / 'frontend' / 'package.json'
        if not package_file.exists():
            self.warnings.append("Frontend package.json not found")
            return False

        content = json.loads(package_file.read_text(encoding='utf-8'))
        content['version'] = self.version

        if not self.dry_run:
            package_file.write_text(
                json.dumps(content, indent=2) + '\n',
                encoding='utf-8'
            )
        
        print(f"  ✓ Updated frontend/package.json")
        return True

    def update_helm_chart(self) -> bool:
        """Update version in Helm chart."""
        chart_file = self.root_dir / 'helm' / 'smartap' / 'Chart.yaml'
        if not chart_file.exists():
            self.warnings.append("Helm Chart.yaml not found")
            return False

        content = chart_file.read_text(encoding='utf-8')
        
        # Update version and appVersion
        new_content = re.sub(
            r'^version:\s*.*$',
            f'version: {self.version}',
            content,
            flags=re.MULTILINE
        )
        new_content = re.sub(
            r'^appVersion:\s*.*$',
            f'appVersion: "{self.version}"',
            new_content,
            flags=re.MULTILINE
        )

        if not self.dry_run:
            chart_file.write_text(new_content, encoding='utf-8')
        
        print(f"  ✓ Updated helm/smartap/Chart.yaml")
        return True

    def update_changelog(self) -> bool:
        """Update CHANGELOG.md with new version."""
        changelog_file = self.root_dir / 'CHANGELOG.md'
        if not changelog_file.exists():
            self.warnings.append("CHANGELOG.md not found")
            return False

        content = changelog_file.read_text(encoding='utf-8')
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Replace [Unreleased] with new version
        new_content = content.replace(
            '## [Unreleased]',
            f'## [Unreleased]\n\n## [{self.version}] - {today}'
        )

        if new_content == content:
            self.warnings.append("Could not find [Unreleased] section in CHANGELOG.md")
            return False

        if not self.dry_run:
            changelog_file.write_text(new_content, encoding='utf-8')
        
        print(f"  ✓ Updated CHANGELOG.md")
        return True

    def run_tests(self) -> bool:
        """Run test suite to ensure release readiness."""
        print("\n📋 Running tests...")
        
        result = subprocess.run(
            ['pytest', 'tests/', '-v', '--tb=short', '-q'],
            capture_output=True,
            text=True,
            cwd=self.root_dir / 'backend'
        )
        
        if result.returncode != 0:
            self.errors.append("Tests failed")
            print(result.stdout)
            print(result.stderr)
            return False
        
        print("  ✓ All tests passed")
        return True

    def check_security(self) -> bool:
        """Run security checks."""
        print("\n🔒 Running security checks...")
        
        # Check pip-audit
        result = subprocess.run(
            ['pip', 'install', 'pip-audit'],
            capture_output=True,
            cwd=self.root_dir / 'backend'
        )
        
        result = subprocess.run(
            ['pip-audit', '-r', 'requirements.txt', '--strict'],
            capture_output=True,
            text=True,
            cwd=self.root_dir / 'backend'
        )
        
        if result.returncode != 0:
            self.warnings.append("pip-audit found vulnerabilities")
            print(f"  ⚠ {result.stdout}")
        else:
            print("  ✓ No known vulnerabilities in Python dependencies")
        
        return True

    def create_release_branch(self) -> bool:
        """Create a release branch."""
        branch_name = f"release/v{self.version}"
        
        if self.dry_run:
            print(f"  Would create branch: {branch_name}")
            return True
        
        result = subprocess.run(
            ['git', 'checkout', '-b', branch_name],
            capture_output=True,
            text=True,
            cwd=self.root_dir
        )
        
        if result.returncode != 0:
            self.errors.append(f"Failed to create branch: {result.stderr}")
            return False
        
        print(f"  ✓ Created branch: {branch_name}")
        return True

    def create_release_commit(self) -> bool:
        """Create release commit with version updates."""
        if self.dry_run:
            print("  Would create release commit")
            return True
        
        # Stage changes
        subprocess.run(
            ['git', 'add', '-A'],
            cwd=self.root_dir
        )
        
        # Create commit
        result = subprocess.run(
            ['git', 'commit', '-m', f'chore(release): prepare v{self.version}'],
            capture_output=True,
            text=True,
            cwd=self.root_dir
        )
        
        if result.returncode != 0:
            self.errors.append(f"Failed to create commit: {result.stderr}")
            return False
        
        print(f"  ✓ Created release commit")
        return True

    def create_tag(self) -> bool:
        """Create git tag for release."""
        tag_name = f"v{self.version}"
        
        if self.dry_run:
            print(f"  Would create tag: {tag_name}")
            return True
        
        result = subprocess.run(
            ['git', 'tag', '-a', tag_name, '-m', f'Release {tag_name}'],
            capture_output=True,
            text=True,
            cwd=self.root_dir
        )
        
        if result.returncode != 0:
            self.errors.append(f"Failed to create tag: {result.stderr}")
            return False
        
        print(f"  ✓ Created tag: {tag_name}")
        return True

    def generate_changelog_preview(self) -> Optional[str]:
        """Generate changelog preview using git-cliff."""
        result = subprocess.run(
            ['git', 'cliff', '--unreleased', '--tag', f'v{self.version}'],
            capture_output=True,
            text=True,
            cwd=self.root_dir
        )
        
        if result.returncode == 0:
            return result.stdout
        return None

    def print_summary(self):
        """Print release preparation summary."""
        print("\n" + "=" * 60)
        print("📦 RELEASE PREPARATION SUMMARY")
        print("=" * 60)
        print(f"\nVersion: v{self.version}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if not self.errors:
            print("\n✅ Release preparation successful!")
            print("\nNext steps:")
            print(f"  1. Review changes: git diff")
            print(f"  2. Push branch: git push origin release/v{self.version}")
            print(f"  3. Push tag: git push origin v{self.version}")
            print(f"  4. Create PR to merge release branch into main")
            print(f"  5. GitHub Actions will handle the rest!")

    def run(self, create_branch: bool = False, skip_tests: bool = False) -> bool:
        """Run the full release preparation process."""
        print(f"\n🚀 Preparing release v{self.version}")
        if self.dry_run:
            print("   (DRY RUN - no changes will be made)\n")
        
        # Validations
        print("\n📋 Validating...")
        if not self.validate_version():
            self.print_summary()
            return False
        print("  ✓ Version format valid")
        
        self.check_git_status()
        self.check_branch()
        
        # Update version numbers
        print("\n📝 Updating version numbers...")
        self.update_backend_version()
        self.update_frontend_version()
        self.update_helm_chart()
        self.update_changelog()
        
        # Run tests
        if not skip_tests:
            if not self.run_tests():
                self.print_summary()
                return False
        
        # Security checks
        self.check_security()
        
        # Create branch if requested
        if create_branch:
            print("\n🌿 Creating release branch...")
            if not self.create_release_branch():
                self.print_summary()
                return False
        
        # Create commit and tag
        if not self.dry_run:
            print("\n📌 Creating release commit and tag...")
            self.create_release_commit()
            self.create_tag()
        
        # Print summary
        self.print_summary()
        
        return len(self.errors) == 0


def main():
    parser = argparse.ArgumentParser(
        description='Prepare a new SmartAP release',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 3.1.0              # Prepare release 3.1.0
  %(prog)s 3.1.0 --dry-run    # Preview changes without making them
  %(prog)s 3.1.0 --create-branch  # Also create release branch
  %(prog)s 3.1.0-beta.1       # Prepare pre-release
        """
    )
    
    parser.add_argument(
        'version',
        help='Version number (e.g., 3.1.0 or 3.1.0-beta.1)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without making them'
    )
    
    parser.add_argument(
        '--create-branch',
        action='store_true',
        help='Create a release branch'
    )
    
    parser.add_argument(
        '--skip-tests',
        action='store_true',
        help='Skip running tests'
    )
    
    args = parser.parse_args()
    
    prep = ReleasePreparation(args.version, args.dry_run)
    success = prep.run(
        create_branch=args.create_branch,
        skip_tests=args.skip_tests
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
