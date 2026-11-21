from unittest import TestCase

from cockpit.reliability import exercise


class RecoveryTests(TestCase):
    def test_concurrent_sessions_and_recovery(self):
        result = exercise(workers=2,rounds=1,people=144)
        self.assertEqual(result['measured_requests'],10)
        self.assertEqual(result['request_errors'],0)
        self.assertGreater(result['backup_bytes'],0)
        self.assertGreaterEqual(result['restored_sessions_revoked'],2)
        self.assertTrue(result['rejected_import_preserved_export'])
