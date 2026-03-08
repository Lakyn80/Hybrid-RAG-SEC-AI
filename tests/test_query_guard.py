import unittest

from app.services.query_guard import is_query_allowed


class QueryGuardTests(unittest.TestCase):
    def test_allows_company_and_form_queries(self):
        self.assertTrue(is_query_allowed("What legal risks did Apple mention in its 10-K?"))

    def test_allows_domain_topic_queries(self):
        self.assertTrue(is_query_allowed("What litigation risks are described in the filings?"))

    def test_blocks_irrelevant_queries(self):
        self.assertFalse(is_query_allowed("Did Elon Musk go to a bar yesterday?"))
        self.assertFalse(is_query_allowed("What is the weather?"))
        self.assertFalse(is_query_allowed("Tell me a joke"))


if __name__ == "__main__":
    unittest.main()
