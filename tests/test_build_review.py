import unittest

from tools.build_review import abstract_sentences, clean_text, join_pdf_linebreaks, paper_note, slug_heading


class BuildReviewTests(unittest.TestCase):
    def test_abstract_sentences_keeps_a_short_extract(self):
        text = "We learn a policy for robot manipulation. The policy improves success on three tasks."
        self.assertEqual(
            abstract_sentences(text, 2),
            "We learn a policy for robot manipulation. The policy improves success on three tasks.",
        )

    def test_paper_note_marks_title_only_inference(self):
        row = {
            "title": "World Models for Robot Control", "authors": "A. Author", "venue": "CoRL",
            "year": "2025", "themes": "World Model", "selection_score": "70", "landing_url": "https://example.test",
        }
        note = paper_note(row, "", "标题/主题推断")
        self.assertIn("标题/主题推断", note)
        self.assertIn("World Models for Robot Control", note)

    def test_slug_heading_is_stable(self):
        self.assertEqual(slug_heading("Vision-Language-Action / VLA"), "Vision-Language-Action-VLA")

    def test_markdown_text_removes_inline_latex_delimiters(self):
        row = {
            "title": "$\\phi$-DPO_with_score", "authors": "A", "venue": "CVPR", "year": "2026",
            "themes": "Supporting Perception", "selection_score": "40", "landing_url": "https://example.test",
        }
        note = paper_note(row, "$\\phi$ improves_model.", "索引摘要")
        self.assertNotIn("$", note)
        self.assertNotIn("\\phi", note)

    def test_clean_text_removes_pdf_control_characters(self):
        self.assertEqual(clean_text("camera\x00 motions\x1b"), "camera motions")

    def test_join_pdf_linebreaks_rejoins_split_words(self):
        self.assertEqual(join_pdf_linebreaks("learn- ing is ef- ficient"), "learning is efficient")


if __name__ == "__main__":
    unittest.main()
