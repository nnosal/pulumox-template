#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "pulumi>=3.0.0",
# ]
# ///
# Test? uv run src/tools/pulumi_inventory.py && ansible all -i src/tools/pulumi_inventory.py --list-hosts && ansible -i src/tools/pulumi_inventory.py NODE1 -m command -a "ls"
import json, os
import pulumi
import pulumi.automation as auto
from pulumi.automation import LocalWorkspace
from pathlib import Path

def clean_ip(ip):
    """Supprime le suffixe CIDR si présent."""
    return str(ip).split('/')[0] if '/' in str(ip) else str(ip)

def get_pulumi_inventory(stack_name, project_path):
    inventory = {
        "all": {
            "hosts": [],
            "children": {
                "proxmox_nodes": {"hosts": []},
                "proxmox_vms": {"hosts": []}
            }
        },
        "_meta": {"hostvars": {}}
    }

    try:
        stack = auto.create_or_select_stack(
            stack_name=stack_name,
            work_dir=project_path,
            program=lambda: None
        )
        outputs = stack.outputs()

        # --- Nodes ---
        proxmox_nodes_data = outputs.get("proxmox_nodes_data")
        if proxmox_nodes_data:
            nodes_dict = proxmox_nodes_data.value
            #read_key = lambda v: Path(os.path.expanduser(v)).read_text() if Path(os.path.expanduser(v)).is_file() else v
            for node_name, node_info in nodes_dict.items():
                ip = node_info.get("ip")
                #ssh_info = node_info.get("_ssh", {})
                ansible_user = os.environ.get("PULUMOX_SSH_USER", "root")

                inventory["all"]["hosts"].append(node_name)
                inventory["all"]["children"]["proxmox_nodes"]["hosts"].append(node_name)
                inventory["_meta"]["hostvars"][node_name] = {
                    "ansible_host": ip or node_name,
                    "ansible_user": ansible_user
                }
                #if ansible_key: inventory["_meta"]["hostvars"][node_name]["ansible_ssh_private_key"] = os.environ.get("PULUMOX_SSH_PRIVATKEY")
                inventory["_meta"]["hostvars"][node_name]["ansible_ssh_private_key_file"] = os.environ.get("PULUMOX_SSH_PRIVATKEY_FILE", "~/.ssh/id_rsa")

        # --- VMs ---
        vms_data = outputs.get("vms_data")
        if vms_data:
            vms_dict = vms_data.value
            for vm_name, vm_info in vms_dict.items():
                ipv4_address = None
                username = vm_info.get("username", "root")
                ssh_keys = vm_info.get("ssh_keys", [])

                if "ipv4_address" in vm_info:
                    ipv4_address = clean_ip(vm_info["ipv4_address"])
                elif "ipConfigs" in vm_info:
                    for cfg in vm_info["ipConfigs"]:
                        if cfg.get("ipv4"):
                            ipv4_address = clean_ip(cfg["ipv4"]["address"])
                            break

                if ipv4_address:
                    inventory["all"]["hosts"].append(vm_name)
                    inventory["all"]["children"]["proxmox_vms"]["hosts"].append(vm_name)
                    inventory["_meta"]["hostvars"][vm_name] = {
                        "ansible_host": ipv4_address,
                        "ansible_user": username
                    }
                    if ssh_keys:
                        inventory["_meta"]["hostvars"][vm_name]["ansible_ssh_private_key"] = ssh_keys[0]

    except Exception as e:
        pulumi.log.error(f"Erreur Pulumi: {str(e)}")
        return {"_meta": {"hostvars": {}}}

    return inventory

if __name__ == "__main__":
    project_path = os.path.abspath("./")
    ws = LocalWorkspace(work_dir=project_path)
    current_stack = ws.stack().name  # récupère la stack active
    inventory = get_pulumi_inventory(
        stack_name=current_stack,
        project_path=project_path
    )
    print(json.dumps(inventory, indent=4))
