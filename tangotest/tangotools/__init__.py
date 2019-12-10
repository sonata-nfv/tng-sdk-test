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

# flake8: noqa

import time
import os
import shutil
import tempfile
import docker
import yaml
import zipfile


def create_vnv_test(tests_path, ns_package_path, test_package_path=None, probe_name=None):
    """
    Prepare tests for uploading to the V&V platform.

    Args:
        tests_path (str): The path to the directory with test files.
        ns_package_path (str): The path to the network service package.
        test_package_path(str): The path for the generated test package files. Default: current directory
        probe_name (str): The name for the generated probe. Default: 'tng-sdk-test-<datetime>'
    """

    test_package_path = test_package_path or '.'
    if not os.path.isdir(test_package_path):
        raise Exception('{} is not a directory'.format(test_package_path))

    probe_name = build_probe(tests_path, probe_name)

    ns_package_data = parse_package(ns_package_path)

    test_descriptor_data = generate_test_descriptor(probe_name, ns_package_data)
    package_descriptor_data = generate_package_descriptor(ns_package_data)

    create_test_package(ns_package_data['ns_name'], test_package_path, test_descriptor_data, package_descriptor_data)


def create_test_package(name, test_package_path, test_descriptor_data, package_descriptor_data):
    folder_name = 'functest-{}'.format(name)
    folder_path = os.path.join(test_package_path, folder_name)
    if os.path.isdir(folder_path):
        shutil.rmtree(folder_path)

    os.mkdir(folder_path)

    package_descriptor_path = os.path.join(folder_path, 'project.yml')
    with open(package_descriptor_path, 'w') as f:
        yaml.dump(package_descriptor_data, f)

    os.mkdir(os.path.join(folder_path, 'Definitions'))
    test_descriptor_path = os.path.join(folder_path, 'Definitions', 'test-descriptor.yml')
    with open(test_descriptor_path, 'w') as f:
        yaml.dump(test_descriptor_data, f)


def build_probe(tests_path, probe_name=None):
    """
    Build a probe with tests

    Args:
        tests_path (str): The path to the directory with test files.
        probe_name (str): The name for the generated probe. Default: 'tng-sdk-test-<datetime>'
    """

    dockerfile_content = """
    FROM ubuntu:xenial
    RUN apt-get update -q && apt-get install -qy \
        apt-transport-https \
        ca-certificates \
        python-setuptools \
        python-dev \
        python-pip \
        git \
        libltdl-dev
    RUN pip install git+https://github.com/tsoenen/tng-sdk-test
    COPY . /
    RUN pip install pytest==4.6.4
    RUN pip install -r requirements.txt
    ENV TANGOTEST_PLATFORM VNV
    CMD python -m pytest -vvv test_ns1.py
    """

    dockerfile = tempfile.NamedTemporaryFile(bufsize=0)
    dockerfile.write(dockerfile_content)

    docker_client = docker.from_env()
    docker_image, _ = docker_client.images.build(path=tests_path, dockerfile=dockerfile.name)

    tag = probe_name or 'tng-sdk-test-{}'.format(time.strftime("%Y-%m-%d-%H-%M-%S"))
    docker_image.tag(tag)

    return tag


def parse_package(package_path, package_format='tango'):
    """
    Extract network service information from its package.

    Output example:
        {
            'ns_name': 'my_ns',
            'testing_tags': ['tag1', 'tag2'],
            'endpoints': {
                'nf1': {
                    'vdu1': ['input', 'output']
                }
            }
        }

    Args:
        package_path (str): The path to the package
        package_format (str): Package format. Default: 'tango'
    """

    if package_format == 'tango':
        return parse_tango_package(package_path)
    else:
        raise Exception('Specified unsupported package_format {}. Supported formats: tango.'.format(package_format))


