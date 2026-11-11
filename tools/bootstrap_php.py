"""Prepare a pinned standalone Windows PHP. Never replaces XAMPP, PATH, registry or app data."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import urllib.request
import zipfile

from runtime_spec import (PHP_VERSION, PHP_WINDOWS_URL, PHP_WINDOWS_SHA256,
                         PHP_COMPATIBILITY_VERSION, PHP_COMPATIBILITY_WINDOWS_URL,
                         PHP_COMPATIBILITY_WINDOWS_SHA256, CA_URL, CA_SHA256, REQUIRED_PHP_EXTENSIONS)


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def download(url, target, expected):
    if not url.startswith('https://'):
        raise ValueError('Only reviewed HTTPS artifacts are allowed.')
    with urllib.request.urlopen(url, timeout=60) as response, target.open('xb') as output:
        while block := response.read(1024 * 1024):
            output.write(block)
    if digest(target) != expected:
        raise ValueError('Upstream artifact hash mismatch; nothing will be executed.')


def extract_verified(archive_path, destination, expected):
    """Validate the complete archive before extracting any member."""
    if digest(archive_path) != expected:
        raise ValueError('Archive hash mismatch.')
    destination = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        seen = set()
        for item in archive.infolist():
            name = item.filename
            relative = PurePosixPath(name)
            mode = item.external_attr >> 16
            if (item.orig_filename != name or '\\' in name or ':' in name or relative.is_absolute() or '..' in relative.parts
                    or not relative.parts or stat.S_ISLNK(mode)
                    or name.casefold() in seen
                    or any(part.endswith((' ', '.')) or re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part)
                           for part in relative.parts)
                    or relative.parts[0].casefold() in {'bootstrap-downloads', 'php.ini', 'cacert.pem', 'runtime-manifest.json'}):
                raise ValueError('Unsafe or duplicate archive member.')
            seen.add(name.casefold())
            target = destination / Path(*relative.parts)
            if not target.resolve().is_relative_to(destination) or target.exists():
                raise ValueError('Archive must not overwrite an existing path.')
        if archive.testzip() is not None:
            raise ValueError('Archive CRC check failed.')
        archive.extractall(destination)


def doctor(executable, expected_version=PHP_VERSION):
    code = "echo json_encode(['version'=>PHP_VERSION,'binary'=>PHP_BINARY,'sapi'=>PHP_SAPI,'threadSafe'=>(bool)PHP_ZTS,'bits'=>PHP_INT_SIZE*8,'ini'=>php_ini_loaded_file(),'extensions'=>get_loaded_extensions(),'timezone'=>date_default_timezone_get(),'curlCa'=>ini_get('curl.cainfo'),'opensslCa'=>ini_get('openssl.cafile'),'bcryptCost'=>password_get_info(password_hash('fictitious-doctor-probe',PASSWORD_DEFAULT))['options']['cost']],JSON_THROW_ON_ERROR);"
    env = {key: value for key, value in os.environ.items() if key not in {'PHPRC', 'PHP_INI_SCAN_DIR'}}
    run = subprocess.run([str(executable), '-r', code], capture_output=True, check=True, text=True,
                         encoding='utf-8', env=env, timeout=20)
    if run.stderr.strip():
        raise RuntimeError('PHP emitted startup warnings; inspect the isolated runtime.')
    result = json.loads(run.stdout)
    if (result['version'] != expected_version or result['sapi'] != 'cli'
            or result['threadSafe'] or result['bits'] != 64
            or not REQUIRED_PHP_EXTENSIONS <= {name.lower() for name in result['extensions']}):
        raise RuntimeError('Runtime version, architecture or extensions do not match the profile.')
    return result


def bootstrap(destination, timezone, compatibility=False):
    destination = destination.absolute()
    if destination.resolve() != destination or destination.exists():
        raise ValueError('Choose a new independent destination without junctions or symlinks.')
    if not re.fullmatch(r'[A-Za-z_]+(?:/[A-Za-z_]+)*', timezone):
        raise ValueError('Invalid timezone.')
    destination.mkdir(parents=True, exist_ok=False)
    downloads = destination / 'bootstrap-downloads'
    downloads.mkdir()
    archive_path = downloads / 'php.zip'
    version, url, archive_hash = ((PHP_COMPATIBILITY_VERSION, PHP_COMPATIBILITY_WINDOWS_URL, PHP_COMPATIBILITY_WINDOWS_SHA256)
        if compatibility else (PHP_VERSION, PHP_WINDOWS_URL, PHP_WINDOWS_SHA256))
    download(url, archive_path, archive_hash)
    extract_verified(archive_path, destination, archive_hash)
    download(CA_URL, destination / 'cacert.pem', CA_SHA256)
    def ini_path(path):
        value = path.as_posix()
        if any(char in value for char in '\n\r"'):
            raise ValueError('Destination cannot be represented safely in php.ini.')
        return value
    configuration = (destination / 'php.ini-production').read_text(encoding='utf-8-sig')
    configuration += '\n\n[altoids-managed-runtime]\n'
    configuration += 'extension_dir="' + ini_path(destination / 'ext') + '"\n'
    for name in ['curl', 'mbstring', 'openssl', 'fileinfo', 'pdo_sqlite']:
        configuration += 'extension=' + name + '\n'
    configuration += 'curl.cainfo="' + ini_path(destination / 'cacert.pem') + '"\n'
    configuration += 'openssl.cafile="' + ini_path(destination / 'cacert.pem') + '"\n'
    configuration += 'date.timezone="' + timezone + '"\nexpose_php=Off\n'
    (destination / 'php.ini').write_text(configuration, encoding='utf-8')
    probe = doctor(destination / 'php.exe', version)
    files = {p.relative_to(destination).as_posix(): digest(p) for p in destination.rglob('*')
             if p.is_file() and not p.is_relative_to(downloads)}
    report = {'status':'STANDALONE_RUNTIME_VERIFIED_NO_ACTIVATION', 'version':version,
              'upstream':{'url':url, 'sha256':archive_hash},
              'caBundle':{'url':CA_URL, 'sha256':CA_SHA256}, 'probe':probe, 'files':files,
              'xamppModified':False, 'globalPathModified':False, 'appDataModified':False}
    (destination / 'runtime-manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--doctor', type=Path)
    parser.add_argument('--timezone', default='America/Costa_Rica')
    parser.add_argument('--compatibility', action='store_true', help='Prepare the reviewed 8.2 compatibility runtime only for QA.')
    args = parser.parse_args()
    if bool(args.destination) == bool(args.doctor):
        parser.error('Choose exactly one of --destination or --doctor.')
    report = (doctor(args.doctor, PHP_COMPATIBILITY_VERSION if args.compatibility else PHP_VERSION)
              if args.doctor else bootstrap(args.destination, args.timezone, args.compatibility))
    print(json.dumps({k:v for k,v in report.items() if k != 'files'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
