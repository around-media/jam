import logging
import os
import re
import time

import requests

logger = logging.getLogger(__name__)


def api_call(self, base_url, auth=None):
    def _call(method, api):
        url = '{base_url}/{api}'.format(base_url=base_url, api=api)
        header = '[%s %s]' if hasattr(self, 'name') else '[%s]'
        args = [self.__class__.__name__, self.name] if hasattr(self, 'name') else [self.__class__.__name__]
        logger.debug("{} External API call {} {}".format(header, method.upper(), url), *args)
        with requests.session() as session:
            crumb_response = session.get(
                url='{jenkins_url}/crumbIssuer/api/json?xpath=concat(//crumbRequestField,":",//crumb)'.format(
                    jenkins_url=base_url
                ),
                auth=auth,
            )
            if crumb_response.status_code == 200:
                crumb = crumb_response.json()
                return session.request(method=method, url=url, auth=auth, headers={
                    crumb['crumbRequestField']: crumb['crumb'],
                })
            else:
                logger.error("url=%s\nheaders=%s\nbody=%s\n", crumb_response.request.url, crumb_response.request.headers, crumb_response.request.body)
                logger.error(auth)
                logger.error(crumb_response.text)
                raise requests.ConnectionError('Could not issue Jenkins crumb.', response=crumb_response)
    return _call


class Jenkins(object):
    def __init__(self, url, username, api_token):
        url_match = re.match(r'^(?P<protocol>https?://)?(?P<bare_url>.*)/?$', url).groupdict()
        self.url = '{protocol}{bare_url}'.format(
            protocol=url_match.get('protocol', 'http://'),
            bare_url=url_match['bare_url'],
        )
        self.agents = {}
        self.auth = (username, api_token)
        self.job_url = os.getenv('JOB_URL', '{jenkins_url}/job/Jam/'.format(jenkins_url=self.url))
        self._call = api_call(self, self.url, self.auth)

    def get_agent(self, name):
        return self.agents.setdefault(name, JenkinsAgent(url=self.url, name=name, auth=self.auth))

    @property
    def jobs(self):
        return [job for job in self._call('get', 'queue/api/json').json()['items']
                if not job['task'].get('url', None) == self.job_url]


class JenkinsAgent(object):
    QUIET_OFFLINE_CAUSES = {
        'hudson.slaves.OfflineCause$ChannelTermination',
    }

    def __init__(self, url, name, auth=None):
        self.url = '{}/computer/{}'.format(url, name)
        self.name = name
        self.info = None
        self.auth = auth
        self._call = api_call(self, self.url, self.auth)

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

    def force_launch(self):
        while not self.is_online:
            logger.info("[%s %s] Agent is not launched.", self.__class__.__name__, self.name)
            offline_cause_reason = self.offline_cause_reason
            if offline_cause_reason is not None:
                logger.info(
                    "[%s %s] Agent is offline because %s.", self.__class__.__name__, self.name, offline_cause_reason
                )
                logger.info("[%s %s] Attempting to launch agent.", self.__class__.__name__, self.name)
                self.launch()
            time.sleep(15)
        logger.info("[%s %s] Agent is launched.", self.__class__.__name__, self.name)

    def refresh(self):
        self.info = self._call('get', 'api/json').json()

    def launch(self):
        logger.info("[%s %s] Launching Agent.", self.__class__.__name__, self.name)
        self._call('post', 'launchSlaveAgent')

    def stop(self):
        logger.info("[%s %s] Stopping Agent.", self.__class__.__name__, self.name)
        self._call('post', 'doDisconnect?offlineMessage=auto')
