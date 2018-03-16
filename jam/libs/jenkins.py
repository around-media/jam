import logging
import os
import re
import time

import enum
import requests

logger = logging.getLogger(__name__)


class StatusError(AttributeError):
    pass


class AgentStatus(enum.Enum):
    ONLINE_BUSY = 'ONLINE BUSY'
    ONLINE_IDLE = 'ONLINE IDLE'
    SCHEDULED_FOR_DISCONNECTION = 'BUSY BUT WILL DISCONNECT AFTERWARDS'
    DISCONNECTED = 'DISCONNECTED'
    SCHEDULED_FOR_SLEEP = 'BUSY BUT WILL SLEEP AFTERWARDS'
    SLEEPING = 'SLEEPING'
    ERROR = 'ERROR'


def perform_crumb_call(session, crumb_url, auth):
    crumb_response = session.get(url=crumb_url, auth=auth)
    if crumb_response.status_code != 200:
        logger.error(
            "url=%s\nheaders=%s\nbody=%s\n",
            crumb_response.request.url, crumb_response.request.headers, crumb_response.request.body
        )
        logger.error(auth)
        logger.error(crumb_response.text)
        raise requests.ConnectionError('Could not issue Jenkins crumb.', response=crumb_response)
    return crumb_response.json()


def api_call(self, base_url, auth=None, crumb_url=None):
    def _call(method, api, retries=3):
        url = '{base_url}/{api}'.format(base_url=base_url, api=api)
        header = '[%s %s]' if hasattr(self, 'name') else '[%s]'
        args = [self.__class__.__name__, self.name] if hasattr(self, 'name') else [self.__class__.__name__]
        args_full = args + [method.upper(), url]
        logger.debug("{} External API call %s %s".format(header), *args_full)
        exc_info = None
        for retry in xrange(retries):
            with requests.session() as session:
                try:
                    crumb = perform_crumb_call(session=session, crumb_url=crumb_url, auth=auth)
                    return session.request(method=method, url=url, auth=auth, headers={
                        crumb['crumbRequestField']: crumb['crumb'],
                    })
                except requests.ConnectionError as err:
                    args_retry_fail = args + [retry + 1, retries]
                    logger.exception("{} Try %d/%d failed.".format(header), *args_retry_fail)
                    exc_info = err
        else:
            logger.error("{} API call %s %s failed!".format(header), *args_full)
            raise exc_info
    return _call


class Jenkins(object):
    def __init__(self, url, username, api_token):
        url_match = re.match(r'^(?P<protocol>.*://)?(?P<bare_url>.*)/?$', url).groupdict()
        self.url = '{protocol}{bare_url}'.format(
            protocol=url_match.get('protocol', 'http://'),
            bare_url=url_match['bare_url'],
        )
        self.crumb_url = '{jenkins_url}/crumbIssuer/api/json'.format(
            jenkins_url=self.url
        )
        self.agents = {}
        self.auth = (username, api_token)
        self.job_url = os.getenv('JOB_URL', '{jenkins_url}/job/Jam/'.format(jenkins_url=self.url))
        self._call = api_call(self, base_url=self.url, auth=self.auth, crumb_url=self.crumb_url)

    def get_agent(self, name):
        return self.agents.setdefault(
            name, JenkinsAgent(url=self.url, name=name, auth=self.auth, crumb_url=self.crumb_url)
        )

    @property
    def jobs(self):
        try:
            return [job for job in self._call('get', 'queue/api/json').json()['items']
                    if not job['task'].get('url', None) == self.job_url]
        except requests.ConnectionError:
            logger.exception("[%s] Impossible to retrieve job queue.", self.__class__.__name__)
            raise


