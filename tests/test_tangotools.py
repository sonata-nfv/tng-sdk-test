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
import inspect
import os
from contextlib import contextmanager
import docker

from tangotest.vim.emulator import Emulator
from tangotest.tangotools.vnv_checker import VnvError
from tangotest.tangotools import parse_package, build_probe


packages = [(
    '/packages/eu.5gtango.emulator-example-service.0.1.tgo',
    'tango',
    {
        'endpoints': {
            'default-vnf0': {
                'vdu01': ['input']
            },
            'default-vnf1': {
                'vdu01': ['output']
            }
        },
        'ns_name': 'emulator_example',
        'ns_vendor': 'eu.5gtango',
        'ns_version': '0.9',
        'tags': ['eu.5gtango'],
        'testing_tags': [],
    }
), (
    '/packages/eu.sonata.emulator-example-service.0.1.son',
    'sonata',
    None
), (
    '/packages/eu.5gtango.test-ns-nsid1v.0.1.tgo',
    'tango',
    {
        'endpoints': {
            'testvnf': {
                'vdu01': ['eth1', 'eth2']
            }
        },
        'ns_name': 'test-nsid1v',
        'ns_vendor': 'eu.5gtango',
        'ns_version': '0.1',
        'tags': ['eu.5gtango'],
        'testing_tags': ['eu.5gtango.testingtag.example']
    }
)]


test_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))


@contextmanager
def emulator_with_vnv_checker_and_package():
    vim = Emulator(vnv_checker=True)
    vim.start()
    path = test_dir + packages[0][0]
    package_format = packages[0][1]
    vim.add_instances_from_package(package=path, package_format=package_format)
    yield vim
    vim.stop()


@contextmanager
def does_not_raise():
    yield


@pytest.mark.parametrize('function_calls,expectation', [
    (0, pytest.raises(VnvError)),
    (1, does_not_raise()),
    (2, pytest.raises(VnvError)),
])
def test_vnv_checker_add_instances_from_package_called_once(function_calls, expectation):
    with expectation:
        with Emulator(vnv_checker=True) as vim:
            for i in range(function_calls):
                path = test_dir + packages[i][0]
                package_format = packages[i][1]
                vim.add_instances_from_package(package=path, package_format=package_format)


@pytest.mark.parametrize('interfaces,expectation', [
    (None, does_not_raise()),
    (2, pytest.raises(VnvError)),
])
def test_vnv_checker_add_instance_from_image_without_interfaces(interfaces, expectation):
    name = 'tangotest_test'
    image = 'ubuntu:trusty'
    with expectation:
        with emulator_with_vnv_checker_and_package() as vim:
            vim.add_instance_from_image(name=name, image=image, interfaces=interfaces)


@pytest.mark.parametrize('interfaces,expectation', [
    (None, does_not_raise()),
    (2, pytest.raises(VnvError)),
])
def test_vnv_checker_add_instance_from_source_without_interfaces(interfaces, expectation):
    name = 'tangotest_test'
    path = test_dir + '/vnfs/empty'
    with expectation:
        with emulator_with_vnv_checker_and_package() as vim:
            vim.add_instance_from_source(name=name, path=path, interfaces=interfaces)


@pytest.mark.parametrize('called,expectation', [
    (False, does_not_raise()),
    (True, pytest.raises(VnvError)),
])
def test_vnv_checker_add_link_not_called(called, expectation):
    with expectation:
        with emulator_with_vnv_checker_and_package() as vim:
            name1 = 'tangotest_test1'
            name2 = 'tangotest_test2'
            image = 'ubuntu:trusty'
            vim.add_instance_from_image(name=name1, image=image)
            vim.add_instance_from_image(name=name2, image=image)
            if called:
                vim.add_link(name1, 'cp0', name2, 'cp0')


@pytest.mark.parametrize('package_path,package_format,expected_result', packages)
def test_package_parser(package_path, package_format, expected_result):
    if expected_result is None:
        pytest.skip('unsupported package')
    path = test_dir + package_path
    result = parse_package(path, package_format)
    assert result == expected_result

@pytest.mark.skip(reason="not working")
def test_probe_builder():
    test_code_path = '/simple-test/'
    path = test_dir + test_code_path
    image_name = build_probe(path)
    command = 'python2 main.py'

    volumes = {
        '/var/run/docker.sock': {
            'bind': '/var/run/docker.sock',
            'mode': 'rw',
        },
        '/usr/bin/docker': {
            'bind': '/usr/bin/docker',
            'mode': 'ro',
        }
    }

    docker_client = docker.from_env()
    try:
        test_results = docker_client.containers.run(image=image_name, volumes=volumes, tty=True, command=command, remove=True)
    except docker.errors.ContainerError as e:
        print(e.stderr)
        assert False

    expected_results = b'hello world\r\n\r\n'
    assert test_results == expected_results

    docker_client.images.remove(image_name, force=True)
