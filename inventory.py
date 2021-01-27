#!/usr/bin/env python

'''
Takes a yaml inventory from an url and combines it with local secrets,
to create a final inventory, to automate ZTP cluster deploy
'''

import argparse

from configparser import ConfigParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.error import URLError

import yaml

try:
    import json
except ImportError:
    import simplejson as json


class ZTPInventory(object):

    def __init__(self):
        self.inventory = {}
        self.read_cli_args()

        # Called with `--url`.
        if self.args.url:
            secrets = self.get_secrets(self.args.secrets_file)
            if not secrets:
                print("Error finding secrets file. Cannot continue")
                return None

            self.inventory = self.inventory_from_url(self.args.url, secrets)
        else:
            # just return an empty inventory
            self.inventory = self.empty_inventory()

        print(json.dumps(self.inventory))

    # reads secrets content from file. Return false if not exists
    def get_secrets(self, secrets_path):
        parser = ConfigParser()
        try:
            parser.read(secrets_path)
            secrets = {"pull_secret": parser.get('default', 'pull_secret'),
                       "ssh_pubkey": parser.get('default', 'ssh_pubkey')}
            return secrets
        except Exception:
            return False

    # retrieves an inventory from a yaml url/file
    def retrieve_yaml_inventory(self, url):
        try:
            config_uri_parsed = urlparse(url)
            if config_uri_parsed.scheme in ['https', 'http']:
                url = urlopen(url)
                yaml_data = url.read()
            else:
                with open(url, 'r') as file_data:
                    yaml_data = file_data.read()
        except URLError as e:
            print(e)

        # Parse the YAML configuration
        try:
            inventory_data = yaml.safe_load(yaml_data)
            return inventory_data[0]
        except yaml.YAMLError as e:
            print(e)
            return None

    # generate inventory from a yaml in an url
    def inventory_from_url(self, url, secrets):
        # retrieve the content
        inventory = self.retrieve_yaml_inventory(url)

        # now combine the content of yaml with secrets
        # to produce a final inventory
        inventory_content = {
                "all": {
                    "vars": {
                        "pull_secret": secrets["pull_secret"],
                        "ssh_public_key": secrets["ssh_pubkey"],
                        "ai_url": inventory["installer_url"],
                        "ignition_url": inventory["ignition_url"],
                        "rootfs_url": inventory["rootfs_url"],
                        "cluster_name": inventory["name"],
                        "cluster_domain": inventory["domain"],
                        "cluster_version": inventory["version"],
                        "ingress_vip": inventory["ingress_vip"],
                        "api_vip": inventory["api_vip"],
                        "ignition_http_server_path":
                            inventory["ignition_http_server_path"],
                        "temporary_path": inventory["temporary_path"]
                    }
                }
            }

        # check if we need to include controlplane data
        if inventory.get("controlplane"):
            inventory_content["all"]["vars"]["provision_controlplane"] = True
            inventory_content["all"]["vars"]["libvirt_uri"] = \
                inventory["controlplane"]["libvirt_uri"]
            inventory_content["all"]["vars"]["bridge_name"] = \
                inventory["controlplane"]["bridge"]
        else:
            inventory_content["all"]["vars"]["provision_controlplane"] = False

        # now check the workers
        inventory_content["worker_nodes"] = {
                "hosts": {}
        }

        needs_racadm = False
        for worker in inventory["workers"]:
            # if at least exists one Dell, we need bmc
            if worker["bmc"]["type"] == "Dell":
                needs_racadm = True

            # general worker settings
            worker_info = {
                "bmc_type": worker["bmc"]["type"],
                "bmc_address": worker["bmc"]["address"],
                "bmc_user": worker["bmc"]["user"],
                "bmc_password": worker["bmc"]["password"],
                "ramdisk_path": worker["ramdisk_path"]
            }

            # virtual media settings, if we need those
            if worker.get("virtualmedia"):
                worker_info["final_iso_path"] = \
                        worker["virtualmedia"]["final_iso_path"]
                if worker["virtualmedia"].get("smb_host"):
                    worker_info["smb_host"] = \
                            worker["virtualmedia"]["smb_host"]
                if worker["virtualmedia"].get("smb_path"):
                    worker_info["smb_path"] = \
                            worker["virtualmedia"]["smb_path"]

            # add the worker information
            inventory_content["worker_nodes"]["hosts"][worker["hostname"]] = \
                worker

        # finally, assign needs_bmc
        inventory_content["all"]["vars"]["need_racadm"] = needs_racadm
        print(inventory_content)

    # Empty inventory for testing.
    def empty_inventory(self):
        return {'_meta': {'hostvars': {}}}

    # Read the command line args passed to the script.
    def read_cli_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--url', action='store')
        parser.add_argument('--secrets_file', action='store',
                            default=str(Path.home())+"/.ztp/secrets")
        self.args = parser.parse_args()


# Get the inventory.
if __name__ == "__main__":
    ZTPInventory()
