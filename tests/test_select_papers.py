import unittest

from tools.select_papers import classify_themes, choose_exact, is_main_paper, paper_score, semantic_scholar_record


class SelectPapersTests(unittest.TestCase):
    def test_vla_paper_gets_relevant_theme_and_score(self):
        row = {
            "title": "A Vision-Language-Action Model for Robot Manipulation",
            "abstract": "We learn a generalist policy from robot demonstrations.",
            "venue": "CoRL",
            "year": 2025,
            "cited_by_count": 0,
        }
        self.assertIn("VLA", classify_themes(row))
        self.assertGreater(paper_score(row, "AI"), 0)

    def test_unrelated_nlp_paper_is_not_relevant(self):
        row = {
            "title": "Improving Machine Translation with Better Tokenization",
            "abstract": "A tokenizer for bilingual text translation.",
            "venue": "ACL",
            "year": 2026,
            "cited_by_count": 0,
        }
        self.assertEqual(classify_themes(row), [])
        self.assertLessEqual(paper_score(row, "AI"), 0)

    def test_choose_exact_deduplicates_and_honors_count(self):
        rows = [
            {"title": "Robot World Model", "authors": "A", "venue": "ICML", "year": 2025,
             "abstract": "world model for robot control", "stable_id": "one"},
            {"title": "Robot World Model", "authors": "A", "venue": "NeurIPS", "year": 2025,
             "abstract": "world model for robot control", "stable_id": "two"},
            {"title": "Distributed LLM Inference", "authors": "B", "venue": "OSDI", "year": 2024,
             "abstract": "distributed inference serving", "stable_id": "three"},
        ]
        selected = choose_exact(rows, 2, "SYSTEMS")
        self.assertEqual(len(selected), 2)
        self.assertEqual(len({item["title"] for item in selected}), 2)

    def test_semantic_scholar_record_preserves_identifiers(self):
        work = {
            "paperId": "abc", "title": "Distributed LLM Inference", "year": 2024,
            "venue": "OSDI", "authors": [{"name": "A. Author"}],
            "externalIds": {"DOI": "10.1/example"}, "url": "https://example.test/paper",
            "openAccessPdf": {"url": "https://example.test/paper.pdf"},
            "abstract": "A serving system.", "citationCount": 12,
        }
        row = semantic_scholar_record(work, "OSDI")
        self.assertEqual(row["doi"], "10.1/example")
        self.assertEqual(row["pdf_url"], "https://example.test/paper.pdf")
        self.assertEqual(row["source"], "Semantic Scholar")

    def test_proceedings_and_workshops_are_not_main_papers(self):
        self.assertFalse(is_main_paper({"title": "OSDI 2026 Full Proceedings"}))
        self.assertFalse(is_main_paper({"title": "Proceedings of the Workshop on AI Systems"}))
        self.assertTrue(is_main_paper({"title": "A Fast Serving System for Language Models"}))

    def test_ai_system_titles_receive_infra_theme(self):
        row = {"title": "Accelerating DNN Training with Model Parallelism", "abstract": ""}
        self.assertIn("AI Infra", classify_themes(row))


if __name__ == "__main__":
    unittest.main()
