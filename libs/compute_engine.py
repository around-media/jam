import datetime
import logging
import re
import time
import types

import enum
import googleapiclient
import googleapiclient.discovery
import oauth2client.client


logger = logging.getLogger(__name__)


def wait_for_operation(compute, project, gce_zone, operation):
    logger.debug('Waiting for operation to finish...')
    operation = operation['name'] if isinstance(operation, types.DictionaryType) else operation
    while True:
        result = compute.zoneOperations().get(
            project=project,
            zone=gce_zone,
            operation=operation,
        ).execute()

        if result['status'] == 'DONE':
            logger.debug("Operation done.")
            if 'error' in result:
                raise Exception(result['error'])
            return result

        time.sleep(1)


class InstanceStatus(str, enum.Enum):
    """https://cloud.google.com/compute/docs/instances/checking-instance-status"""

    """Resources are being reserved for the instance. The instance isn't running yet."""
    PROVISIONING = 'PROVISIONING'

    """Resources have been acquired and the instance is being prepared for launch."""
    STAGING = 'STAGING'

    """The instance is booting up or running. You should be able to ssh into the instance soon, though not 
    immediately, after it enters this state."""
    RUNNING = 'RUNNING'

    """The instance is being stopped either due to a failure, or the instance being shut down. This is a temporary 
    status and the instance will move to `TERMINATED`."""
    STOPPING = 'STOPPING'

    """No doc? Deprecated?"""
    STOPPED = 'STOPPED'

    """The instance is being suspended, saving its state to persistent storage, and allowed to be resumed at a 
    later time. This is a temporary status and the instance will move to `SUSPENDED`."""
    SUSPENDING = 'SUSPENDING'

    """The instance is suspended. Suspended instances incur reduced per-minute, virtual machine usage charges while 
    they are suspended. Any resources the virtual machine is using, such as persistent disks and static IP addresses, 
    will continue to be charged until they are deleted."""
    SUSPENDED = 'SUSPENDED'

    """The instance was shut down or encountered a failure, either through the API or from inside the guest. 
    You can choose to restart the instance or delete it."""
    TERMINATED = 'TERMINATED'


class ComputeEngine(object):
    def __init__(self, project, gce_zone):
        credentials = oauth2client.client.GoogleCredentials.get_application_default()
        self.project = project
        self.gce_zone = gce_zone
        self.compute = googleapiclient.discovery.build('compute', 'v1', credentials=credentials, cache_discovery=False)
        self.__instances = {}

    def get_instance(self, name):
        return self.__instances.setdefault(name, ComputeEngineInstance(
            name=name,
            compute=self.compute,
            project=self.project,
            gce_zone=self.gce_zone,
        ))

    def wait_for_operation(self, operation):
        return wait_for_operation(
            compute=self.compute, project=self.project, gce_zone=self.gce_zone, operation=operation['name']
        )

    @property
    def instances(self):
        result = self.compute.instances().list(project=self.project, zone=self.gce_zone).execute()
        result_ts = datetime.datetime.now()
        self.__instances = {
            item['name']: ComputeEngineInstance.build_from_info(
                compute=self.compute,
                info=item,
                info_ts=result_ts,
            ) for item in result['items']
        }
        logger.info("[%s %s] Discovered the following instances: %s.",
                    self.__class__.__name__, self.project,
                    ', '.join(i.name for i in self.__instances))
        return self.__instances


class ComputeEngineInstance(object):
    DEFAULT_STALE_AFTER_MS = 1000

    def __init__(self, name, compute, project, gce_zone, stale_after=None):
        self.name = name
        self.compute = compute
        self.project = project
        self.gce_zone = gce_zone
        self.info = None
        self.stale_after = datetime.timedelta(
            milliseconds=self.DEFAULT_STALE_AFTER_MS if stale_after is None else stale_after,
        )
        self.info_ts = datetime.datetime.min

    @classmethod
    def build_from_info(cls, compute, info, info_ts=None, stale_after=None):
        regex = (r'https://www.googleapis.com/compute/beta'
                 r'/projects/(?P<project>.*)'
                 r'/zones/(?P<gce_zone>.*)'
                 r'/instances/(?P<name>.*)')
        match = re.match(regex, info['selfLink']).groupdict()
        instance = cls(
            name=info['name'],
            compute=compute,
            project=match['project'],
            gce_zone=match['gce_zone'],
            stale_after=stale_after,
        )
        instance.info = info
        instance.info_ts = datetime.datetime.now() if info_ts is None else info_ts
        return instance

    def refresh(self):
        self.info = self.compute.instances().get(project=self.project, zone=self.gce_zone, instance=self.name).execute()
        self.info_ts = datetime.datetime.now()

    @property
    def status(self):
        if datetime.datetime.now() - self.info_ts > self.stale_after:
            self.refresh()
        return self.info['status']

    def wait_for_operation(self, operation):
        return wait_for_operation(
            compute=self.compute, project=self.project, gce_zone=self.gce_zone, operation=operation['name']
        )

    def wait_for_status(self, statuses):
        if not isinstance(statuses, (types.ListType, types.TupleType)):
            statuses = [statuses]
        previous_status = None
        while True:
            if not self.status == previous_status:
                logger.info('[%s %s] Instance is {}'.format(self.status), self.__class__.__name__, self.name)
            if self.status in statuses:
                break
            previous_status = self.status
            time.sleep(3)

    def start(self):
        logger.info("[%s %s] Starting Instance.", self.__class__.__name__, self.name)
        operation = self.compute.instances().start(
            project=self.project, zone=self.gce_zone, instance=self.name
        ).execute()
        self.wait_for_operation(operation=operation)
        logger.info("[%s %s] Instance status: %s.", self.__class__.__name__, self.name, self.status)

    def stop(self):
        logger.info("[%s %s] Stopping Instance.", self.__class__.__name__, self.name)
        operation = self.compute.instances().stop(
            project=self.project, zone=self.gce_zone, instance=self.name
        ).execute()
        self.wait_for_operation(operation=operation)
        logger.info("[%s %s] Instance status: %s.", self.__class__.__name__, self.name, self.status)
