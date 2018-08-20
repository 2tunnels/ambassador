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

from typing import Any, ClassVar, Dict, List, Optional, Union, TYPE_CHECKING
from typing import cast as typecast

import re

from ..config import Config

from .irresource import IRResource
from .irtls import IREnvoyTLS

if TYPE_CHECKING:
    from .ir import IR

#############################################################################
## ircluster.py -- the ircluster configuration object for Ambassador
##
## IRCluster represents an Envoy cluster: a collection of endpoints that
## provide a single service. IRClusters get used for quite a few different
## things in Ambassador -- they are basically the generic "upstream service"
## entity.


class IRCluster (IRResource):
    TransparentRouteKeys: ClassVar[Dict[str, bool]] = {
        "auto_host_rewrite": True,
        "case_sensitive": True,
        "envoy_override": True,
        "host_rewrite": True,
        "path_redirect": True,
        "priority": True,
        "timeout_ms": True,
        "use_websocket": True
    }

    def __init__(self, ir: 'IR', aconf: Config,
                 location: str,  # REQUIRED

                 service: str,   # REQUIRED

                 ctx_name: Optional[Union[str, bool]]=None,
                 host_rewrite: Optional[str]=None,

                 dns_type: str="strict_dns",
                 lb_type: str="round_robin",
                 grpc: Optional[bool] = False,

                 cb_name: Optional[str]=None,
                 od_name: Optional[str]=None,

                 rkey: str="-override-",
                 kind: str="IRCluster",
                 apiVersion: str="ambassador/v0",   # Not a typo! See below.
                 **kwargs) -> None:
        # Step one: look at the service and such and figure out a cluster name
        # and TLS origination info.

        # Here's how it goes:
        # - If the service starts with https://, it is forced to originate TLS.
        # - Else, if it starts with http://, it is forced to _not_ originate TLS.
        # - Else, if we have a context (either a string that names a valid context,
        #   or the boolean value True), it will originate TLS.
        #
        # After figuring that out, if we have a context which is a string value,
        # we try to use that context name to look up certs to use. If we can't
        # find any, we won't send any originating cert.
        #
        # Finally, if no port is present in the service already, we force port 443
        # if we're originating TLS, 80 if not.

        originate_tls: bool = False
        name_fields: List[str] = [ "cluster" ]
        ctx: Optional[IREnvoyTLS] = None
        errors: List[str] = []
        tls_array: Optional[List[Dict[str, Any]]] = None

        # If we have a ctx_name, does it match a real context?
        if ctx_name:
            if ctx_name is True:
                ctx = IREnvoyTLS(ir=ir, aconf=aconf,
                                 rkey="ir.nulltlscontext",
                                 name="ir.nulltlscontext",
                                 _ambassador_enabled=True)
            else:
                ctx = ir.get_tls_context(typecast(str, ctx_name))

            if not ctx:
                errors.append("Originate-TLS context %s is not defined" % ctx_name)

        if service.lower().startswith("https://"):
            service = service[len("https://"):]

            originate_tls = True
            name_fields.append('otls')

        elif service.lower().startswith("http://"):
            if ctx:
                errors.append("Originate-TLS context %s being used even though service %s lists HTTP" % (ctx_name, service))
                originate_tls = True
                name_fields.append('otls')
            else:
                service = service[len("http://"):]
                originate_tls = False

        elif ctx:
            # No scheme, but we have a context.
            originate_tls = True
            name_fields.append('otls')
            name_fields.append(typecast(str, ctx_name))

        # XXX Should this be checking originate_tls? Why does it do that? 
        if originate_tls and host_rewrite:
            name_fields.append("hr-%s" % host_rewrite)

        name_fields.append(service)
        name = "_".join(name_fields)
        name = re.sub(r'[^0-9A-Za-z_]', '_', name)

        port = 443 if originate_tls else 80

        svc_and_port = service

        if ':' not in svc_and_port:
            svc_and_port = '%s:%d' % (service, port)

        if rkey == '-override-':
            rkey = name

        url = 'tcp://%s' % svc_and_port

        # OK. Build our default args.

        new_args: Dict[str, Any] = {
            "type": dns_type,
            "lb_type": lb_type,
            "urls": [ url ],
            "service": service
        }

        if originate_tls:
            if ctx:
                new_args['tls_context'] = typecast(IREnvoyTLS, ctx)

                new_args['tls_array'] = [
                    { 'key': key, 'value': ctx[key] }
                    for key in sorted(typecast(IREnvoyTLS, ctx).keys()) if not key.startswith('_')
                ]

                if host_rewrite:
                    new_args['tls_array'].append({'key': 'sni', 'value': host_rewrite })

        if grpc:
            new_args['features'] = 'http2'

        # if cb_name and (cb_name in self.breakers):
        #     cluster['circuit_breakers'] = self.breakers[cb_name]
        #     self.breakers[cb_name].referenced_by(_source)

        # if od_name and (od_name in self.outliers):
        #     cluster['outlier_detection'] = self.outliers[od_name]
        #     self.outliers[od_name].referenced_by(_source)

        super().__init__(
            ir=ir, aconf=aconf, rkey=rkey, location=location,
            kind=kind, name=name, apiVersion=apiVersion,
            **new_args
        )

        if ctx:
            ctx.referenced_by(self)

    def add_url(self, url: str) -> List[str]:
        self.urls.append(url)

        return self.urls
