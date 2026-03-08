import unittest

from app.services.question_bank_service import build_question_bank


class QuestionBankTests(unittest.TestCase):
    def test_question_bank_is_static_and_guard_safe(self):
        questions = build_question_bank()

        self.assertGreater(len(questions), 20)
        self.assertFalse(any("tesla" in question.lower() for question in questions))
        self.assertFalse(any("the company's" in question.lower() for question in questions))
        self.assertTrue(all(question.endswith("?") for question in questions))


if __name__ == "__main__":
    unittest.main()
