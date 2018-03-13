import argparse
import time

import libs.core


def parse_args():
    parser = argparse.ArgumentParser(description="Jenkins Agent Manager -- Manages agents on Google Compute Engine.")

    gce_group = parser.add_argument_group(title="Google Compute Engine", description="GCE-related arguments")
    gce_group.add_argument('-p', '--project', action='store', required=True, type=str,
                           help="Name of the Google Compute Engine project")
    gce_group.add_argument('-z', '--gce-zone', action='store', type=str, default='europe-west1-b', dest='gce_zone',
                           help="Google Compute Engine zone (see https://cloud.google.com/compute/docs/regions-zones/ )"
                           )

    j_group = parser.add_argument_group(title="Jenkins", description="Jenkins-related arguments")
    j_group.add_argument('-l', '--jenkins-url', action='store', required=True, type=str, dest='jenkins_url',
                         help="URL to the Jenkins Server")
    j_group.add_argument('-u', '--jenkins-username', action='store', type=str,
                         help="The Jenkins user")
    j_group.add_argument('-t', '--jenkins-api-token', action='store', type=str,
                         help="The Jenkins API Token")

    parser.add_argument('nodes', action='store', metavar='NODE_LIST', nargs='+',
                        help="Names of the nodes to use")

    args = parser.parse_args()

    if not args.nodes:
        parser.print_help()
        exit(1)

    return args


def monitor():
    args = parse_args()
    jam = libs.core.Jam(
        jenkins_url=args.jenkins_url,
        jenkins_username=args.jenkins_username,
        jenkins_api_token=args.jenkins_api_token,
        project=args.project,
        gce_zone=args.gce_zone,
        usable_nodes=args.nodes,
    )

    while True:
        jam.balance_nodes()
        time.sleep(5)


if __name__ == '__main__':
    import logging
    import sys
    FORMAT = "[%(levelname)-7s] %(asctime)-15s %(filename)20s:%(lineno)-4d >> %(message)s"
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=FORMAT)
    logging.getLogger('googleapiclient.discovery').setLevel(logging.WARNING)
    monitor()
