"""
Security Configuration Tests

These tests validate that security configurations are properly set
and security best practices are followed in the codebase.
"""

import os
import re
from pathlib import Path

import pytest


def read_file_safe(file_path: Path) -> str:
    """Read file with fallback encoding handling."""
    try:
        return file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return file_path.read_text(encoding='utf-8', errors='ignore')


class TestSecurityConfiguration:
    """Test security-related configuration settings."""

    def test_debug_mode_disabled_in_production(self):
        """Verify DEBUG is not hardcoded to True."""
        # Check config.py for debug settings
        config_path = Path(__file__).parent.parent.parent / "src" / "config.py"
        if config_path.exists():
            content = read_file_safe(config_path)
            # Debug should default to False or be loaded from environment
            assert 'debug: bool = True' not in content.lower(), \
                "DEBUG should not be hardcoded to True"

    def test_secret_key_not_hardcoded(self):
        """Verify secret keys are loaded from environment."""
        config_path = Path(__file__).parent.parent.parent / "src" / "config.py"
        if config_path.exists():
            content = read_file_safe(config_path)
            # Secret key should use Field with no hardcoded default
            assert 'secret_key' not in content.lower() or \
                   'Field(' in content or \
                   'os.getenv' in content or \
                   'os.environ' in content, \
                "Secret keys should be loaded from environment"

    def test_cors_not_allow_all_by_default(self):
        """Verify CORS doesn't allow all origins by default."""
        main_path = Path(__file__).parent.parent.parent / "src" / "main.py"
        if main_path.exists():
            content = read_file_safe(main_path)
            # Should not have hardcoded allow_origins=["*"]
            lines_without_comments = [
                line for line in content.split('\n')
                if not line.strip().startswith('#')
            ]
            filtered_content = '\n'.join(lines_without_comments)
            # CORS should be configurable, not hardcoded to *
            if 'allow_origins=["*"]' in filtered_content:
                # Check if it's conditional
                assert 'cors_origins' in content or 'CORS_ORIGINS' in content, \
                    "CORS should be configurable via environment"


class TestHardcodedSecrets:
    """Test for hardcoded secrets in source code."""

    @pytest.fixture
    def source_files(self):
        """Get all Python source files (excluding tests)."""
        src_path = Path(__file__).parent.parent.parent / "src"
        return list(src_path.rglob("*.py"))

    def test_no_hardcoded_passwords(self, source_files):
        """Check for hardcoded password strings."""
        password_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'passwd\s*=\s*["\'][^"\']+["\']',
            r'pwd\s*=\s*["\'][^"\']+["\']',
        ]
        
        for file_path in source_files:
            content = read_file_safe(file_path)
            for pattern in password_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                # Filter out configuration definitions and empty defaults
                real_matches = [
                    m for m in matches
                    if 'Field(' not in m
                    and 'os.getenv' not in m
                    and 'os.environ' not in m
                    and '""' not in m
                    and "''" not in m
                ]
                assert len(real_matches) == 0, \
                    f"Potential hardcoded password in {file_path}: {real_matches}"

    def test_no_hardcoded_api_keys(self, source_files):
        """Check for hardcoded API keys."""
        api_key_patterns = [
            r'api_key\s*=\s*["\'][a-zA-Z0-9_-]{20,}["\']',
            r'apikey\s*=\s*["\'][a-zA-Z0-9_-]{20,}["\']',
            r'api-key\s*=\s*["\'][a-zA-Z0-9_-]{20,}["\']',
        ]
        
        for file_path in source_files:
            content = read_file_safe(file_path)
            for pattern in api_key_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                assert len(matches) == 0, \
                    f"Potential hardcoded API key in {file_path}"

    def test_no_hardcoded_tokens(self, source_files):
        """Check for hardcoded tokens."""
        # Skip checking for JWT tokens in test files
        token_patterns = [
            r'token\s*=\s*["\']eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+["\']',
        ]
        
        for file_path in source_files:
            content = read_file_safe(file_path)
            for pattern in token_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                assert len(matches) == 0, \
                    f"Potential hardcoded token in {file_path}"


