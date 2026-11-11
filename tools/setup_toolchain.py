"""Prepare standalone PHP and a locked Python venv in a new folder; no activation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import venv

from bootstrap_php import bootstrap
from runtime_spec import PHP_VERSION, PYTHON_VERSION


def setup(destination):
    destination = destination.absolute()
    root = Path(__file__).resolve().parents[1]
    if destination.resolve() != destination or destination.exists() or root.is_relative_to(destination):
        raise ValueError('Use a new independent directory; existing environments are preserved.')
    if sys.version.split()[0] != PYTHON_VERSION:
        raise RuntimeError('Use Python ' + PYTHON_VERSION + ' to create this toolchain.')
    requirements = root / 'qa/requirements.txt'
    if not requirements.is_file():
        raise RuntimeError('The release must include qa/requirements.txt.')
    destination.mkdir(parents=True, exist_ok=False)
    php = bootstrap(destination / ('php-' + PHP_VERSION), 'America/Costa_Rica')
    python_dir = destination / 'python'
    venv.EnvBuilder(with_pip=True).create(python_dir)
    python = python_dir / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    subprocess.run([str(python), '-m', 'pip', 'install', '--disable-pip-version-check',
        '--no-cache-dir', '--require-hashes', '--only-binary=:all:', '-r', str(requirements)], check=True)
    probe = subprocess.check_output([str(python), '-B', '-c',
        "import importlib.metadata,json,sys;print(json.dumps({'python':sys.version.split()[0],'openpyxl':importlib.metadata.version('openpyxl'),'et_xmlfile':importlib.metadata.version('et_xmlfile')}))"], text=True)
    profile = json.loads(probe)
    if profile != {'python':PYTHON_VERSION,'openpyxl':'3.1.5','et_xmlfile':'2.0.0'}:
        raise RuntimeError('Python dependency profile mismatch.')
    config = {'schemaVersion':1,'phpVersion':PHP_VERSION,'pythonVersion':PYTHON_VERSION,
              'phpExecutable':php['probe']['binary'],'pythonExecutable':str(python)}
    (destination / 'toolchain.local.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    report = {'status':'TOOLCHAIN_PREPARED_NOT_ACTIVATED','php':PHP_VERSION,'python':profile,
              'config':str(destination/'toolchain.local.json'),
              'requirementsSha256':hashlib.sha256(requirements.read_bytes()).hexdigest(),
              'xamppModified':False,'globalEnvironmentModified':False,'appDataModified':False}
    (destination / 'toolchain-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Standalone ZIP bootstrap targets Windows x64; CI Linux uses the same PHP version via setup-php.')
    print(json.dumps(setup(args.destination)))
