import unittest

from app.services.rag_service import (
    assemble_context,
    enforce_source_diversity,
    truncate_context,
)
from app.services.vector_service import filter_results_by_score


def make_result(
    material_id: int,
    title: str,
    chunk_index: int,
    document: str,
    similarity: float = 0.9,
):
    return {
        "id": f"{material_id}_{chunk_index}",
        "document": document,
        "metadata": {
            "material_id": material_id,
            "title": title,
            "chunk_index": chunk_index,
        },
        "distance": 1 - similarity,
        "similarity": similarity,
    }


class RetrievalQualityTests(unittest.TestCase):
    def test_score_filter_uses_cosine_similarity_and_keeps_metadata(self):
        accepted = make_result(1, "DBMS", 0, "Relevant", 0.8)
        rejected = make_result(2, "OS", 0, "Weak", 0.7)

        filtered = filter_results_by_score(
            [accepted, rejected],
            threshold=0.75,
        )

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["metadata"], accepted["metadata"])
        self.assertEqual(filtered[0]["similarity"], 0.8)

    def test_diversity_prefers_a_similarly_relevant_new_source(self):
        first = make_result(1, "DBMS", 0, "A", 0.91)
        duplicate = make_result(1, "DBMS", 1, "B", 0.90)
        second_source = make_result(2, "OS", 0, "C", 0.88)

        selected = enforce_source_diversity(
            [first, duplicate, second_source],
            limit=2,
        )

        self.assertEqual(selected, [first, second_source])

    def test_context_groups_sources_and_orders_chunks(self):
        context = assemble_context(
            [
                make_result(1, "DBMS Unit 1", 1, "second"),
                make_result(2, "Operating Systems", 0, "other"),
                make_result(1, "DBMS Unit 1", 0, "first"),
            ]
        )

        self.assertLess(context.index("[Chunk 1]\nfirst"), context.index("[Chunk 2]\nsecond"))
        self.assertEqual(context.count("Source: DBMS Unit 1"), 1)
        self.assertIn("Source: Operating Systems", context)

    def test_truncation_keeps_whole_chunks_and_source_labels(self):
        results = [
            make_result(1, "DBMS", 0, "a" * 20),
            make_result(1, "DBMS", 1, "b" * 20),
        ]
        context = assemble_context(results)
        first_chunk = "Source: DBMS\n\n[Chunk 1]\n" + "a" * 20

        truncated = truncate_context(context, max_chars=len(first_chunk))

        self.assertEqual(truncated, first_chunk)
        self.assertLessEqual(len(truncated), len(first_chunk))
        self.assertNotIn("b" * 20, truncated)


if __name__ == "__main__":
    unittest.main()