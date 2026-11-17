"""A dirty host checkout must not replace the sources pinned to installed firmware."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import verify
from build import ROOT


class VerifySourcesTests(unittest.TestCase):
    def test_uses_frozen_sources_and_never_hides_corrupt_snapshot_with_checkout(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as temp:
            base=Path(temp);build=base/'build';frozen=build/'source-snapshot';checkout=base/'checkout'
            frozen.mkdir(parents=True);checkout.mkdir();(frozen/'input').write_bytes(b'firmware input')
            (checkout/'input').write_bytes(b'later host changes')
            (build/'source-hashes.json').write_text(json.dumps({'input':hashlib.sha256(b'firmware input').hexdigest()}))
            with patch.object(verify,'ROOT',checkout):
                self.assertEqual(verify.verified_source_root(build),frozen)
                (frozen/'input').write_bytes(b'corruption');(checkout/'input').write_bytes(b'firmware input')
                with self.assertRaises(ValueError):verify.verified_source_root(build)

    def test_checks_current_sources_when_no_snapshot_exists(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as temp:
            base=Path(temp);build=base/'build';checkout=base/'checkout';build.mkdir();checkout.mkdir()
            (checkout/'input').write_bytes(b'new build')
            (build/'source-hashes.json').write_text(json.dumps({'input':hashlib.sha256(b'new build').hexdigest()}))
            with patch.object(verify,'ROOT',checkout):
                self.assertEqual(verify.verified_source_root(build),checkout)


if __name__=='__main__':unittest.main()
