"""Reproducible QA on public code and fictitious data; never runs against an operational store."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

from prepare_code_release import code_path, read_inside
from runtime_spec import PHP_VERSION, PHP_COMPATIBILITY_VERSION, PYTHON_VERSION, NODE_VERSION, REQUIRED_PHP_EXTENSIONS

ROOT = Path(__file__).resolve().parents[1]


def public_code(source):
    result = {}
    for root, directories, names in os.walk(source):
        directories[:] = [name for name in directories if name in {'api','Html','css','js','img','tests','tools','docs','.github','qa'}]
        # Below a public root, traverse normal code directories, never private/generated trees.
        if Path(root) != source:
            directories[:] = [p.name for p in Path(root).iterdir() if p.is_dir()
                and p.name not in {'node_modules','__pycache__','.git','data','runtime','outputs','backups'}]
        for name in names:
            relative = (Path(root) / name).relative_to(source).as_posix()
            if code_path(relative):
                result[relative] = read_inside(source, relative)
    return result


def fixture(source, destination):
    """Copy allowlisted code only. Never copy source data, descriptors, OAuth or secrets."""
    source = source.resolve()
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    code = public_code(source)
    for name, payload in code.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    for name in ['data','backups','outputs']:
        (destination / name).mkdir(exist_ok=True)
    template = {'genre':'Anime', 'status':'Activo', 'format':'Serie', 'chapters':12,
                'emissionYear':2026, 'emissionSeason':'Fall', 'seasonsCount':1,
                'productionStatus':'Finalizado', 'image':'https://example.invalid/fixture.png',
                'description':'Fictitious QA content'}
    catalog = destination.parent / 'fixture-catalog'
    state = destination.parent / 'fixture-sync-state'
    catalog.mkdir()
    state.mkdir()
    collections = {}
    for kind, filename, count in [('anime','anime',90),('movies','peliculas',12),('series','series',12)]:
        collections[filename] = [dict(template, id=f'qa-{kind}-{i:03}', type=kind,
            title=('Princess ' if i % 20 == 0 else 'QA ') + kind + f' {i:03}',
            createdAt=f'2026-10-{i % 28 + 1:02}T12:00:00Z') for i in range(count)]
    collections['anime'][0].update(sourceCode='QA-0001', sourceRow=2)
    collections['noticias'] = [{'id':f'qa-news-{i}', 'title':f'QA news {i}', 'summary':'Fictitious summary',
        'content':'Fictitious news body', 'status':'publicada','visibilityStatus':'Visible',
        'category':'Anime','featured':False,'author':'QA fixture',
        'createdAt':'2026-10-01T12:00:00Z','image':'https://example.invalid/news.png'} for i in range(2)]
    for name in ['temporadas','episodios','anime-revisiones','anime-sheet-writeback','anime-hoja']:
        collections[name] = []
    for name, rows in collections.items():
        payload = json.dumps(rows, ensure_ascii=False).encode('utf-8')
        (catalog / (name + '.json')).write_bytes(payload)
        (destination / 'data' / (name + '.json')).write_bytes(payload)
    for name in ['usuarios','perfiles','configuraciones','favoritos','historial']:
        (destination / 'data' / (name + '.json')).write_text('[]\n', encoding='utf-8')
    descriptor = destination.parent / 'fixture-storage.json'
    descriptor.write_text(json.dumps({'environment':'isolated-qa-fictitious-data',
        'catalogDir':str(catalog), 'syncStateDir':str(state)}), encoding='utf-8')
    return descriptor, {name: hashlib.sha256(payload).hexdigest() for name, payload in code.items()}


def environment(temporary_root=None):
    result = {key:value for key,value in os.environ.items()
        if not key.startswith(('ALTOIDSS_','WATCHMODE','MAL_'))
        and key not in {'NODE_PATH','PHPRC','PHP_INI_SCAN_DIR'}}
    if temporary_root is not None:
        canonical = Path(temporary_root).resolve()
        if not canonical.is_dir():
            raise ValueError('Create the owned QA temporary directory before configuring child processes.')
        # Windows runners can inherit an 8.3 alias such as RUNNER~1. The recovery
        # guards intentionally reject indirect paths; use a canonical owned temp.
        result.update(TMP=str(canonical), TEMP=str(canonical), TMPDIR=str(canonical))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--php', default=os.environ.get('PHP_BIN') or shutil.which('php'))
    parser.add_argument('--node', default=shutil.which('node'))
    parser.add_argument('--suite', choices=['python','browser','all'], default='all')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-legacy-runtime', action='store_true', help='Isolated comparison only; never production.')
    parser.add_argument('--browser-channel', help='Optional local browser; default is the locked Chromium revision.')
    args = parser.parse_args()
    if not args.php or not args.node:
        parser.error('Set --php/PHP_BIN and install Node before running QA.')
    args.php = shutil.which(args.php) or str(Path(args.php).resolve())
    args.node = shutil.which(args.node) or str(Path(args.node).resolve())
    if not Path(args.php).is_file() or not Path(args.node).is_file():
        parser.error('The selected PHP or Node executable does not exist.')
    output = args.output.absolute()
    if output.resolve() != output or output == ROOT or ROOT.is_relative_to(output):
        parser.error('Choose a new output directory; it must not contain the source checkout.')
    output.mkdir(parents=True, exist_ok=False)
    temporary_base = Path(os.environ.get('RUNNER_TEMP') or tempfile.gettempdir()).resolve()
    if not temporary_base.is_dir():
        raise ValueError('The standard temporary base directory is unavailable.')
    temporary = tempfile.TemporaryDirectory(prefix='altoids-qa-', dir=temporary_base)
    owned_temporary = Path(temporary.name).resolve()
    if owned_temporary.parent != temporary_base:
        raise ValueError('Unexpected temporary directory boundary.')
    env = environment(owned_temporary)
    env.update(PHP_BIN=str(Path(args.php).resolve()), PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
        ALTOIDSS_QA_NODE_MODULES=str(ROOT / 'qa/node_modules'),
        PLAYWRIGHT_BROWSERS_PATH=os.environ.get('PLAYWRIGHT_BROWSERS_PATH', str(ROOT / 'runtime/qa-browsers')),
        ALTOIDSS_REQUIRE_BROWSER='1')
    if args.browser_channel:
        env['ALTOIDSS_BROWSER_CHANNEL'] = args.browser_channel
    report = {'status':'RUNNING','startedAt':datetime.now(timezone.utc).isoformat(),
              'source':str(ROOT),'output':str(output),'usesProductionData':False,
              'externalProviderRequests':False,'sheetsStarted':False,'checks':[]}
    windows = {'creationflags':subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}

    def command(label, argv, cwd, timeout=120):
        start = time.monotonic()
        run = subprocess.run([str(a) for a in argv], cwd=cwd, env=env, capture_output=True,
                             text=True, encoding='utf-8', timeout=timeout, **windows)
        (output / (label + '.log')).write_text(run.stdout + run.stderr, encoding='utf-8')
        entry = {'name':label,'exitCode':run.returncode,'seconds':round(time.monotonic()-start,3)}
        report['checks'].append(entry)
        if run.returncode:
            raise RuntimeError(label + ' failed; inspect its log in the output directory.')
        return run

    try:
        php = command('php-profile', [args.php,'-r',"echo json_encode(['version'=>PHP_VERSION,'extensions'=>get_loaded_extensions(),'timezone'=>date_default_timezone_get(),'binary'=>PHP_BINARY,'ini'=>php_ini_loaded_file()],JSON_THROW_ON_ERROR);"], ROOT)
        profile = json.loads(php.stdout)
        allowed = {PHP_VERSION, PHP_COMPATIBILITY_VERSION}
        if args.allow_legacy_runtime:
            allowed.add('8.2.12')
        if profile['version'] not in allowed or not REQUIRED_PHP_EXTENSIONS <= {name.lower() for name in profile['extensions']}:
            raise RuntimeError('PHP version or required extensions do not match the reviewed profile.')
        if sys.version.split()[0] != PYTHON_VERSION:
            raise RuntimeError('Use the Python patch version declared in tools/runtime_spec.py.')
        dependencies = {name:importlib.metadata.version(name) for name in ['openpyxl','et_xmlfile']}
        if dependencies != {'openpyxl':'3.1.5','et_xmlfile':'2.0.0'}:
            raise RuntimeError('Install qa/requirements.txt with --require-hashes in a clean virtual environment.')
        node = command('node-version', [args.node,'--version'], ROOT).stdout.strip().lstrip('v')
        if node != NODE_VERSION:
            raise RuntimeError('Use the Node patch version declared in tools/runtime_spec.py.')
        command('bootstrap-sri', [args.node,'-e',"require('./tests/browser-runtime.cjs').verifyBootstrapSri(process.cwd())"], ROOT)
        report['runtime'] = {'php':profile,'python':sys.version.split()[0], 'pythonExecutable':sys.executable,
                             'node':node,'pythonDependencies':dependencies}
        app = output / 'fixture/app'
        descriptor, hashes = fixture(ROOT, app)
        env.update(ALTOIDSS_STORAGE_CONFIG=str(descriptor), ALTOIDSS_TEST_SOURCE=str(app))
        report['codeFiles'] = len(hashes)
        report['sourceCodeSha256'] = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
        (output / 'source-code-hashes.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
        # Compile without executing operational Python tools or producing bytecode.
        for name in hashes:
            if name.endswith('.py'):
                compile((app/name).read_text(encoding='utf-8-sig'), name, 'exec')
        for index, name in enumerate(n for n in hashes if n.endswith('.php')):
            command(f'php-syntax-{index:03}', [args.php,'-l',app/name], app)
        for index, name in enumerate(n for n in hashes if n.endswith(('.js','.cjs'))):
            command(f'js-syntax-{index:03}', [args.node,'--check',app/name], app)
        for name in ['catalog-pagination-state.cjs','content-order.cjs','auth-fail-closed.cjs']:
            command(name, [args.node,app/'tests'/name], app)
        if args.suite in ['python','all']:
            run = command('python-regressions', [sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_*.py','-v'], app, 900)
            count = re.search(r'Ran (\d+) tests?', run.stderr)
            report['pythonTests'] = int(count.group(1)) if count else None
            if re.search(r'skipped[= ]', run.stderr):
                raise RuntimeError('QA complete must not silently omit tests; inspect python-regressions.log.')
        if args.suite in ['browser','all']:
            with socket.socket() as listener:
                listener.bind(('127.0.0.1',0))
                port = listener.getsockname()[1]
            env['ALTOIDSS_TEST_URL'] = f'http://127.0.0.1:{port}'
            out = (output/'fixture-server.stdout').open('wb')
            err = (output/'fixture-server.stderr').open('wb')
            server = subprocess.Popen([args.php,'-S',f'127.0.0.1:{port}','-t','.', 'server-router.php'],
                cwd=app, env=env, stdout=out, stderr=err, **windows)
            try:
                for _ in range(100):
                    with socket.socket() as probe:
                        if probe.connect_ex(('127.0.0.1',port)) == 0:
                            break
                    if server.poll() is not None:
                        raise RuntimeError('Isolated QA server exited before readiness.')
                    time.sleep(.1)
                else:
                    raise RuntimeError('Isolated QA server did not become ready.')
                for name in ['catalog-order-browser.cjs','catalog-mobile-browser.cjs','admin-content-responsive.cjs','api-workflow.cjs']:
                    command(name, [args.node, app/'tests'/name], app, 240)
            finally:
                if server.poll() is None:
                    server.terminate()
                try:
                    server.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    server.kill(); server.wait(timeout=5)
                out.close(); err.close()
            with socket.socket() as probe:
                report['fixtureServerClosed'] = probe.connect_ex(('127.0.0.1',port)) != 0
            if not report['fixtureServerClosed']:
                raise RuntimeError('Own fixture server did not close.')
        if {name:hashlib.sha256(payload).hexdigest() for name,payload in public_code(ROOT).items()} != hashes:
            raise RuntimeError('Source code changed while QA was running; rerun for a stable candidate.')
        report['sourceCodeUnchanged'] = True
        report['status'] = 'PASSED'
    except BaseException as error:
        report.update(status='FAILED', errorType=type(error).__name__, error=str(error))
        raise
    finally:
        # Remove only the canonical directory allocated by this invocation.
        if owned_temporary.resolve().parent != temporary_base:
            raise RuntimeError('Temporary directory moved outside the expected boundary; cleanup refused.')
        try:
            temporary.cleanup()
            report['ownedTemporaryDirectoryRemoved'] = not owned_temporary.exists()
        except BaseException:
            report.update(status='FAILED', error='Could not clean the owned QA temporary directory.')
            raise
        report['finishedAt'] = datetime.now(timezone.utc).isoformat()
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['status','sourceCodeSha256','codeFiles','runtime']}
                     | {'pythonTests':report.get('pythonTests'),'output':str(output)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
