"""Reviewed runtime versions and public upstream artifact hashes; no local paths/secrets."""
PHP_VERSION = '8.4.27'
PHP_COMPATIBILITY_VERSION = '8.2.35'
PYTHON_VERSION = '3.13.12'
NODE_VERSION = '22.22.0'
PHP_WINDOWS_URL = 'https://downloads.php.net/~windows/releases/php-8.4.27-1-nts-Win32-vs17-x64.zip'
PHP_WINDOWS_SHA256 = 'dbae154a0a89791f36c3d48e68bae797878333e7d6cb5721e74617de59b63ab7'
PHP_COMPATIBILITY_WINDOWS_URL = 'https://downloads.php.net/~windows/releases/php-8.2.35-1-nts-Win32-vs16-x64.zip'
PHP_COMPATIBILITY_WINDOWS_SHA256 = 'ebe75134c03869826cb1714d31fd5eb96afefa6d9fd35d786971c03020e7bce2'
CA_URL = 'https://curl.se/ca/cacert-2026-11-05.pem'
CA_SHA256 = '427c064216761a1e72a8b30f0d954d08cb6e4435a82091fb865afd20c8497285'
REQUIRED_PHP_EXTENSIONS = {'curl', 'mbstring', 'openssl', 'fileinfo', 'json', 'session', 'pdo_sqlite'}
