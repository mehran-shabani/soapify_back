from django.test import TestCase
from django.contrib.auth import get_user_model

from checklist.services import ChecklistEvaluationService
from checklist.models import ChecklistCatalog
from encounters.models import Encounter, AudioChunk, TranscriptSegment


User = get_user_model()


class ChecklistServiceMoreTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='svcuser', email='svc@example.com', password='x'
        )
        self.encounter = Encounter.objects.create(doctor=self.user, patient_ref='PXX')
        self.service = ChecklistEvaluationService()

    def test_evaluate_encounter_not_found(self):
        with self.assertRaises(ValueError):
            self.service.evaluate_encounter(encounter_id=999999)

    def test_evaluate_encounter_no_transcript(self):
        # Create transcript container but no text segments
        chunk = AudioChunk.objects.create(
            encounter=self.encounter, chunk_number=1, file_path='x', file_size=1, format='wav'
        )
        # No TranscriptSegment objects -> service returns message
        res = self.service.evaluate_encounter(self.encounter.id)
        self.assertIsInstance(res, dict)
        self.assertIn('message', res)
        self.assertIn('No transcript', res['message'])

    def test_keyword_eval_no_keywords(self):
        item = ChecklistCatalog.objects.create(
            title='Allergies',
            description='Ask about allergies',
            category='general',
            keywords=[],
            question_template='Do you have any allergies?',
            created_by=self.user,
        )
        out = self.service._keyword_based_evaluation(item, 'any text')
        self.assertEqual(out['status'], 'unclear')
        self.assertEqual(out['confidence_score'], 0.0)
        self.assertTrue(out['generated_question'])

    def test_keyword_eval_missing_partial_covered(self):
        item = ChecklistCatalog.objects.create(
            title='Symptoms',
            description='Core symptoms',
            category='subjective',
            keywords=['pain', 'fever', 'cough', 'nausea', 'headache'],
            question_template='What symptoms do you have?',
            created_by=self.user,
        )

        # missing
        out_missing = self.service._keyword_based_evaluation(item, 'no relevant words here')
        self.assertEqual(out_missing['status'], 'missing')
        self.assertEqual(out_missing['confidence_score'], 0.0)

        # partial (>=0.5 and <0.8). Use exactly 2/5 = 0.4 would be 'unclear', so pick 3/5.
        txt_partial = 'Patient reports pain and cough and headache at night.'
        out_partial = self.service._keyword_based_evaluation(item, txt_partial)
        self.assertEqual(out_partial['status'], 'partial')
        self.assertGreater(out_partial['confidence_score'], 0.0)
        self.assertTrue(out_partial['generated_question'])

        # covered (>= 0.8)
        txt_covered = 'Fever and headache with severe pain; denies cough or nausea.'
        out_covered = self.service._keyword_based_evaluation(item, txt_covered)
        self.assertEqual(out_covered['status'], 'covered')
        self.assertGreaterEqual(out_covered['confidence_score'], 0.8)

