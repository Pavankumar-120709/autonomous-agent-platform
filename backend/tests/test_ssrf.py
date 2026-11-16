import pytest
from app.security.ssrf import validate_url_safe, SSRFValidationError


def test_ssrf_rejects_localhost_and_loopback():
    with pytest.raises(SSRFValidationError, match="blocked|restricted"):
        validate_url_safe("http://localhost:8000/secret")

    with pytest.raises(SSRFValidationError, match="restricted IP"):
        validate_url_safe("http://127.0.0.1:8080/admin")

    with pytest.raises(SSRFValidationError):
        validate_url_safe("http://127.0.0.2:80")


def test_ssrf_rejects_private_and_cloud_metadata():
    # Cloud metadata
    with pytest.raises(SSRFValidationError):
        validate_url_safe("http://169.254.169.254/latest/meta-data/")

    with pytest.raises(SSRFValidationError):
        validate_url_safe("http://metadata.google.internal/computeMetadata/v1/")

    # Private networks
    with pytest.raises(SSRFValidationError):
        validate_url_safe("http://10.0.0.1/internal")

    with pytest.raises(SSRFValidationError):
        validate_url_safe("http://192.168.1.1/router")

    with pytest.raises(SSRFValidationError):
        validate_url_safe("http://172.16.0.5/api")


def test_ssrf_rejects_invalid_schemes():
    with pytest.raises(SSRFValidationError, match="Invalid URL scheme"):
        validate_url_safe("file:///etc/passwd")

    with pytest.raises(SSRFValidationError, match="Invalid URL scheme"):
        validate_url_safe("ftp://ftp.example.com/file.txt")

    with pytest.raises(SSRFValidationError, match="Invalid URL scheme"):
        validate_url_safe("gopher://example.com")


def test_ssrf_accepts_valid_public_url():
    is_safe, canonical = validate_url_safe("https://example.com")
    assert is_safe is True
    assert canonical == "https://example.com"