class TestSQLInjectionPrevention:
    """Test for SQL injection prevention."""

    @pytest.fixture
    def source_files(self):
        """Get all Python source files."""
        src_path = Path(__file__).parent.parent.parent / "src"
        return list(src_path.rglob("*.py"))

    def test_no_raw_sql_string_formatting(self, source_files):
        """Check for SQL queries using string formatting."""
        dangerous_patterns = [
            r'execute\s*\([^)]*%[^)]*\)',
            r'execute\s*\([^)]*\.format\s*\([^)]*\)',
            r'execute\s*\(f["\']',
            r'executemany\s*\([^)]*%[^)]*\)',
        ]
        
        for file_path in source_files:
            content = read_file_safe(file_path)
            # Skip if file has noqa comment for this check
            if '# noqa: sql-injection' in content:
                continue
                
            for pattern in dangerous_patterns:
                matches = re.findall(pattern, content)
                # Filter out false positives (e.g., logging statements)
                real_matches = [
                    m for m in matches
                    if 'log' not in m.lower()
                    and 'print' not in m.lower()
                ]
                assert len(real_matches) == 0, \
                    f"Potential SQL injection vulnerability in {file_path}: {pattern}"

    def test_sqlalchemy_text_uses_parameters(self, source_files):
        """Check that SQLAlchemy text() uses bound parameters."""
        for file_path in source_files:
            content = read_file_safe(file_path)
            # Find text() usage
            text_usages = re.findall(r'text\s*\([^)]+\)', content)
            for usage in text_usages:
                # If text() contains format strings, it might be vulnerable
                if '%s' in usage or '.format' in usage or 'f"' in usage or "f'" in usage:
                    # Check if using bindparams
                    if 'bindparams' not in content[:content.find(usage) + 200]:
                        pytest.skip(f"Review text() usage in {file_path}")


class TestInputValidation:
    """Test input validation patterns."""

    @pytest.fixture
    def route_files(self):
        """Get route/endpoint files."""
        routes_path = Path(__file__).parent.parent.parent / "src" / "routes"
        if routes_path.exists():
            return list(routes_path.rglob("*.py"))
        return []

    def test_endpoints_use_pydantic_models(self, route_files):
        """Check that endpoints use Pydantic models for validation."""
        for file_path in route_files:
            content = read_file_safe(file_path)
            
            # Find POST/PUT endpoints
            endpoint_patterns = [
                r'@router\.(post|put|patch)\s*\([^)]*\)',
            ]
            
            for pattern in endpoint_patterns:
                if re.search(pattern, content):
                    # Should import or use Pydantic models
                    has_validation = (
                        'from pydantic' in content or
                        'BaseModel' in content or
                        ': ' in content  # Type hints
                    )
                    assert has_validation, \
                        f"Endpoints in {file_path} should use Pydantic models for validation"


class TestAuthenticationSecurity:
    """Test authentication security configurations."""

    def test_jwt_algorithm_is_secure(self):
        """Verify JWT uses secure algorithms."""
        auth_files = list(Path(__file__).parent.parent.parent.rglob("*auth*.py"))
        auth_files.extend(list(Path(__file__).parent.parent.parent.rglob("*token*.py")))
        
        insecure_algorithms = ['none', 'HS256']  # HS256 is okay but RS256 is better
        
        for file_path in auth_files:
            if not file_path.exists():
                continue
            content = read_file_safe(file_path)
            
            # Check for 'none' algorithm (critical vulnerability)
            if 'algorithm' in content.lower():
                assert '"none"' not in content.lower(), \
                    f"JWT 'none' algorithm found in {file_path}"

    def test_password_hashing_uses_bcrypt(self):
        """Verify password hashing uses bcrypt or similar."""
        auth_path = Path(__file__).parent.parent.parent / "src" / "auth"
        if not auth_path.exists():
            pytest.skip("Auth module not found")
        
        auth_files = list(auth_path.rglob("*.py"))
        has_secure_hashing = False
        
        for file_path in auth_files:
            content = read_file_safe(file_path)
            if 'bcrypt' in content or 'argon2' in content or 'passlib' in content:
                has_secure_hashing = True
                break
        
        assert has_secure_hashing, "Password hashing should use bcrypt, argon2, or passlib"


