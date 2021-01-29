#!/usr/bin/env python3

'''
Dynamic inventory from remote yaml
'''

import argparse

from configparser import ConfigParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.error import URLError

import json
import os
import yaml


class ZTPInventory(object):

    def __init__(self):
        self.inventory = {}
        self.read_cli_args()
        self.get_inventory()

    def get_inventory(self):
        if not self.args.list:
            print(json.dumps(self.empty_inventory()))

        # secrets file can be retrieved from $HOME/.ztp/secrets
        secrets_file = str(Path.home())+"/.ztp/secrets"
        secrets = self.get_secrets(secrets_file)
        if not secrets:
            print(json.dumps(self.empty_inventory()))

        # the url can be read from env var
        if not os.environ.get("INVENTORY_URL"):
            print(json.dumps(self.empty_inventory()))

        print(json.dumps(self.inventory_from_url(
            os.environ.get("INVENTORY_URL"), secrets)))

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
        general_vars = {
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

        # check if we need to include controlplane data
        if inventory.get("controlplane"):
            general_vars["provision_controlplane"] = True
            general_vars["libvirt_uri"] = \
                inventory["controlplane"]["libvirt_uri"]
            general_vars["bridge_name"] = inventory["controlplane"]["bridge"]
        else:
            general_vars["provision_controlplane"] = False

        inventory_content = {"all": {"vars": general_vars},
                             "children": ["provisioner",
                                          "ungrouped",
                                          "worker_nodes"],
                             "_meta": {"hostvars": {}},
                             "worker_nodes": {"hosts": []}}

        # now check the workers
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
            inventory_content["worker_nodes"]["hosts"].append(
                worker["hostname"])
            inventory_content["_meta"]["hostvars"][worker["hostname"]] = worker

        # finally, assign needs_bmc
        inventory_content["all"]["vars"]["need_racadm"] = needs_racadm
        return inventory_content

    # Empty inventory for testing.
    def empty_inventory(self):
        return {"_meta": {"hostvars": {}}}

    # Read the command line args passed to the script.
    def read_cli_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--list', action='store_true',
                            help="Returns the full inventory list")
        parser.add_argument('--host', help="Returns empty inventory")
        self.args = parser.parse_args()


# Get the inventory.
ZTPInventory()
