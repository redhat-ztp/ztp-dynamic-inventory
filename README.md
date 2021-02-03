
# ztp-dynamic-inventory
The purpose of this repository is to create a dynamic inventory based on a yaml file, to be used together with https://github.com/redhat-ztp/ztp-cluster-deploy 
This combination will allow to deploy clusters automatically, based on yaml files stored in any git repository

## Prerequisites
**Secrets**
As the main goal of the dynamic inventory is to push it into some git repository, it means that the secrets cannot be pushed and need to remain in a local folder. In order to consume the dynamic inventory, you will need to create a secrets file in $HOME/.ztp/secrets path (or a different one, that can be configured). The file needs to have the following format:

    [default]
    pull_secret=<your pull secret in json format>
    ssh_pubkey=<the pubkey used to ssh into the servers>
You can specify a custom secrets path by exporting the env var before running the playbook:

    export SECRETS_FILE=/path/to/secrets

**Provisioner host**
This dynamic inventory allows to define the inventory for control plane and workers, but is not defining any setting for the provisioner host. In order to include the provisioner host in the inventory, two environment vars need to be exported:

    export PROVISIONER_HOST=ip_or_hostname_of_your_provisioner | localhost
    export PROVISIONER_METHOD=ssh | local

The PROVISIONER_HOST var needs to contain the IP of the hostname of your provisioner, where all the ansible tasks are going to be executed. You can use localhost to run locally as well.
The PROVISIONER_METHOD specifies the type of connection to use . It needs to be ssh if the provisioner is a remote host, or local if you are executing in localhost
By exporting these two vars, the same inventory file can be reused and be run in different environments

## How to use
This component is written as an ansible dynamic inventory generator, so it can be used when running the playbook.
You will need to copy the inventory.py file of this repository inside your local system, and then run:

    ansible-playbook -vvv -i /path/to/inventory.py playbook.yml

Inside the https://github.com/redhat-ztp/ztp-cluster-deploy/tree/master/ai-deploy-cluster-remoteworker folder
This script will generate a dynamic inventory based on a yaml file, that needs to follow the following format: https://raw.githubusercontent.com/redhat-ztp/ztp-dynamic-inventory/main/sample_inventory.yaml

You can store the sample_inventory.yaml file locally, or push it into some git repository. To specify the path of the yaml file to use, the INVENTORY_URL var needs to be exported:

    export INVENTORY_URL=/path/to/inventory.yaml | http://url/to/inventory.yaml

After being exported this var, along with the PROVISIONER_* vars and the secrets, you can run the ansible playbook and the cluster will be deployed automatically based on the settings of the yaml file
