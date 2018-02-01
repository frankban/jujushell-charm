from unittest import (
    TestCase,
    mock,
)
from urllib.error import HTTPError

import collect_metrics

TEST_DATA = """
# HELP go_threads Number of OS threads created.
# TYPE go_threads gauge
go_threads 7
# HELP jujushell_containers_duration time spent doing container operations
# TYPE jujushell_containers_duration histogram
jujushell_containers_duration_bucket{operation="create-container",le="0.25"} 0
jujushell_containers_duration_bucket{operation="create-container",le="0.5"} 0
jujushell_containers_duration_bucket{operation="create-container",le="1"} 0
jujushell_containers_duration_bucket{operation="create-container",le="1.5"} 0
jujushell_containers_duration_bucket{operation="create-container",le="2"} 0
jujushell_containers_duration_bucket{operation="create-container",le="3"} 0
jujushell_containers_duration_bucket{operation="create-container",le="5"} 1
jujushell_containers_duration_bucket{operation="create-container",le="10"} 1
jujushell_containers_duration_bucket{operation="create-container",le="+Inf"} 2
jujushell_containers_duration_sum{operation="create-container"} 30.739989075
jujushell_containers_duration_count{operation="create-container"} 2
jujushell_containers_duration_bucket{operation="get-all-containers",le="0.25"} 16
jujushell_containers_duration_bucket{operation="get-all-containers",le="0.5"} 16
jujushell_containers_duration_bucket{operation="get-all-containers",le="1"} 16
jujushell_containers_duration_bucket{operation="get-all-containers",le="1.5"} 16
jujushell_containers_duration_bucket{operation="get-all-containers",le="2"} 16
jujushell_containers_duration_bucket{operation="get-all-containers",le="3"} 16
jujushell_containers_duration_bucket{operation="get-all-containers",le="5"} 16
jujushell_containers_duration_bucket{operation="get-all-containers",le="10"} 16
jujushell_containers_duration_bucket{operation="get-all-containers",le="+Inf"} 16
jujushell_containers_duration_sum{operation="get-all-containers"} 0.127221213
jujushell_containers_duration_count{operation="get-all-containers"} 16
# HELP jujushell_containers_in_flight the number of containers currently present in the machine
# TYPE jujushell_containers_in_flight gauge
jujushell_containers_in_flight 2
# HELP jujushell_errors_count the number of encountered errors
# TYPE jujushell_errors_count counter
jujushell_errors_count{message="cannot log into juju: cannot authenticate user: interaction required but not possible"} 1
# HELP jujushell_requests_count the total count of requests
# TYPE jujushell_requests_count counter
jujushell_requests_count{code="200"} 17
# HELP jujushell_requests_duration time spent in requests
# TYPE jujushell_requests_duration summary
jujushell_requests_duration{code="200",quantile="0.5"} 1.162983433
jujushell_requests_duration{code="200",quantile="0.9"} 1.162983433
jujushell_requests_duration{code="200",quantile="0.99"} 1.162983433
jujushell_requests_duration_sum{code="200"} 28474.801069908997
jujushell_requests_duration_count{code="200"} 17
# HELP jujushell_requests_in_flight the number of requests currently in flight
# TYPE jujushell_requests_in_flight gauge
jujushell_requests_in_flight 0
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total 292.48""".split('\n')  # noqa: E501


class TestGetMetrics(TestCase):

    @mock.patch('urllib.request.urlopen')
    def test_get_metric(self, mock_urlopen):
        self.assertTrue(collect_metrics.METRIC_NAME_MAP is not None)
        mock_urlopen.return_value = TEST_DATA
        self.assertEqual(collect_metrics.get_metric('dalek'), '')
        self.assertEqual(collect_metrics.get_metric('requests_count'), '17')
        error = HTTPError('', 400, 'Bad Request', None, None)
        with mock.patch('urllib.request.urlopen', side_effect=error) as \
                mock_urlopen:
            self.assertEqual(collect_metrics.get_metric('requests_count'), '')