class JenkinsAgent(object):
    QUIET_OFFLINE_CAUSES = {
        'hudson.slaves.OfflineCause$ChannelTermination',
    }
    WAIT_TIME_FORCE_LAUNCH = 15

    STATUSES = {
        (False, False, False): AgentStatus.ONLINE_BUSY,
        (False, False, True): AgentStatus.ONLINE_IDLE,
        (False, True, False): AgentStatus.ERROR,
        (False, True, True): AgentStatus.ERROR,
        (True, False, False): AgentStatus.SCHEDULED_FOR_DISCONNECTION,
        (True, False, True): AgentStatus.DISCONNECTED,
        (True, True, False): AgentStatus.SCHEDULED_FOR_SLEEP,
        (True, True, True): AgentStatus.SLEEPING,
    }

    def __init__(self, url, name, auth=None, crumb_url=None):
        self.url = '{}/computer/{}'.format(url, name)
        self.name = name
        self.info = None
        self.auth = auth
        self._call = api_call(self, base_url=self.url, auth=self.auth, crumb_url=crumb_url)

    @property
    def status(self):
        self.refresh()
        return self.STATUSES[(self.info['offline'], self.info['temporarilyOffline'], self.info['idle'])]

    @property
    def is_idle(self):
        self.refresh()
        return self.info['idle']

    @property
    def is_online(self):
        self.refresh()
        return not any([self.info['offline'], self.info['temporarilyOffline']])

    @property
    def is_offline(self):
        self.refresh()
        return self.info['offline']

    @property
    def is_temporarily_offline(self):
        self.refresh()
        return self.info['temporarilyOffline']

    @property
    def offline_cause_reason(self):
        self.refresh()
        if not self.info['offlineCauseReason']:
            return None
        if self.info['offlineCause']['_class'] in self.QUIET_OFFLINE_CAUSES:
            return self.info['offlineCause']['_class']
        return '{} || {}'.format(self.info['offlineCause']['_class'], self.info['offlineCauseReason'])

    def _reconnect(self):
        pass

    def _wake_up(self):
        self.toggle()
        status = self.status

        if status is AgentStatus.DISCONNECTED:
            self._reconnect()

        if status in (AgentStatus.SCHEDULED_FOR_SLEEP, AgentStatus.SLEEPING, AgentStatus.ERROR):
            raise StatusError

    def smart_launch(self):
        status = self.status
        if status in (AgentStatus.ONLINE_BUSY, AgentStatus.ONLINE_IDLE):
            return

        if status is AgentStatus.DISCONNECTED:
            self._reconnect()

        elif status is AgentStatus.SLEEPING:
            self._wake_up()

        elif status is AgentStatus.SCHEDULED_FOR_SLEEP:
            self.toggle()
        else:
            raise StatusError

    def smart_sleep(self):
        status = self.status

        if status in (AgentStatus.DISCONNECTED, AgentStatus.SCHEDULED_FOR_SLEEP, AgentStatus.SLEEPING):
            logger.info("[%s %s] Already off (sleeping, scheduled or disconnected).", self.__class__.__name__, self.name)
            return

        if status is AgentStatus.ONLINE_BUSY:
            logger.info(
                "[%s %s] Agent is online and busy. It will be scheduled for sleep", self.__class__.__name__, self.name
            )
            self.toggle()
            if self.status is AgentStatus.SCHEDULED_FOR_SLEEP:
                return

        elif status is AgentStatus.ONLINE_IDLE:
            logger.info(
                "[%s %s] Agent is online and idle. It will be put to sleep", self.__class__.__name__, self.name
            )
            self.toggle()
            if self.status is AgentStatus.SLEEPING:
                return

        raise StatusError

    def force_launch(self):
        while not self.is_online:
            logger.info("[%s %s] Agent is not launched.", self.__class__.__name__, self.name)
            offline_cause_reason = self.offline_cause_reason
            if offline_cause_reason is not None:
                logger.info(
                    "[%s %s] Agent is offline because %s.", self.__class__.__name__, self.name, offline_cause_reason
                )
                self.launch()
            time.sleep(self.WAIT_TIME_FORCE_LAUNCH)
        logger.info("[%s %s] Agent is launched.", self.__class__.__name__, self.name)

    def refresh(self):
        try:
            self.info = self._call('get', 'api/json').json()
        except requests.ConnectionError:
            logger.exception("[%s %s] Impossible to get information about this agent!",
                             self.__class__.__name__, self.name)
            raise

    def launch(self):
        logger.info("[%s %s] Launching Agent.", self.__class__.__name__, self.name)
        self._call('post', 'launchSlaveAgent')

    def stop(self):
        logger.info("[%s %s] Stopping Agent.", self.__class__.__name__, self.name)
        self._call('post', 'doDisconnect?offlineMessage=jam.stop')

    def toggle(self):
        logger.info("[%s %s] Agent is %s.", self.__class__.__name__, self.name,
                    'online' if self.is_online else 'offline')
        logger.info("[%s %s] Toggling Agent.", self.__class__.__name__, self.name)
        self._call('post', 'toggleOffline?offlineMessage=jam.toggle')
        logger.info("[%s %s] Agent is %s.", self.__class__.__name__, self.name,
                    'online' if self.is_online else 'offline')
