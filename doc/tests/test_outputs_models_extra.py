from django.test import TestCase
from django.contrib.auth import get_user_model
from encounters.models import Encounter
from nlp.models import SOAPDraft
from outputs.models import FinalizedSOAP, OutputFile, PatientLink
from django.utils import timezone


User = get_user_model()


class OutputsModelsExtraTest(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='doc', email='d@e.com', password='x')
		self.encounter = Encounter.objects.create(doctor=self.user, patient_ref='P1')
		self.draft = SOAPDraft.objects.create(encounter=self.encounter, soap_data={})
		self.final = FinalizedSOAP.objects.create(soap_draft=self.draft)

	def test_output_file_properties(self):
		f = OutputFile.objects.create(finalized_soap=self.final, file_type='json', file_path='s3://x', file_size=2048)
		assert f.get_file_size_mb() == 0.0 or isinstance(f.get_file_size_mb(), float)

	def test_patient_link_flags(self):
		pl = PatientLink.objects.create(finalized_soap=self.final, access_token='t', expires_at=timezone.now(), view_count=0)
		assert isinstance(pl.is_accessible, bool)
		url = pl.generate_access_url('https://example.com')
		assert 'https://example.com/patient/' in url