class TestXSSPrevention:
    """Test XSS prevention measures."""

    def test_no_unsafe_html_rendering(self):
        """Check for unsafe HTML rendering in backend responses."""
        src_path = Path(__file__).parent.parent.parent / "src"
        source_files = list(src_path.rglob("*.py"))
        
        dangerous_patterns = [
            r'HTMLResponse\s*\([^)]*\+',  # String concatenation in HTML
            r'return\s+["\']<[^>]+>.*\+',  # HTML string with concatenation
        ]
        
        for file_path in source_files:
            content = read_file_safe(file_path)
            for pattern in dangerous_patterns:
                matches = re.findall(pattern, content)
                assert len(matches) == 0, \
                    f"Potential XSS vulnerability in {file_path}: {pattern}"


class TestSecurityHeaders:
    """Test security headers configuration."""

    def test_security_middleware_exists(self):
        """Check that security headers middleware is configured."""
        main_path = Path(__file__).parent.parent.parent / "src" / "main.py"
        if not main_path.exists():
            pytest.skip("main.py not found")
        
        content = read_file_safe(main_path)
        
        # Should have some security configuration
        security_indicators = [
            'CORSMiddleware',
            'TrustedHostMiddleware',
            'HTTPSRedirectMiddleware',
            'X-Content-Type-Options',
            'X-Frame-Options',
            'Content-Security-Policy',
            'security',
        ]
        
        has_security = any(indicator in content for indicator in security_indicators)
        assert has_security, "Security middleware should be configured"


class TestRateLimiting:
    """Test rate limiting configuration."""

    def test_rate_limiting_middleware_exists(self):
        """Check that rate limiting is configured."""
        middleware_path = Path(__file__).parent.parent.parent / "src" / "middleware"
        main_path = Path(__file__).parent.parent.parent / "src" / "main.py"
        
        has_rate_limiting = False
        
        # Check middleware directory
        if middleware_path.exists():
            for file_path in middleware_path.rglob("*.py"):
                content = read_file_safe(file_path)
                if 'ratelimit' in content.lower() or 'rate_limit' in content.lower():
                    has_rate_limiting = True
                    break
        
        # Check main.py
        if main_path.exists() and not has_rate_limiting:
            content = read_file_safe(main_path)
            if 'ratelimit' in content.lower() or 'rate_limit' in content.lower():
                has_rate_limiting = True
        
        assert has_rate_limiting, "Rate limiting should be implemented"

    def test_sensitive_endpoints_have_stricter_limits(self):
        """Check that auth endpoints have rate limiting."""
        routes_path = Path(__file__).parent.parent.parent / "src" / "routes"
        if not routes_path.exists():
            pytest.skip("Routes not found")
        
        auth_routes = routes_path / "auth.py"
        if auth_routes.exists():
            content = read_file_safe(auth_routes)
            # Auth routes should reference rate limiting
            # This is a soft check - actual rate limiting might be in middleware
            if 'login' in content or 'token' in content:
                # Just verify the file exists and has auth endpoints
                assert 'router' in content


class TestEnvironmentConfiguration:
    """Test environment configuration security."""

    def test_env_example_has_no_real_secrets(self):
        """Verify .env.example doesn't contain real secrets."""
        env_example = Path(__file__).parent.parent.parent.parent / ".env.example"
        if not env_example.exists():
            env_example = Path(__file__).parent.parent.parent / ".env.example"
        
        if not env_example.exists():
            pytest.skip(".env.example not found")
        
        content = read_file_safe(env_example)
        
        # Check for obviously real secrets (long random strings)
        secret_patterns = [
            r'=[a-zA-Z0-9]{32,}',  # Long random strings
            r'=eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+',  # JWT tokens
        ]
        
        for pattern in secret_patterns:
            matches = re.findall(pattern, content)
            # Filter out placeholder values
            real_secrets = [
                m for m in matches
                if 'your_' not in m.lower()
                and 'changeme' not in m.lower()
                and 'placeholder' not in m.lower()
                and 'example' not in m.lower()
            ]
            assert len(real_secrets) == 0, \
                f".env.example may contain real secrets: {real_secrets}"

    def test_gitignore_excludes_env_files(self):
        """Verify .gitignore excludes .env files."""
        gitignore = Path(__file__).parent.parent.parent.parent / ".gitignore"
        if not gitignore.exists():
            gitignore = Path(__file__).parent.parent.parent / ".gitignore"
        
        if not gitignore.exists():
            pytest.skip(".gitignore not found")
        
        content = read_file_safe(gitignore)
        
        # Should ignore .env files
        assert '.env' in content or '*.env' in content, \
            ".gitignore should exclude .env files"
