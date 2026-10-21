"""Local-only advanced-session inputs and pinned dependency checks."""
import hashlib,json,os,sys
from pathlib import Path
from setup import tv_address

def load(project,require_build=True):
    if sys.version_info<(3,12):raise ValueError('Advanced integration requires Python 3.12 or newer.')
    project=Path(project)
    path=project/'.setup/session.json'
    if not path.is_file():raise ValueError('Run setup.py advanced-session after reading docs/advanced-home.md.')
    session=json.loads(path.read_text())
    if set(session)!={'tv_ip','host_ip','sdb','root_source','payloads'}:raise ValueError('Invalid local session configuration.')
    tv_address(session['tv_ip']);tv_address(session['host_ip'])
    if not Path(session['sdb']).is_file():raise ValueError('Configured SDB executable is missing.')
    source=Path(session['root_source'])
    package=source/'src/samsung_tv_root'
    if source.is_symlink() or (source/'src').is_symlink() or package.is_symlink():raise ValueError('Unexpected linked source artifact.')
    for path in package.rglob('*'):
        if path.is_symlink() or (path.is_file() and path.suffix!='.py'):raise ValueError('Unexpected executable/cache artifact in root source; use a clean reviewed snapshot.')
    expected=json.loads((project/'tools/root-source-files.json').read_text())
    actual={p.relative_to(source/'src').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (source/'src/samsung_tv_root').rglob('*.py')}
    if actual!=expected:raise ValueError('Root source does not match the reviewed commit plus the supplied runtime-enumeration patch.')
    inputs=json.loads((project/'tools/root-build-inputs.json').read_text())
    for name,digest in inputs.items():
        path=source/name
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Root payload source does not match the reviewed build inputs.')
    native_inputs=json.loads((project/'tools/native-build-inputs.json').read_text())
    for name,digest in native_inputs.items():
        path=project/name
        if path.is_symlink() or path.parent.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Calm Home native source does not match the reviewed build inputs.')
    if Path(session['payloads']).resolve()!=(project/'.setup/root-payloads').resolve():raise ValueError('Use this project’s .setup/root-payloads build directory.')
    if require_build:
        record_path=project/'.setup/payload-build.json'
        if record_path.is_symlink() or not record_path.is_file():raise ValueError('Run setup.py build-advanced to record a reviewed-source build first.')
        record=json.loads(record_path.read_text())
        compatibility=json.loads((project/'compatibility.json').read_text())
        if record.get('nativeInputs')!=native_inputs or record.get('inputs')!=inputs or record.get('rootSourceCommit')!=compatibility['rootSourceCommit']:raise ValueError('Payload build provenance does not match the reviewed source.')
        outputs={directory+'/'+stem+suffix for directory,stems in [('root-payloads',['SamsungTvRootAgent','SamsungTvArchiveRoot']),('native',['CalmHomeTool'])] for stem in stems for suffix in ['.dll','.deps.json','.runtimeconfig.json']}
        if set(record.get('outputs',{}))!=outputs:raise ValueError('Incomplete payload build record.')
        for name,digest in record['outputs'].items():
            path=project/'.setup'/name
            if path.is_symlink() or path.parent.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Payload build output changed; rebuild from the reviewed source.')
    sys.dont_write_bytecode=True
    os.environ['SDB']=str(Path(session['sdb']).resolve())
    return session
