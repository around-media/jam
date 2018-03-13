import sys

import jam


def test_args():
    sys.argv[1:] = ('--project=jam-project '
                    '--jenkins-url=mock://jenkins.mydomain.com:8080 '
                    '--jenkins-api-token=pass '
                    '--jenkins-username=user '
                    'build1 build2').split()
    args = jam.parse_args()
    assert ['build1', 'build2'] == args.nodes
    assert 'europe-west1-b' == args.gce_zone
    assert set(vars(args).keys()) == {'project', 'jenkins_api_token', 'jenkins_url', 'gce_zone', 'nodes',
                                      'jenkins_username'}
