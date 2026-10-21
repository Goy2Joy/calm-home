import hashlib,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.family_session import load

class AdvancedTests(unittest.TestCase):
    def fixture(self,folder):
        project=Path(folder);state=project/'.setup';source=state/'root-source';package=source/'src/samsung_tv_root'
        package.mkdir(parents=True);(project/'tools').mkdir();(package/'__init__.py').write_text('# verified source\n')
        expected={'samsung_tv_root/__init__.py':hashlib.sha256((package/'__init__.py').read_bytes()).hexdigest()}
        (project/'tools/root-source-files.json').write_text(json.dumps(expected))
        cs=source/'payloads/common/Agent.cs';cs.parent.mkdir(parents=True);cs.write_text('// reviewed\n')
        inputs={'payloads/common/Agent.cs':hashlib.sha256(cs.read_bytes()).hexdigest()}
        (project/'tools/root-build-inputs.json').write_text(json.dumps(inputs))
        native_source=project/'native/Program.cs';native_source.parent.mkdir();native_source.write_text('// reviewed native\n')
        native_inputs={'native/Program.cs':hashlib.sha256(native_source.read_bytes()).hexdigest()}
        (project/'tools/native-build-inputs.json').write_text(json.dumps(native_inputs))
        (project/'compatibility.json').write_text(json.dumps({'rootSourceCommit':'pinned'}))
        sdk=state/'sdb';sdk.write_text('tool')
        payloads=state/'root-payloads';payloads.mkdir();native=state/'native';native.mkdir()
        outputs={}
        for directory,stems in [(payloads,['SamsungTvRootAgent','SamsungTvArchiveRoot']),(native,['CalmHomeTool'])]:
            for stem in stems:
                for suffix in ['.dll','.deps.json','.runtimeconfig.json']:
                    p=directory/(stem+suffix);p.write_bytes(b'output');outputs[p.relative_to(state).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
        (state/'payload-build.json').write_text(json.dumps({'rootSourceCommit':'pinned','inputs':inputs,'nativeInputs':native_inputs,'outputs':outputs}))
        (state/'session.json').write_text(json.dumps({'tv_ip':'192.168.1.50','host_ip':'192.168.1.20','sdb':str(sdk),'root_source':str(source),'payloads':str(payloads)}))
        return project,package,payloads,cs

    def test_unverified_bytecode_and_native_replacements_are_rejected(self):
        for name in ['__init__.pyc','channel.so']:
            with tempfile.TemporaryDirectory() as td:
                project,package,_,_=self.fixture(td);(package/name).write_bytes(b'unsafe')
                with self.assertRaisesRegex(ValueError,'artifact'):load(project)

    def test_altered_payloads_and_source_cannot_pass_recorded_build(self):
        with tempfile.TemporaryDirectory() as td:
            project,_,payloads,cs=self.fixture(td)
            load(project)
            dll=payloads/'SamsungTvRootAgent.dll';dll.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'build'):load(project)
            dll.write_bytes(b'output');cs.write_text('// changed\n')
            with self.assertRaisesRegex(ValueError,'source'):load(project)

    def test_changed_native_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            project,_,_,_=self.fixture(td)
            load(project)
            (project/'native/Program.cs').write_text('// changed native\n')
            with self.assertRaisesRegex(ValueError,'native'):load(project)

if __name__=='__main__':unittest.main()
