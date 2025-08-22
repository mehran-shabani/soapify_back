from django.test import TestCase
from worker.tasks import test_task, backup_database


class WorkerTasksTest(TestCase):
	def test_test_task_callable(self):
		# Call task function directly to cover body
		res = test_task()
		assert isinstance(res, dict)
		assert res.get('status') == 'success'

	def test_backup_database_callable(self):
		res = backup_database()
		assert isinstance(res, dict)
		assert res.get('status') == 'completed'

