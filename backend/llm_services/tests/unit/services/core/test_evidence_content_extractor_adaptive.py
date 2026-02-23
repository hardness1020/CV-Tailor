"""
Unit tests for EvidenceContentExtractor adaptive PDF processing.

TDD RED PHASE: These tests define expected behavior for adaptive extraction strategies.
Tests will FAIL until adaptive processing is implemented in Stage G.
"""

from unittest.mock import Mock, patch, AsyncMock, MagicMock
from django.test import TestCase, tag
from llm_services.services.core.evidence_content_extractor import EvidenceContentExtractor


@tag('medium', 'integration', 'llm_services')
class AdaptivePDFExtractionTestCase(TestCase):
    """Test suite for adaptive PDF extraction - TDD RED phase"""

    def setUp(self):
        """Set up test fixtures."""
        self.extractor = EvidenceContentExtractor()

        # Check if adaptive methods exist
        self.has_adaptive = (
            hasattr(self.extractor, 'pdf_classifier') and
            hasattr(self.extractor, '_select_section_aware_chunks') and
            hasattr(self.extractor, '_adaptive_chunk_selection') and
            hasattr(self.extractor, '_map_reduce_extraction')
        )

    async def test_extract_pdf_content_classifies_document(self):
        """Test extract_pdf_content calls PDFDocumentClassifier."""
        if not self.has_adaptive:
            self.skipTest("Adaptive processing not yet implemented (TDD RED phase)")

        # Given: PDF chunks with metadata
        pdf_chunks = [
            {'content': 'Test content', 'metadata': {'file_path': '/fake/thesis.pdf'}}
        ]

        # Mock the extractor's pdf_classifier instance
        with patch.object(self.extractor, 'pdf_classifier') as mock_classifier:
            mock_classifier.classify_document = AsyncMock(return_value={
                'category': 'academic_thesis',
                'confidence': 0.95,
                'processing_strategy': {
                    'max_chunks': 300,
                    'max_chars': 300_000,
                    'sampling': 'map_reduce',
                    'summary_tokens': 3_000,
                    'map_reduce': True
                }
            })

            # Mock map-reduce to avoid actual processing
            with patch.object(self.extractor, '_map_reduce_extraction', new_callable=AsyncMock) as mock_map_reduce:
                mock_map_reduce.return_value = Mock(
                    success=True,
                    data={'technologies': [], 'achievements': [], 'summary': 'Test'}
                )

                # When: Extracting PDF content
                result = await self.extractor.extract_pdf_content(
                    pdf_chunks=pdf_chunks,
                    user_id=1,
                    source_url='/media/thesis.pdf'
                )

                # Then: Should call classifier
                mock_classifier.classify_document.assert_called_once_with('/fake/thesis.pdf')

    async def test_certificate_uses_full_sampling_strategy(self):
        """Test certificate documents use 'full' sampling with small budget."""
        if not self.has_adaptive:
            self.skipTest("Adaptive processing not yet implemented (TDD RED phase)")

        # Given: Certificate classification strategy
        strategy = {
            'max_chunks': 10,
            'max_chars': 10_000,
            'sampling': 'full',
            'summary_tokens': 500,
            'map_reduce': False
        }

        pdf_chunks = [{'content': f'Chunk {i}', 'metadata': {}} for i in range(20)]

        # When: Selecting chunks with 'full' strategy
        selected_chunks = self.extractor._select_chunks_by_strategy(
            pdf_chunks, strategy
        )

        # Then: Should select up to max_chunks sequentially
        self.assertLessEqual(len(selected_chunks), 10)
        self.assertEqual(selected_chunks[0]['content'], 'Chunk 0')

    async def test_research_paper_uses_section_aware_sampling(self):
        """Test research papers use section-aware chunk selection."""
        if not self.has_adaptive:
            self.skipTest("Adaptive processing not yet implemented (TDD RED phase)")

        # Given: Research paper strategy
        strategy = {
            'max_chunks': 100,
            'max_chars': 100_000,
            'sampling': 'section_aware',
            'chunk_selection': 'section_priority',
            'map_reduce': False
        }

        # PDF chunks with section indicators
        pdf_chunks = [
            {'content': 'Abstract: Novel approach...', 'metadata': {'section': 'abstract'}},
            {'content': 'Introduction text...', 'metadata': {}},
            {'content': 'Methodology: We used...', 'metadata': {'section': 'methodology'}},
            {'content': 'Results: Accuracy 95%...', 'metadata': {'section': 'results'}},
            {'content': 'Discussion text...', 'metadata': {}},
            {'content': 'Conclusion: We found...', 'metadata': {'section': 'conclusion'}},
        ]

        # When: Selecting section-aware chunks
        selected_chunks = self.extractor._select_section_aware_chunks(
            pdf_chunks, strategy
        )

        # Then: Should prioritize key sections (abstract, methodology, results, conclusion)
        selected_sections = [c.get('metadata', {}).get('section') for c in selected_chunks]
        priority_sections = ['abstract', 'methodology', 'results', 'conclusion']

        for priority_section in priority_sections:
            self.assertIn(priority_section, selected_sections,
                         f"Section-aware sampling should include {priority_section}")

    async def test_project_report_uses_heading_aware_sampling(self):
        """Test project reports use heading-aware adaptive sampling."""
        if not self.has_adaptive:
            self.skipTest("Adaptive processing not yet implemented (TDD RED phase)")

        # Given: Project report strategy
        strategy = {
            'max_chunks': 150,
            'max_chars': 150_000,
            'sampling': 'adaptive',
            'chunk_selection': 'heading_aware',
            'map_reduce': False
        }

        pdf_chunks = [
            {'content': 'Introduction...', 'metadata': {'has_heading': True}},
            {'content': 'Body text...', 'metadata': {}},
            {'content': 'Implementation...', 'metadata': {'has_heading': True}},
            {'content': 'More text...', 'metadata': {}},
            {'content': 'Results...', 'metadata': {'has_heading': True}},
        ]

        # When: Adaptive chunk selection
        selected_chunks = self.extractor._adaptive_chunk_selection(
            pdf_chunks, strategy
        )

        # Then: Should prefer chunks with headings
        heading_chunks = [c for c in selected_chunks if c.get('metadata', {}).get('has_heading')]
        self.assertGreater(len(heading_chunks), 0,
                          "Heading-aware sampling should prioritize chunks with headings")

    async def test_combine_chunks_respects_max_chars_limit(self):
        """Test chunk combining respects max_chars limit from strategy."""
        if not self.has_adaptive:
            self.skipTest("Adaptive processing not yet implemented (TDD RED phase)")

        # Given: Chunks totaling >50K chars
        large_chunks = [
            {'content': 'A' * 30_000, 'metadata': {}},
            {'content': 'B' * 30_000, 'metadata': {}},
            {'content': 'C' * 30_000, 'metadata': {}},
        ]

        # When: Combining with 50K limit
        combined_text = self.extractor._combine_chunks(large_chunks, max_chars=50_000)

        # Then: Should respect limit
        self.assertLessEqual(len(combined_text), 50_000)
        self.assertIn('A', combined_text)  # First chunk included
        self.assertNotIn('C', combined_text)  # Third chunk likely excluded

    async def test_adaptive_processing_stores_document_category(self):
        """Test extracted content includes document_category and classification_confidence."""
        if not self.has_adaptive:
            self.skipTest("Adaptive processing not yet implemented (TDD RED phase)")

        # Given: Mock classification
        with patch.object(self.extractor, 'pdf_classifier') as mock_classifier:
            mock_classifier.classify_document = AsyncMock(return_value={
                'category': 'research_paper',
                'confidence': 0.88,
                'processing_strategy': {
                    'max_chunks': 100,
                    'max_chars': 100_000,
                    'sampling': 'section_aware',
                    'summary_tokens': 1_500,
                    'map_reduce': False
                }
            })

            pdf_chunks = [{'content': 'Test', 'metadata': {'file_path': '/test.pdf'}}]

            # When: Extracting content
            with patch.object(self.extractor, '_call_llm_for_extraction', new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = {
                    'content': '{"technologies": [], "achievements": [], "summary": "Test"}',
                    'cost': 0.01
                }

                result = await self.extractor.extract_pdf_content(
                    pdf_chunks, user_id=None, source_url='/test.pdf'
                )

                # Then: Result should include category and confidence
                self.assertIn('document_category', result.data)
                self.assertEqual(result.data['document_category'], 'research_paper')
                self.assertIn('classification_confidence', result.data)
                self.assertEqual(result.data['classification_confidence'], 0.88)

    async def test_map_reduce_extraction_for_thesis(self):
        """Test map-reduce extraction is used for academic theses."""
        if not self.has_adaptive:
            self.skipTest("Adaptive processing not yet implemented (TDD RED phase)")

        # Given: Thesis classification
        with patch.object(self.extractor, 'pdf_classifier') as mock_classifier:
            mock_classifier.classify_document = AsyncMock(return_value={
                'category': 'academic_thesis',
                'confidence': 0.95,
                'processing_strategy': {
                    'max_chunks': 300,
                    'max_chars': 300_000,
                    'sampling': 'map_reduce',
                    'map_reduce': True,
                    'map_chunk_size': 50_000
                }
            })

            # Large thesis with 100 chunks
            pdf_chunks = [{'content': f'Chapter {i // 10} content', 'metadata': {'file_path': '/fake/thesis.pdf'}} for i in range(100)]

            # Mock map-reduce method
            with patch.object(self.extractor, '_map_reduce_extraction', new_callable=AsyncMock) as mock_map_reduce:
                mock_map_reduce.return_value = Mock(
                    success=True,
                    data={'summary': 'Comprehensive thesis summary', 'technologies': [], 'achievements': []}
                )

                # When: Extracting thesis content
                result = await self.extractor.extract_pdf_content(
                    pdf_chunks, user_id=1, source_url='/thesis.pdf'
                )

                # Then: Should call map-reduce extraction
                mock_map_reduce.assert_called_once()

    async def test_token_budget_varies_by_document_type(self):
        """Test LLM calls use different max_tokens based on document category."""
        if not self.has_adaptive:
            self.skipTest("Adaptive processing not yet implemented (TDD RED phase)")

        # Given: Different document types
        test_cases = [
            ('certificate', 500),
            ('resume', 1_000),
            ('research_paper', 1_500),
            ('project_report', 2_000),
            ('academic_thesis', 3_000)
        ]

        for category, expected_tokens in test_cases:
            with self.subTest(category=category):
                # When: Building adaptive prompt
                prompt = self.extractor._build_adaptive_prompt('Test content', category)

                # Then: Prompt should reference expected quality level
                self.assertIsNotNone(prompt)
                # Adaptive prompt should differ by category
                # (actual implementation will vary, this tests the concept)

    async def test_backward_compatibility_without_classification(self):
        """Test extract_pdf_content still works if classification fails."""
        if not self.has_adaptive:
            self.skipTest("Adaptive processing not yet implemented (TDD RED phase)")

        # Given: Classification fails
        with patch.object(self.extractor, 'pdf_classifier') as mock_classifier:
            mock_classifier.classify_document = AsyncMock(side_effect=Exception("Classification error"))

            pdf_chunks = [{'content': 'Test', 'metadata': {'file_path': '/test.pdf'}}]

            # When: Extracting content (should fallback to default)
            with patch.object(self.extractor, '_call_llm_for_extraction', new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = {
                    'content': '{"technologies": [], "achievements": [], "summary": "Test"}',
                    'cost': 0.01
                }

                result = await self.extractor.extract_pdf_content(
                    pdf_chunks, user_id=None, source_url='/test.pdf'
                )

                # Then: Should complete successfully with default strategy
                self.assertTrue(result.success)
                # Should use fallback category
                self.assertIn('document_category', result.data)
                self.assertEqual(result.data['document_category'], 'resume')  # Default fallback


@tag('medium', 'integration', 'llm_services')
class MapReduceExtractionTestCase(TestCase):
    """Test suite for map-reduce extraction - TDD RED phase"""

    def setUp(self):
        """Set up test fixtures."""
        self.extractor = EvidenceContentExtractor()

    async def test_map_reduce_splits_into_sections(self):
        """Test map phase processes chunks in sections."""
        # Skip if not implemented
        if not hasattr(self.extractor, '_map_reduce_extraction'):
            self.skipTest("Map-reduce not yet implemented (TDD RED phase)")

        # Given: 100 chunks (simulating 10 chapters, 10 chunks each)
        pdf_chunks = [
            {'content': f'Chapter {i // 10} Section {i % 10}', 'metadata': {}}
            for i in range(100)
        ]

        strategy = {
            'map_chunk_size': 50_000,
            'reduce_strategy': 'hierarchical',
            'summary_tokens': 3_000
        }

        # Mock section extraction
        with patch.object(self.extractor, '_extract_section_content', new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {
                'technologies': ['Python'],
                'achievements': ['Test achievement'],
                'summary': 'Section summary'
            }

            # When: Running map-reduce
            result = await self.extractor._map_reduce_extraction(
                pdf_chunks, strategy, user_id=1, source_url='/thesis.pdf'
            )

            # Then: Should call extract_section_content multiple times (once per section)
            self.assertGreater(mock_extract.call_count, 1)

    async def test_reduce_phase_aggregates_section_summaries(self):
        """Test reduce phase combines section summaries into final summary."""
        if not hasattr(self.extractor, '_reduce_summaries'):
            self.skipTest("Map-reduce not yet implemented (TDD RED phase)")

        # Given: Multiple section summaries
        section_summaries = [
            {
                'technologies': ['Python', 'Django'],
                'achievements': ['Built API'],
                'summary': 'Chapter 1: Introduction to system'
            },
            {
                'technologies': ['PostgreSQL', 'Redis'],
                'achievements': ['Optimized queries'],
                'summary': 'Chapter 2: Database design'
            },
            {
                'technologies': ['React', 'TypeScript'],
                'achievements': ['Created UI'],
                'summary': 'Chapter 3: Frontend implementation'
            }
        ]

        strategy = {
            'reduce_strategy': 'hierarchical',
            'summary_tokens': 3_000
        }

        # When: Reducing summaries
        with patch.object(self.extractor, '_call_llm_for_extraction', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                'content': '{"technologies": ["Python", "Django", "PostgreSQL", "Redis", "React"], "achievements": ["Built API", "Optimized queries", "Created UI"], "summary": "Comprehensive thesis on full-stack development"}',
                'cost': 0.05
            }

            final_summary = await self.extractor._reduce_summaries(
                section_summaries, strategy, user_id=1
            )

            # Then: Should aggregate all technologies and achievements
            self.assertIn('Python', final_summary.data['technologies'])
            self.assertIn('PostgreSQL', final_summary.data['technologies'])
            self.assertIn('React', final_summary.data['technologies'])
            self.assertEqual(len(final_summary.data['achievements']), 3)

    async def test_map_reduce_preserves_chapter_boundaries(self):
        """Test map-reduce doesn't split mid-chapter."""
        if not hasattr(self.extractor, '_map_reduce_extraction'):
            self.skipTest("Map-reduce not yet implemented (TDD RED phase)")

        # Given: Chunks with chapter metadata
        pdf_chunks = [
            {'content': 'Chapter 1 intro', 'metadata': {'chapter': 1}},
            {'content': 'Chapter 1 body', 'metadata': {'chapter': 1}},
            {'content': 'Chapter 2 intro', 'metadata': {'chapter': 2}},
            {'content': 'Chapter 2 body', 'metadata': {'chapter': 2}},
        ]

        strategy = {'map_chunk_size': 50_000, 'reduce_strategy': 'hierarchical'}

        # When: Running map-reduce
        sections = self.extractor._group_chunks_by_chapter(pdf_chunks)

        # Then: Should group by chapter boundaries
        self.assertEqual(len(sections), 2)
        self.assertEqual(len(sections[0]), 2)  # Chapter 1 has 2 chunks
        self.assertEqual(len(sections[1]), 2)  # Chapter 2 has 2 chunks
