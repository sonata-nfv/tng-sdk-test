#  Copyright (c) 2015 SONATA-NFV, 5GTANGO
# ALL RIGHTS RESERVED.
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
# limitations under the License.
#
# Neither the name of the SONATA-NFV, 5GTANGO
# nor the names of its contributors may be used to endorse or promote
# products derived from this software without specific prior written
# permission.
#
# This work has been performed in the framework of the SONATA project,
# funded by the European Commission under Grant number 671517 through
# the Horizon 2020 and 5G-PPP programmes. The authors would like to
# acknowledge the contributions of their colleagues of the SONATA
# partner consortium (www.sonata-nfv.eu).
#
# This work has also been performed in the framework of the 5GTANGO project,
# funded by the European Commission under Grant number 761493 through
# the Horizon 2020 and 5G-PPP programmes. The authors would like to
# acknowledge the contributions of their colleagues of the SONATA
# partner consortium (www.5gtango.eu).

import os

from tangotest.vim.dockerbase import DockerBasedVIM, DockerBasedInstance
from tangotest.vim.base import BaseImmutableInstance
from tangotest.tangotools import parse_package


class Vnv(DockerBasedVIM):
    @property
    def InstanceClass(self):
        return VnvInstance

    def add_instances_from_package(self, package, package_format='tango'):
        if not os.path.isfile(package):
            raise Exception('Package {} not found'.format(package))

        package_data = parse_package(package, package_format)

        instances = []
        for name, vdus in package_data['endpoints'].items():
            # if len(vdus) != 1:
            #     raise Exception('Only one deployment unit per NF is supported.')
            instances.append(self._add_instance(name))

        return instances

    def add_link(self, *args, **kwargs):
        raise Exception('Network configuration is not available')

    def _add_immutable_instance(self, name):
        instance = VnvImmutableInstance(self, name)
        self.instances[name] = instance
        return instance


class VnvInstance(DockerBasedInstance):
    """
    A representation of an instance on the V&V platform.
    Should not be created manually but by the Vnv class.
    """
    def get_ip(self, interface):
        """
        Get an IP address of an interface.

        Args:
            interface (str): The name of the interface

        Returns:
            (str) or (None): The IP address of the interface or None if the interface doesn't exist
                             or if the interface has no IP address
        """

#        env_name = '{}_{}'.format(self.name, interface)
        print("GOT HERE")
        return os.environ.get(self.name, None)


class VnvImmutableInstance(BaseImmutableInstance):
    """
    A representation of an instance without direct access
    Should not be created manually but by the Vnv class.
    """
    def get_ip(self, interface):
        """
        Get an IP address of an interface.

        Args:
            interface (str): The name of the interface

        Returns:
            (str) or (None): The IP address of the interface or None if the interface doesn't exist
                             or if the interface has no IP address
        """

#        env_name = '{}_{}'.format(self.name, interface)
        print("GOT HERE")
        return os.environ.get(self.name, None)
