from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from analytics.services import AnalyticsService
from analytics.models import Metric, PerformanceMetric, UserActivity


User = get_user_model()


class AnalyticsServiceExtraTest(TestCase):
	def setUp(self):
		self.service = AnalyticsService()
		self.user = User.objects.create_user(username='alice', email='a@a.com', password='x')

	def test_calculate_business_metrics_empty(self):
		start = datetime.now() - timedelta(days=1)
		end = datetime.now()
		res = self.service.calculate_business_metrics(start, end)
		assert 'total_encounters' in res

	def test_get_user_and_perf_analytics(self):
		# seed minimal data
		UserActivity.objects.create(user=self.user, action='login', resource='', resource_id=None, metadata={})
		PerformanceMetric.objects.create(endpoint='/api/x', method='GET', response_time_ms=123, status_code=200)
		Metric.objects.create(name='m', metric_type='gauge', value=1.2, tags={})
		ua = self.service.get_user_analytics(self.user.id, days=7)
		pa = self.service.get_performance_analytics(days=7)
		assert 'total_activities' in ua
		assert 'total_requests' in pa