def parse_tango_package(package_path):
    def extract_external_cps(descriptor, upper_level_cps):
        virtual_links = [vl['connection_points_reference'] for vl in descriptor['virtual_links']]
        external_virtual_links = [vl for vl in virtual_links if set(vl) & set(upper_level_cps)]
        external_cps = list(set(sum(external_virtual_links, [])).difference(upper_level_cps))
        return external_cps

    result = {}
    nsd = None
    nfds = {}

    with zipfile.ZipFile(package_path, "r") as z:
        with z.open('TOSCA-Metadata/NAPD.yaml') as pd_file:
            pd = yaml.safe_load(pd_file)

        for record in pd['package_content']:
            if record['content-type'] == 'application/vnd.5gtango.nsd':
                if nsd:
                    raise Exception('Only one NSD can be in the package')
                with z.open(record['source']) as nsd_file:
                    nsd = yaml.safe_load(nsd_file)
                result['tags'] = record.get('tags', [])
                result['testing_tags'] = record.get('testing_tags', [])
            if record['content-type'] == 'application/vnd.5gtango.vnfd':
                with z.open(record['source']) as nfd_file:
                    nfd = yaml.safe_load(nfd_file)
                    nfds[nfd['name']] = nfd

    if not nsd:
        raise Exception('NSD is not found')

    result['ns_name'] = nsd['name']
    result['ns_version'] = nsd['version']
    result['ns_vendor'] = nsd['vendor']
    result['endpoints'] = {}

    external_ns_cps = [cp['id'] for cp in nsd['connection_points'] if cp['type'] == 'external']
    external_nfs_cps = extract_external_cps(nsd, external_ns_cps)

    for nf in nsd['network_functions']:
        nf_name = nf['vnf_name']
        nf_id = nf['vnf_id']
        nfd = nfds[nf_name]
        external_nf_cps = [cp.split(':')[1] for cp in external_nfs_cps if cp.split(':')[0] == nf_id]
        external_dus_cps = extract_external_cps(nfd, external_nf_cps)

        result['endpoints'][nf_name] = {}
        deployment_units = nfd.get('virtual_deployment_units', []) or nfd.get('cloudnative_deployment_units')
        for du in deployment_units:
            du_name = du['id']
            external_du_cps = [cp.split(':')[1] for cp in external_dus_cps if cp.split(':')[0] == du_name]
            result['endpoints'][nf_name][du_name] = external_du_cps

    return result


def generate_test_descriptor(probe_name, package_data):
    return {
        'descriptor_schema': 'https://raw.githubusercontent.com/sonata-nfv/tng-schema/master/test-descriptor/testdescriptor-schema.yml',
        'vendor': 'eu.5gtango',
        'name': 'tng-sdk-test-{}'.format(package_data['ns_name']),
        'version': '0.1',
        'author': 'tng-sdk-test',
        'description': 'Functional test for {}'.format(package_data['ns_name']),
        'testing_tags': package_data.get('testing_tags', []),
        'test_category': ['functional'],
        'service_platforms': ["SONATA"],
        'phases': [{
            'id': 'setup',
            'steps': [{
                'name': 'deployment',
                'description': 'Deploying a NS',
                'action': 'deploy',
            }, {
                'name': 'configuration',
                'description': 'Configuring test',
                'action': 'configure',
                'probes': [{
                    'id': 'tester',
                    'name': 'tester',
                    'image': 'tsoenen/{}'.format(probe_name),
                    'description': 'A container with tng-sdk-test and the test code',
                    'parameters': [{
                        'key': '{}'.format(vnf),
                        'value': '$({}/endpoints/id:floating_ip/address)'.format(vnf)
                    } for vnf in package_data['endpoints']],
                }],
            }],
        }, {
            'id': 'exercise',
            'steps': [{
                'name': 'run_tests',
                'description': 'Run a probe with tng-sdk-test and the test code',
                'run': 'tester',
                'index': 0,
                'start_delay': 0,
                'instances': 1,
                'output': [{
                    'results': 'logs.txt',
                    'verdict': 'status.txt',
                }],
            }],
        }, {
            'id': 'verification',
            'steps': [{
                'name': 'tester',
                'description': 'Check the exit-code of the test',
                'step': 'configure_service',
                'condition': [{
                    'type': 'json',
                    'name': 'test-exit-code',
                    'file': 'status.txt',
                    'find': 'exit-code',
                    'value': '0',
                    'verdict': 'pass',
                    'condition': '=',
                }]
            }]
        }]
    }


def generate_package_descriptor(package_data):
    return {
        'descriptor_extension': 'yml',
        'version': '0.1',
        'package': {
            'vendor': 'eu.5gtango',
            'maintainer': 'tng-sdk-test',
            'name': 'functest-{}'.format(package_data['ns_name']),
            'version': package_data['ns_version'],
            'description': 'Functional test for {}'.format(package_data['ns_name']),
        },
        'files': [{
            'path': 'Definitions/test-descriptor.yml',
            'type': 'application/vnd.5gtango.tstd',
            'testing_tags': package_data['testing_tags'],
        }]
    }
