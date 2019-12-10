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

import pytest
import time
import inspect
import os


@pytest.mark.parametrize('package,package_format,expected_instances', [
    ('/packages/eu.5gtango.emulator-example-service.0.1.tgo', 'tango', ['vnf0.vdu01.0', 'vnf1.vdu01.0']),
    ('/packages/eu.sonata.emulator-example-service.0.1.son', 'sonata', ['empty_vnf1', 'empty_vnf2', 'empty_vnf3']),
])
def test_add_instances_from_package(vim, package, package_format, expected_instances):
    expected_interfaces = ['input', 'output', 'mgmt']

    test_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    path = test_dir + package

    actual_instances = vim.add_instances_from_package(package=path, package_format=package_format)

    assert len(actual_instances) == len(expected_instances)

    actual_instances.sort(key=lambda x: x.name)

    for i in range(len(expected_instances)):
        actual_instance = actual_instances[i]
        expected_instance = expected_instances[i]
        assert actual_instance.name == expected_instance

        for interface in expected_interfaces:
            cmd = 'cat /sys/class/net/{}/operstate'.format(interface)
            exec_code, exec_output = actual_instance.execute(cmd)
            assert exec_code == 0
            assert exec_output.strip() == 'up'


@pytest.mark.parametrize('interfaces,expected_interfaces', [
    (None, ['emu0']),
    (3, ['emu0', 'emu1', 'emu2']),
    (['input', 'output', 'management'], ['input', 'output', 'management']),
])
def test_add_instance_from_image(vim, interfaces, expected_interfaces):
    name = 'tangotest_test'
    image = 'ubuntu:trusty'
    instance = vim.add_instance_from_image(name=name, image=image, interfaces=interfaces)
    for interface in expected_interfaces:
        cmd = 'cat /sys/class/net/{}/operstate'.format(interface)
        exec_code, exec_output = instance.execute(cmd)
        assert exec_code == 0
        assert exec_output.strip() == 'up'


def test_add_instance_from_source(vim):
    name = 'tangotest_test'
    test_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    path = test_dir + '/vnfs/empty'
    interface = 'cp0'
    instance = vim.add_instance_from_source(name=name, path=path, interfaces=[interface])
    cmd = 'cat /sys/class/net/{}/operstate'.format(interface)
    exec_code, exec_output = instance.execute(cmd)
    assert exec_code == 0
    assert exec_output.strip() == 'up'


@pytest.mark.parametrize('add_link,expected_exec_code', [
    (False, 1),
    (True, 0),
])
def test_add_link(vim, add_link, expected_exec_code):
    image = 'ubuntu:trusty'
    interface = 'emu0'

    name1 = 'tangotest_test1'
    instance1 = vim.add_instance_from_image(name=name1, image=image, interfaces=[interface])

    name2 = 'tangotest_test2'
    instance2 = vim.add_instance_from_image(name=name2, image=image, interfaces=[interface])
    instance2_ip = instance2.get_internal_ip(interface)

    if add_link:
        vim.add_link(name1, interface, name2, interface)

    cmd = 'ping -c1 -W1 {}'.format(instance2_ip)
    exec_code, exec_output = instance1.execute(cmd)
    assert exec_code == expected_exec_code


@pytest.mark.parametrize('test_vnf', [
    'sniffer', 'generator'
])
@pytest.mark.skip(reason="pass")
def test_add_test_vnf(vim, test_vnf):
    pass


@pytest.mark.skip(reason="pass")
def test_get_traffic(vim):
    image = 'ubuntu:trusty'
    interface = 'emu0'

    name1 = 'tangotest_test1'
    instance1 = vim.add_instance_from_image(name=name1, image=image, interfaces=[interface])

    name2 = 'tangotest_test2'
    instance2 = vim.add_instance_from_image(name=name2, image=image, interfaces=[interface])
    instance2_ip = instance2.get_internal_ip(interface)

    vim.add_link(name1, interface, name2, interface, sniff=True)
    traffic_start = vim.get_traffic(name1, interface, name2, interface)

    time.sleep(2)
    cmd = 'ping -c1 -W1 {}'.format(instance2_ip)
    exec_code, exec_output = instance1.execute(cmd)
    assert exec_code == 0

    time.sleep(5)
    traffic_end = vim.get_traffic(name1, interface, name2, interface)

    assert len(traffic_start) < len(traffic_end)
