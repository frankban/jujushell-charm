#!/usr/bin/env python3

import sys
from urllib import request
from urllib.error import HTTPError


METRIC_NAME_MAP = {
    'requests_in_flight': 'jujushell_requests_in_flight',
    'requests_count': 'jujushell_requests_count',
    'requests_duration': 'jujushell_requests_duration_sum',
    'errors_count': 'jujushell_errors_count',
    'containers_in_flight': 'jujushell_containers_in_flight',
    'containers_duration_create_container':
        'jujushell_containers_duration_sum{operation="create-container"}',
    'containers_duration_get_all_containers':
        'jujushell_containers_duration_sum{operation="get-all-containers"}',
}


def get_metric(metric_name):
    """Fetch a given metric from the prometheus metrics and return to
    omnibus.
    """
    metric = METRIC_NAME_MAP.get(metric_name)
    if metric is None:
        return ''
    try:
        response = request.urlopen('http://127.0.0.1/metrics')
    except HTTPError:
        return ''
    for line in response:
        if line.startswith(metric):
            return line.split(' ')[-1]
    return ''


if __name__ in '__main__':
    print(get_metric(sys.argv[1]))
