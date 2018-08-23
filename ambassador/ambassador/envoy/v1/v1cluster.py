# Copyright 2018 Datawire. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License

from typing import List, TYPE_CHECKING

from ...ir.ircluster import IRCluster

if TYPE_CHECKING:
    from . import V1Config


class V1Cluster(dict):
    def __init__(self, config: 'V1Config', cluster: IRCluster) -> None:
        super().__init__()

        self["name"] = cluster.name
        self["connect_timeout_ms"] = cluster.get("timeout_ms", 3000)
        self["type"] = cluster.get("dns_type", "strict_dns")
        self["lb_type"] = cluster.get("lb_type", "round_robin")

        self["hosts"] = [ { "url": url } for url in cluster.urls ]

        if cluster.get('features', []):
            self["features"] = cluster.features

        if cluster.get('breakers', {}):
            pass
            # brk = cluster.breakers
            #
            # self["circuit_breakers"] = {
            #     "default": {
            #         "max_connections": {{ brk.max_connections or 1024 }},
            #         "max_pending_requests": {{ brk.max_pending or 1024 }},
            #         "max_requests": {{ brk.max_requests or 1024 }},
            #         "max_retries": {{ brk.max_retries or 3 }}
            #     }
            # }

        if cluster.get('outlier', {}):
            pass
            # outlier = cluster.outlier
            #
            # self["outlier_detection"] = {
            #     "consecutive_5xx": outlier.consecutive_5xx or 5
            #     "max_ejection_percent": outlier.max_ejection or 100
            #     "interval_ms": outlier.interval_ms or 3000
            # }

        # "ssl_context": {
        #   {% for entry in cluster.tls_array %}
        #   "{{ entry.key }}": "{{ entry.value }}"{{ "," if not loop.last }}
        #   {% endfor %}
        # }{%- endif -%}

    @classmethod
    def generate(self, config: 'V1Config') -> List['V1Cluster']:
        clusters: List['V1Cluster'] = []

        for cluster in sorted(config.ir.clusters.values(), key=lambda x: x.name):
            clusters.append(V1Cluster(config, cluster))

        return clusters
