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
    return '{}.{}.{}.{}'.format(
        random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
    )


def anonymize_email(root):
    anon_email = "012345678942-compute@developer.gserviceaccount.com"
    for account in root.get('serviceAccounts', []):
        if 'email' in account:
            # $.serviceAccounts[*].email
            print 'Replacing email {} => {}'.format(account['email'], anon_email)
            account['email'] = anon_email


def anonymize_ip(root):
    for interface in root.get('networkInterfaces', []):
        for config in interface.get('accessConfigs', []):
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


def anonymize_by_translations(text, translations):
    for translation in translations:
        text = text.replace(translation[0], translation[1])
    return text


def anonymize_json(root):
    kind = get_item_kind(root)
    if kind == ItemKind.INSTANCE_LIST:
        for item in root.get('items', []):
            anonymize_instance(item)
    elif kind == ItemKind.INSTANCE:
        anonymize_instance(root)
    elif kind == ItemKind.OPERATION:
        root['user'] = 'anonymous.user@anonymo.us'


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

    out = anonymize_by_translations(text=out, translations=translations)

    json_out = json.loads(out, object_pairs_hook=collections.OrderedDict)
    anonymize_json(json_out)

    with open(filepath, 'w') as f:
        json.dump(json_out, f, indent=1, separators=(',', ': '))
