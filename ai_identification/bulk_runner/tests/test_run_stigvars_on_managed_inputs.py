"""Unit tests for run_stigvars_on_managed_inputs.py. boto3 is mocked; no AWS access."""
import io
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

try:
    import boto3  # noqa: F401
    from botocore.exceptions import ClientError
except ImportError:  # keep the tests runnable without the AWS SDK installed
    class ClientError(Exception):
        def __init__(self, error_response, operation_name):
            super().__init__(operation_name)
            self.response = error_response

    _botocore = types.ModuleType("botocore")
    _exceptions = types.ModuleType("botocore.exceptions")
    _exceptions.ClientError = ClientError
    _botocore.exceptions = _exceptions
    sys.modules.setdefault("boto3", types.ModuleType("boto3"))
    sys.modules.setdefault("botocore", _botocore)
    sys.modules.setdefault("botocore.exceptions", _exceptions)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import run_stigvars_on_managed_inputs as runner  # noqa: E402

LEGACY = ("avillach-73-bdcatalyst-etl", "dictionary/{dataset_id}/vars.tsv")
IN_BOUNDARY = ("bdc-etl-data-d0d6191", "data/dictionary/dictionary/{dataset_id}/vars.tsv")


def not_found():
    return ClientError({"Error": {"Code": "404"}}, "HeadObject")


class ResolveTemplateTest(unittest.TestCase):
    def test_default_source_is_legacy(self):
        self.assertEqual(runner.DEFAULT_SOURCE, "legacy")
        self.assertEqual(runner.resolve_vars_template(runner.DEFAULT_SOURCE, None), LEGACY)

    def test_in_boundary_bucket_and_key(self):
        self.assertEqual(runner.resolve_vars_template("in-boundary", None), IN_BOUNDARY)

    def test_vars_uri_overrides_source(self):
        uri = "s3://bdc-etl-data-d0d6191/avillach-73-bdcatalyst-etl/dictionary/{dataset_id}/vars.tsv"
        for source in ("legacy", "in-boundary"):
            self.assertEqual(
                runner.resolve_vars_template(source, uri),
                ("bdc-etl-data-d0d6191", "avillach-73-bdcatalyst-etl/dictionary/{dataset_id}/vars.tsv"),
            )

    def test_vars_uri_rejected(self):
        bad = {
            "missing placeholder": "s3://bucket/dictionary/phs000000/vars.tsv",
            "placeholder twice": "s3://bucket/{dataset_id}/{dataset_id}/vars.tsv",
            "bad scheme": "https://bucket/dictionary/{dataset_id}/vars.tsv",
            "no scheme": "bucket/dictionary/{dataset_id}/vars.tsv",
            "empty bucket": "s3:///dictionary/{dataset_id}/vars.tsv",
            "templated bucket": "s3://{dataset_id}/vars.tsv",
            "empty key": "s3://bucket/",
            "no key": "s3://bucket",
        }
        for name, uri in bad.items():
            with self.subTest(name):
                with self.assertRaises(ValueError):
                    runner.resolve_vars_template("legacy", uri)


class DatasetIdTest(unittest.TestCase):
    def test_valid(self):
        for dataset_id in ("phs000000", "phs999999", "phs123456", "phs123456.v1.p1"):
            with self.subTest(dataset_id):
                runner.validate_dataset_id(dataset_id)

    def test_invalid(self):
        for dataset_id in ("", " phs123456", "../phs123456", "phs123456/x", ".phs123456",
                           "phs 123456", "phs123456\n"):
            with self.subTest(dataset_id):
                with self.assertRaises(ValueError):
                    runner.validate_dataset_id(dataset_id)


class DownloadTest(unittest.TestCase):
    def test_download_uses_bucket_and_key(self):
        client = mock.Mock()
        with TemporaryDirectory() as tmp:
            for bucket, template in (LEGACY, IN_BOUNDARY):
                path = runner.download_vars_tsv(client, bucket, template, "phs000000", Path(tmp) / "phs000000")
                self.assertEqual(path, Path(tmp) / "phs000000" / "vars.tsv")
                client.download_file.assert_called_with(
                    bucket, template.replace("{dataset_id}", "phs000000"), str(path))

    def test_missing_object_is_skipped_and_reported(self):
        client = mock.Mock()
        client.download_file.side_effect = not_found()
        stderr = mock.MagicMock()
        with TemporaryDirectory() as tmp, mock.patch.object(sys, "stderr", stderr):
            path = runner.download_vars_tsv(client, *IN_BOUNDARY, "phs999999", Path(tmp) / "phs999999")
        self.assertIsNone(path)
        written = "".join(c.args[0] for c in stderr.write.call_args_list)
        self.assertIn("skip phs999999", written)
        self.assertIn("s3://bdc-etl-data-d0d6191/data/dictionary/dictionary/phs999999/vars.tsv", written)


