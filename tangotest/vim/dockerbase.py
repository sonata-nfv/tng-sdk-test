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
from abc import ABCMeta, abstractproperty
import docker
import requests


from tangotest.vim.base import BaseVIM, BaseInstance


class DockerBasedVIM(BaseVIM):
    __metaclass__ = ABCMeta

    def __init__(self, *args, **kwargs):
        super(DockerBasedVIM, self).__init__(*args, **kwargs)

    @abstractproperty
    def InstanceClass(self):
        return DockerBasedInstance

    def start(self):
        super(DockerBasedVIM, self).start()
        self.docker_client = docker.from_env(timeout=999999)

    def stop(self):
        super(DockerBasedVIM, self).stop()
        for name, instance in self.instances.items():
            instance.stop()

    def _image_exists(self, image):
        try:
            self.docker_client.images.get(image)
        except docker.errors.ImageNotFound:
            if ':' in image:
                image_name, image_tag = image.split(':')
            else:
                image_name = image
                image_tag = 'latest'
            url = 'https://index.docker.io/v1/repositories/{}/tags/{}'.format(image_name, image_tag)
            if not requests.get(url).ok:
                return False
        except docker.errors.APIError as e:
            raise e
        return True

    def add_instance_from_image(self, name, image, interfaces=None, docker_command='/bin/bash', **docker_run_args):
        """
        Run a Docker image on the Emulator.

        Args:
            name (str): The name of an instance
            image (str): The name of an image
            interfaces (int) or (list) or (dict): Network configuration
            docker_command (str): The command to execute when starting the instance

        Returns:
            (EmulatorInstance): The added instance
        """

        if not self._image_exists(image):
            raise Exception('Docker image {} not found'.format(image))

        self.docker_client.containers.run(name=name, image=image, command=docker_command,
                                          tty=True, detach=True, **docker_run_args)
        return self._add_instance(name)

    def add_instance_from_source(self, name, path, interfaces=None, image_name=None,
                                 docker_command=None, **docker_build_args):
        """
        Build and run a Docker image on the Emulator.

        Args:
            name (str): The name of an instance
            path (str): The path to the directory containing Dockerfile
            interfaces (int) or (list) or (dict): Network configuration
            image_name (str): The name of an image. Default: tangotest<name>
            docker_command (str): The command to execute when starting the instance
            **docker_build_args: Extra arguments to be used by the Docker engine to build the image

        Returns:
            (EmulatorInstance): The added instance
        """

        if path[-1] != '/':
            path += '/'

        if not os.path.isfile('{}Dockerfile'.format(path)):
            raise Exception('Dockerfile in {} not found'.format(path))

        tag = image_name or 'tangotest{}'.format(name)
        docker_image, _ = self.docker_client.images.build(path=path, **docker_build_args)
        docker_image.tag(tag)

        return self.add_instance_from_image(name, tag, interfaces)


class DockerBasedInstance(BaseInstance):
    """
    A representation of a docker-based instance.
    Should not be created manually but by the DockerBaseVIM class.
    """
    __metaclass__ = ABCMeta

    def __init__(self, vim, name):
        """
        Initialize the instance.

        Args:
            name (str): The name of an instance
            path (str): The path to the directory containing Dockerfile
        """
        self.vim = vim
        self.name = name
        self.output = None
        # Don't stop here in vnv case, just ignore
        try:
            self.docker_client = self.vim.docker_client
            self.container = self.docker_client.containers.get(self.container_name)
        except:
            self.docker_client = None
            self.container = None

    @property
    def container_name(self):
        return self.name

    def execute(self, cmd, stream=False, **kwargs):
        return self.container.exec_run(cmd=['sh', '-c', cmd], stream=stream, **kwargs)

    def stop(self):
        try:
            self.container.remove(force=True)
        except Exception:
            pass
