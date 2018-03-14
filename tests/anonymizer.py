import random
import json
import collections


def random_ip():
    """Generates a random IP v4.

    :return str: a random IP address.
    """
    return '{}.{}.{}.{}'.format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))


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
    anon_email = "012345678942-compute@developer.gserviceaccount.com"
    with open(filepath, 'r') as f:
        out = f.read()
    for translation in translations:
        out = out.replace(translation[0], translation[1])
    json_out = json.loads(out, object_pairs_hook=collections.OrderedDict)
    if 'items' in json_out:
        for item in json_out['items']:
            if 'networkInterfaces' in item:
                for interface in item['networkInterfaces']:
                    if 'accessConfigs' in interface:
                        for config in interface['accessConfigs']:
                            if 'natIP' in config:
                                # $.items[*].networkInterfaces[*].accessConfigs[*].natIP
                                print 'Replacing IP {}'.format(config['natIP'])
                                config['natIP'] = random_ip()
            if 'serviceAccounts' in item:
                for account in item['serviceAccounts']:
                    if 'email' in account:
                        # $.items[*].serviceAccounts[*].email
                        print 'Replacing email {} => {}'.format(account['email'], anon_email)
                        account['email'] = anon_email
            if 'metadata' in item and 'items' in item['metadata']:
                for index, metadata_item in enumerate(item['metadata']['items'][:]):
                    if metadata_item.get('key') == 'windows-keys':
                        # $.items[*].metadata.items[?(@.key == "windows-keys")]
                        del item['metadata']['items'][index]
    with open(filepath, 'w') as f:
        json.dump(json_out, f, indent=1, separators=(',', ': '))