class MainTest(unittest.TestCase):
    def run_main(self, argv, client=None):
        client = client or mock.Mock()
        stig = mock.Mock(return_value=True)
        with TemporaryDirectory() as tmp, \
                mock.patch.object(sys, "argv", ["prog", *argv]), \
                mock.patch.object(runner, "THIS_DIR", Path(tmp)), \
                mock.patch.object(runner.boto3, "client", create=True, return_value=client) as make_client, \
                mock.patch.object(runner, "run_stig_id_ai", stig):
            rc = runner.main()
        return rc, client, make_client, stig

    def test_default_reads_legacy(self):
        rc, client, _, stig = self.run_main(["--study-identifier", "phs123456"])
        self.assertEqual(rc, 0)
        self.assertEqual(client.download_file.call_args.args[:2],
                         ("avillach-73-bdcatalyst-etl", "dictionary/phs123456/vars.tsv"))
        stig.assert_called_once()

    def test_in_boundary_source(self):
        _, client, _, _ = self.run_main(["--source", "in-boundary", "--study-identifier", "phs123456"])
        self.assertEqual(client.download_file.call_args.args[:2],
                         ("bdc-etl-data-d0d6191", "data/dictionary/dictionary/phs123456/vars.tsv"))

    def test_vars_uri_override(self):
        uri = "s3://other-bucket/some/prefix/{dataset_id}/vars.tsv"
        _, client, _, _ = self.run_main(["--vars-uri", uri, "--study-identifier", "phs123456"])
        self.assertEqual(client.download_file.call_args.args[:2],
                         ("other-bucket", "some/prefix/phs123456/vars.tsv"))

    def test_invalid_vars_uri_exits_before_any_s3_call(self):
        for uri in ("s3://bucket/vars.tsv", "http://bucket/{dataset_id}", "s3:///{dataset_id}/vars.tsv"):
            with self.subTest(uri):
                client = mock.Mock()
                with mock.patch.object(runner.boto3, "client", create=True, return_value=client) as make_client, \
                        mock.patch.object(sys, "argv", ["prog", "--vars-uri", uri, "--study-identifier", "phs123456"]):
                    with self.assertRaises(SystemExit):
                        runner.main()
                make_client.assert_not_called()
                client.download_file.assert_not_called()

    def test_prints_the_source_used(self):
        for argv, expected in (
                (["--source", "in-boundary"],
                 "vars.tsv source (--source in-boundary): s3://bdc-etl-data-d0d6191/data/dictionary/dictionary/{dataset_id}/vars.tsv"),
                (["--vars-uri", "s3://other-bucket/p/{dataset_id}/vars.tsv"],
                 "vars.tsv source (--vars-uri): s3://other-bucket/p/{dataset_id}/vars.tsv")):
            with self.subTest(argv), mock.patch.object(sys, "stdout", new_callable=io.StringIO) as out:
                self.run_main([*argv, "--study-identifier", "phs123456"])
            self.assertIn(expected, out.getvalue())

    def test_invalid_study_identifier_exits_before_any_s3_call(self):
        client = mock.Mock()
        with mock.patch.object(runner.boto3, "client", create=True, return_value=client) as make_client, \
                mock.patch.object(sys, "argv", ["prog", "--study-identifier", "../phs123456"]):
            with self.assertRaises(SystemExit):
                runner.main()
        make_client.assert_not_called()
        client.download_file.assert_not_called()

    def test_missing_object_skipped_run_continues(self):
        client = mock.Mock()
        client.download_file.side_effect = [not_found(), None]
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "Managed_Inputs.csv"
            csv_path.write_text(
                "Study Identifier,Data is ready to process,Data Processed\n"
                "phs999999,Yes,No\nphs000000,Yes,No\nphs123456,No,No\n")
            rc, client, _, stig = self.run_main(["--input-csv", str(csv_path)], client)
        self.assertEqual(rc, 0)
        self.assertEqual(client.download_file.call_count, 2)
        stig.assert_called_once()

    def test_invalid_id_in_csv_is_skipped_without_s3_call(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "Managed_Inputs.csv"
            csv_path.write_text(
                "Study Identifier,Data is ready to process,Data Processed\n../phs999999,Yes,No\n")
            rc, client, _, stig = self.run_main(["--input-csv", str(csv_path)])
        self.assertEqual(rc, 0)
        client.download_file.assert_not_called()
        stig.assert_not_called()


if __name__ == "__main__":
    unittest.main()
