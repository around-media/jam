import random
import json
import collections
import enum


class ItemKind(enum.Enum):
    INSTANCE = 'compute#instance'
    INSTANCE_LIST = 'compute#instanceList'
    OPERATION = 'compute#operation'
    UNKNOWN = 'unknown'


REVERSED_ITEM_KIND = {ik.value: ik for ik in ItemKind.__members__.itervalues()}


def random_ip():
    """Generates a random IP v4.

    :return str: a random IP address.
    """
    return '{}.{}.{}.{}'.format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))


def anonymize_email(root):
    anon_email = "012345678942-compute@developer.gserviceaccount.com"
    if 'serviceAccounts' in root:
        for account in root['serviceAccounts']:
            if 'email' in account:
                # $.serviceAccounts[*].email
                print 'Replacing email {} => {}'.format(account['email'], anon_email)
                account['email'] = anon_email


def anonymize_ip(root):
    if 'networkInterfaces' in root:
        for interface in root['networkInterfaces']:
            if 'accessConfigs' in interface:
                for config in interface['accessConfigs']:
                    if 'natIP' in config:
                        # $.networkInterfaces[*].accessConfigs[*].natIP
                        print 'Replacing IP {}'.format(config['natIP'])
                        config['natIP'] = random_ip()


def anonymize_windows_keys(root):
    if 'metadata' in root and 'items' in root['metadata']:
        for index, metadata_item in enumerate(root['metadata']['items'][:]):
            if metadata_item.get('key') == 'windows-keys':
                # $.items[*].metadata.items[?(@.key == "windows-keys")]
                del root['metadata']['items'][index]


def anonymize_instance(root):
    # $.items[*].networkInterfaces[*].accessConfigs[*].natIP
    anonymize_ip(root)
    # $.items[*].serviceAccounts[*].email
    anonymize_email(root)
    # $.items[*].metadata.items[?(@.key == "windows-keys")]
    anonymize_windows_keys(root)


def get_item_kind(root):
    return REVERSED_ITEM_KIND[root.get('kind', 'unknown')]


def anonymize(filepath, translations):
    """Anonymizes a json file.

    Will perform the following operations:

        * for each tuple in `translations`, replace any occurrence of the first member by the second member
        * randomizes natIP (at $.items[*].networkInterfaces[*].accessConfigs[*].natIP )
        * replaces any email (at $.items[*].serviceAccounts[*].email ) by a fake one
        * Removes any windows-key that would be present (at $.items[*].metadata.items[?(@.key == "windows-keys")] )

    Please note: the file in `filepath` will be changed inplace!

    :param str filepath: Path to the file to anonymize.
    :param list(tuple) translations: List of translation table to be done
    """
    with open(filepath, 'r') as f:
        out = f.read()
    for translation in translations:
        out = out.replace(translation[0], translation[1])
    json_out = json.loads(out, object_pairs_hook=collections.OrderedDict)
    kind = get_item_kind(json_out)
    if kind == ItemKind.INSTANCE_LIST:
        if 'items' in json_out:
            for item in json_out['items']:
                anonymize_instance(item)
    elif kind == ItemKind.INSTANCE:
        anonymize_instance(json_out)
    elif kind == ItemKind.OPERATION:
        json_out['user'] = 'anonymous.user@anonymo.us'

    with open(filepath, 'w') as f:
        json.dump(json_out, f, indent=1, separators=(',', ': '))
