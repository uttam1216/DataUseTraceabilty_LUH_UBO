from unittest import TestCase
from src.traceability_manager import initialize_records


class Test(TestCase):

    def test_initialize_records(self):
        try:
            initialize_records()
        except ValueError:
            self.fail('Exception raised')
