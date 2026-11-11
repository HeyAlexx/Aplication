import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import ci_release
import prepare_code_release as release
import test_code_release_preparation as preparation

class ReleasePayloadHygieneTests(unittest.TestCase):
    setup_workspace=preparation.CodeReleasePreparationTests.setup_workspace

    def test_renamed_credentials_cannot_enter_preparation_or_built_archive(self):
        workspace,source,_=self.setup_workspace()
        payload=b'<?php // '+b'ghp_'+b'C'*40
        (source/'api/leak.php').write_bytes(payload)
        release.git(source,'add','api/leak.php');release.git(source,'commit','-qm','fictitious blocked payload')
        commit=release.git(source,'rev-parse','HEAD').decode().strip()
        with self.assertRaisesRegex(ValueError,'no publicable'):release.prepare(workspace,source,commit)
        self.assertFalse(any((workspace/'work/installation-plans').glob('*/code/api/leak.php')))
        package=workspace/'package'
        with patch.object(ci_release,'ROOT',source):
            with self.assertRaisesRegex(ValueError,'no publicable'):ci_release.build(package)
        self.assertFalse((package/'code.zip').exists())

    def test_matching_manifest_does_not_make_a_secret_payload_safe_to_execute(self):
        with tempfile.TemporaryDirectory(prefix='altoids-payload-') as temp:
            package=Path(temp);payload=b'ghp_'+b'D'*40;name='api/config/app.php'
            (package/'manifest.json').write_text(json.dumps({'commit':'1'*40,'files':{name:hashlib.sha256(payload).hexdigest()}}))
            with zipfile.ZipFile(package/'code.zip','w') as z:z.writestr(name,payload)
            with patch.object(ci_release.subprocess,'Popen') as process:
                with self.assertRaisesRegex(ValueError,'no publicable'):ci_release.smoke(package,'php')
                process.assert_not_called()

if __name__=='__main__':unittest.main()
