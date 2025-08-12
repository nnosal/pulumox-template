#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "pulumi>=3.0.0",
# ]
# ///
import json, os, pulumi
import pulumi.automation as auto
from pulumi.automation import LocalWorkspace

def clean_ip(ip):
    return str(ip).split('/')[0] if '/' in str(ip) else str(ip)

def get_pulumi_inventory(stack_name, project_path):
    inventory = {
        "all": {
            "hosts": [],  # Liste des noms d'hôtes
            "children": {}
        }, "_meta": { "hostvars": {} } # Variables d'hôtes séparées
    }
    
    try:
        ws = LocalWorkspace(work_dir=project_path)
        stack = auto.create_or_select_stack(
            stack_name=stack_name,
            work_dir=project_path,
            program=lambda: None
        )
        state = stack.export_stack()

        if state and state.deployment:
            for resource in state.deployment.get('resources', []):
                if resource.get('type') == 'proxmoxve:VM/virtualMachine:VirtualMachine':
                    outputs = resource.get('outputs', {})
                    inputs = resource.get('inputs', {})
                    
                    # Extraction data
                    name = outputs.get('name', 'unknown')
                    ipv4_address = None

                    # Extraction data-IP
                    if outputs.get('ipv4_address'):
                        ipv4_address = clean_ip(outputs['ipv4_address'])
                    else:
                        ip_configs = outputs.get('initialization', {}).get('ipConfigs') or inputs.get('initialization', {}).get('ipConfigs')
                        if ip_configs:
                            for entry in ip_configs:
                                if entry.get('ipv4'):
                                    ipv4_address = clean_ip(entry['ipv4']['address'])
                                    break

                    # Configuration utilisateur
                    user_data = outputs.get('initialization', {}).get('userAccount', {})
                    ssh_keys = user_data.get('keys', [])
                    username = user_data.get('username', 'root')

                    # Construction des variables Ansible
                    if ipv4_address:
                        inventory["all"]["hosts"].append(name)
                        inventory["_meta"]["hostvars"][name] = {
                            "ansible_host": ipv4_address,
                            "ansible_user": username,
                        }
                        
                        # Ajout de la clé SSH
                        if ssh_keys:
                            if len(ssh_keys) > 0:
                                inventory["_meta"]["hostvars"][name]["ansible_ssh_private_key"] = ssh_keys[0]

    except Exception as e:
        pulumi.error(f"Erreur Pulumi: {str(e)}")
        return {"_meta": {"hostvars": {}}}

    return inventory

if __name__ == "__main__":
    inventory = get_pulumi_inventory(
        stack_name="dev_test",
        project_path=os.path.abspath("./")
    )
    print(json.dumps(inventory, indent=4))