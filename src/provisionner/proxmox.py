# https://www.pulumi.com/registry/packages/proxmoxve/api-docs/
import os
import pulumi_command as command
import pulumi, pulumi_proxmoxve as proxmox
from .base import BaseProvider

class ProxmoxProvider(BaseProvider):

    VALID_PROVIDER_KEYS = {
        'api_token', 'auth_ticket', 'csrf_prevention_token',
        'endpoint', 'insecure', 'min_tls', 'otp', 'username', 'password',
        'random_vm_id_end', 'random_vm_id_start', 'random_vm_ids',
        # 'ssh', # weirdly 'ssh' is not valid for pulumi
        'tmp_dir' }

    def __init__(self, name: str, config: dict) -> None:
        #super().__init__(**kwargs)
        try:
            if 'ssh' in config: del config['ssh'] # fix pulumi bug "ssh" key
            self.set_config(config)
            if self.config:
                self.provider = proxmox.Provider( resource_name=name, **self.config )
                if self.provider: self.test_provider() # test connect
                self.set_default_ssh_keys()
                self.vms = lambda config_file, post=None: self.provision(config_file, post, type="vms")
                self.lxcs = lambda config_file, post=None: self.provision(config_file, post, type="lxcs")
        except Exception as e:
            print(f"Erreur: Proxmox credential not correct: {str(e)}")
            raise e

    def test_provider(self) -> proxmox.cluster.get_nodes:
        """
        Test the Proxmox provider connection and return available node names.
        """
        try:
            self.nodes_available = proxmox.cluster.get_nodes(opts=pulumi.InvokeOptions(provider=self.provider))
            print(f"Sucess connect. Nodes availables: {self.nodes_available.names}")
        except Exception as e:
            pulumi.log.error(f"Erreur lors de la tentative de connexion Proxmox VE: {e}")

    def get_default_proxmox_node(self) -> str:
        if hasattr(self, 'nodes_available') and self.nodes_available and self.nodes_available.names:
            return self.nodes_available.names[0]
        else:
            raise RuntimeError("Aucun node Proxmox disponible — impossible de récupérer un node par défaut.")

    def test_cmd(self) -> None:
        """
        Test the Proxmox ssh connection and return available node names.
        """
        ssh_connection = command.remote.ConnectionArgs( host=os.getenv( 'SSH_HOST', 'test.lan' ), user=os.getenv( 'SSH_USER', 'root' ), private_key=os.getenv( 'SSH_PRIVATE_KEY_FILE', '' ) )
        testcmd = command.remote.Command( "test-cmd", connection=ssh_connection, create="pwd")
        testcmd.stdout.apply(lambda result: print(f"Résultat de la commande 'pwd': {result}")) #print(testcmd.stdout.__dict__)

    def get_provider(self) -> proxmox:
        """
        Get Proxmox Provider
        """
        return self.provider

    def get_config(self) -> dict:
        """
        Get Config Used for Proxmox Provider
        """
        return self.config

    def read_vm(self, vm_config: dict) -> dict:
        """
        Read YAML-format for manage VM (inspired from: https://blog.jbriault.fr/pulumi-proxmox-cloudinit/)
        Args:
            vm_config: Dictionnaire de configuration YAML pour la VM
        Returns:
            dict: Configuration formatée pour pulumi_proxmoxve
        Raises:
            ValueError: Si la configuration est invalide
        """

        ## 1. DISK
        # disks = [
        #     proxmox.vm.VirtualMachineDiskArgs(
        #         interface=disk['interface'],
        #         datastore_id=disk['datastore_id'],
        #         size=disk['size'],
        #         file_format=disk['file_format'],
        #         file_id=disk.get('file_id',''),
        #         cache=disk['cache'],
        #         ({'import_from': disk['import_from']} if 'import_from' in disk else {})
        #     )
        #     for disk_entry in vm_config.get('disks', [])
        #     for disk in [disk_entry.popitem()[1]]
        # ]
        disks = [
            proxmox.vm.VirtualMachineDiskArgs(
                interface=disk['interface'],
                datastore_id=disk['datastore_id'],
                cache=disk.get('cache', 'none'),
                **{key: disk[key] for key in ['file_format', 'size', 'file_id', 'import_from','path_in_datastore', 'replicate'] if key in disk}
            )
            for disk_entry in vm_config.get('disks', [])
            for disk in [disk_entry.popitem()[1]]
        ]
        ## 2. NETWORK
        ip_configs = []
        if vm_config.get('cloud_init', {}).get('ip_configs', {}):
            for ip_config in vm_config['cloud_init']['ip_configs']:
                config_args = {}
                if 'ipv4' in ip_config:
                    config_args['ipv4'] = proxmox.vm.VirtualMachineInitializationIpConfigIpv4Args(**ip_config['ipv4'])
                if 'ipv6' in ip_config:
                    config_args['ipv6'] = proxmox.vm.VirtualMachineInitializationIpConfigIpv6Args(**ip_config['ipv6'])
                ip_configs.append(proxmox.vm.VirtualMachineInitializationIpConfigArgs(**config_args))
        # 3. FIX SSH KEYS
        if self.ssh_keys_vm:
            try:
                vm_config['cloud_init']['user_account']['keys'] = self.ssh_keys_vm
            except Exception as e:
                print("Skip add ssh_key")

        # 3. CDROMS (but not allowed by pulumi_proxmoxve)
        # cdroms = [
        #     proxmox.vm.VirtualMachineCdromArgs(
        #         interface=cdrom['interface'],
        #         file_id=cdrom.get('file_id',''),
        #     )
        #     for cdrom_entry in vm_config.get('cdroms', [])
        #     for cdrom in [cdrom_entry.popitem()[1]]
        # ]

        ## --> OUTPUT
        config = {
            'operating_system': proxmox.vm.VirtualMachineOperatingSystemArgs( type=vm_config.get('operating_system','other') ),
            'timeout_stop_vm': 5, 'timeout_shutdown_vm': 10, # fix: shutdown vm
            'timeout_reboot': 30, # fix: reboot vm (when updating)
            'vm_id': vm_config['vm_id'],
            'node_name': vm_config['node_name'] if vm_config.get('node_name') and vm_config['node_name'] != 'testnode' else self.get_default_proxmox_node(),
            'name': vm_config['name'],
            'agent': proxmox.vm.VirtualMachineAgentArgs(**vm_config['agent']) if vm_config.get('agent') else None,
            'stop_on_destroy': True if not vm_config.get('agent', {}).get('enabled') else False,
            'disks': disks,
            'cpu': proxmox.vm.VirtualMachineCpuArgs(**vm_config['cpu']) if vm_config.get('cpu') else None,
            'memory': proxmox.vm.VirtualMachineMemoryArgs(**vm_config['memory']) if vm_config.get('memory') else None,
            'network_devices': [
                proxmox.vm.VirtualMachineNetworkDeviceArgs(**net_entry.popitem()[1])
                for net_entry in vm_config.get('network_devices', [])
            ]
        }

        # -> Dynamic inject: ADVANCED MAPPING
        if not vm_config.get('cdrom'): # fix: template require cdrom with ide3 as disabled when update
            config['cdrom'] = proxmox.vm.VirtualMachineCdromArgs(
                file_id="", interface="ide3"
                #enabled="true", file_id="local:iso/my-jammy-server-cloudimg-amd64.img", interface="ide3"
            )
        else:
            config['cdrom'] = proxmox.vm.VirtualMachineCdromArgs(**vm_config.get('cdrom'))

        if vm_config.get('cloud_init'):
            config['initialization'] = proxmox.vm.VirtualMachineInitializationArgs(
                type=vm_config['cloud_init']['type'],
                datastore_id=vm_config['cloud_init']['datastore_id'],
                dns=proxmox.vm.VirtualMachineInitializationDnsArgs(
                    domain=vm_config['cloud_init']['dns']['domain'],
                    servers=vm_config['cloud_init']['dns']['server'].split()
                ),
                ip_configs=ip_configs,
                user_account=proxmox.vm.VirtualMachineInitializationUserAccountArgs(
                    **vm_config['cloud_init']['user_account']
                )
            )
        if vm_config.get('clone'):
            config['clone'] = proxmox.vm.VirtualMachineCloneArgs(**vm_config['clone'])
        if vm_config.get('vga'):
            config['vga'] = proxmox.vm.VirtualMachineVgaArgs(**vm_config['vga'])
        if vm_config.get('serial_devices', {}).get('device', {}):
            config['serial_devices'] = proxmox.vm.VirtualMachineSerialDeviceArgs(device=vm_config['serial_devices']['device'])
        if vm_config.get('efi_disk'):
            config['efi_disk'] = proxmox.vm.VirtualMachineEfiDiskArgs(**vm_config['efi_disk'])
            print(vm_config['efi_disk'])
        if vm_config.get('tpm_state'):
            config['tpm_state'] = proxmox.vm.VirtualMachineTpmStateArgs(**vm_config['tpm_state'])
        if vm_config.get('kvm_arguments'):
            valid_lines = [
                line.strip()
                for line in vm_config.get('kvm_arguments').splitlines()
                if line.strip() and not line.strip().startswith('#')
            ]
            config['kvm_arguments'] = ' '.join(valid_lines) #if '\n' in vm_config.get('kvm_arguments') else vm_config.get('kvm_arguments')

        # -> Dynamic inject: SIMPLE MAPPING
        # Autres paramètres optionnels
        optional_params = {
            'description': 'description',
            'pool_id': 'pool',
            'protection': 'protection',
            'template': 'template',
            'tags': 'tags',
            'boot_orders': 'boot_orders',
            'hook_script_file_id': 'hook_script_file_id',
            'bios': 'bios',
            'on_boot': 'on_boot',
            'machine': 'machine',
            'keyboard_layout': 'keyboard_layout',
            'balloon': 'balloon'
        }
        for param_name, config_key in optional_params.items():
            if config_key in vm_config:
                config[param_name] = vm_config[config_key]
        return config

    def read_lxc(self, lxc_config: dict) -> dict:
        """
        Read YAML-format for manage LXC (inspired from: https://blog.jbriault.fr/pulumi-proxmox-cloudinit/)
        Args:
            lxc_config: Dictionnaire de configuration YAML pour le containeur LXC
        Returns:
            dict: Configuration formatée pour pulumi_proxmoxve
        Raises:
            ValueError: Si la configuration est invalide
        """
        # On reprend la pattern pour les VM
        config = {
            'vm_id': lxc_config['vm_id'],
            'node_name': lxc_config['node_name'],
            'unprivileged': lxc_config.get('unprivileged', True),
            'start_on_boot': lxc_config.get('on_boot', True)
        }
        # Operating System
        default_os = { 'path': 'local:vztmpl', 'template_file_name': 'debian-12-turnkey-core_18.1-1_amd64.tar.gz', 'type': 'debian'}
        config['operating_system'] = proxmox.ct.ContainerOperatingSystemArgs(
            template_file_id= lxc_config.get('os', {}).get('template_file_id', f"{default_os['path']}/{default_os['template_file_name']}" ),
            type=lxc_config.get('os', {}).get('type', default_os['type'])
        )
        # Network Interfaces
        if 'network_devices' in lxc_config:
            config['network_interfaces'] = [
                proxmox.ct.ContainerNetworkInterfaceArgs(
                    name=f"eth{i}",
                    bridge=net['bridge'],
                    enabled=True,
                    firewall=net.get('firewall', False),
                    mac_address=net.get('mac_address',''),
                    #mtu=net.get('mtu',0),
                    #rate_limit=net.get('rate',''),
                    #vlan_id=net.get('vlan_id',0)
                )
                for i, net_entry in enumerate(lxc_config['network_devices'])
                for net in [net_entry.popitem()[1]]
            ]
        # CPU et Mémoire
        if 'cpu' in lxc_config:
            config['cpu'] = proxmox.ct.ContainerCpuArgs(
                cores=lxc_config['cpu'].get('cores', 1),
                units=lxc_config['cpu'].get('units')
            )
        if 'memory' in lxc_config:
            config['memory'] = proxmox.ct.ContainerMemoryArgs(
                dedicated=lxc_config['memory'].get('dedicated'),
                swap=lxc_config['memory'].get('swap')
            )
        # Disque
        if 'rootfs' in lxc_config:
            config['disk'] = proxmox.ct.ContainerDiskArgs(
                datastore_id=lxc_config['rootfs'].get('datastore_id'),
                size=lxc_config['rootfs'].get('size')
            )
        # Mount Points
        if 'mount_points' in lxc_config:
            config['mount_points'] = [
                proxmox.ct.ContainerMountPointArgs(
                    volume=mp.get('volume'),
                    mp=mp.get('mp'),
                    size=mp.get('size')
                )
                for mp in lxc_config['mount_points']
            ]
        # Cloudinit
        if 'cloud_init' in lxc_config:
            cloud_config = lxc_config['cloud_init']
            # Configuration DNS
            dns_config = proxmox.ct.ContainerInitializationDnsArgs(
                domain=cloud_config['dns']['domain'],
                servers=cloud_config['dns']['server'].split()  # Conversion en liste
            )
            # Configuration IP
            ip_configs = []
            for ip_cfg in cloud_config['ip_configs']:
                ipv4_cfg = None
                ipv6_cfg = None
                if 'ipv4' in ip_cfg:
                    ipv4_cfg = proxmox.ct.ContainerInitializationIpConfigIpv4Args(
                        address=ip_cfg['ipv4']['address'],
                        gateway=ip_cfg['ipv4'].get('gateway')
                    )
                if 'ipv6' in ip_cfg:
                    ipv6_cfg = proxmox.ct.ContainerInitializationIpConfigIpv6Args(
                        address=ip_cfg['ipv6']['address'],
                        gateway=ip_cfg['ipv6'].get('gateway')
                    )
                ip_configs.append(proxmox.ct.ContainerInitializationIpConfigArgs(
                    ipv4=ipv4_cfg,
                    ipv6=ipv6_cfg
                ))
            # Configuration utilisateur
            user_account = proxmox.ct.ContainerInitializationUserAccountArgs(
                password="" if not cloud_config['user_account']['password'] or len(cloud_config['user_account']['password']) < 5 else cloud_config['user_account']['password'],
                keys=self.ssh_keys_vm if self.ssh_keys_vm else cloud_config['user_account'].get('keys', [])
            )
            # Configuration Init
            config['initialization'] = proxmox.ct.ContainerInitializationArgs(
                hostname=lxc_config['name'],
                dns=dns_config,
                ip_configs=ip_configs,
                user_account=user_account
            )
        # Autres paramètres optionnels
        optional_params = {
            'description': 'description',
            'pool_id': 'pool',
            'protection': 'protection',
            'template': 'template',
            'tags': 'tags'
        }
        for param_name, config_key in optional_params.items():
            if config_key in lxc_config:
                config[param_name] = lxc_config[config_key]
        # Return final config
        return config

    def add_vm(self, vm_config: dict, name: str = None, depend_on=[] ) -> proxmox.vm.VirtualMachine:
        """
        Add VM
        See doc: https://www.pulumi.com/registry/packages/proxmoxve/api-docs/vm/virtualmachine/
        """
        config = self.read_vm( vm_config )
        name = name if name else config.get('name')
        return proxmox.vm.VirtualMachine(  resource_name=name, **config, opts=pulumi.ResourceOptions(provider=self.provider, depends_on=depend_on) )

    def read_vm2_test(self, vm_config : dict) -> dict:
        """
        Test VM2 (not working)
        """
        cdrom_args = {
            device_name: proxmox.vm.VirtualMachine2CdromArgs( file_id=cdrom_config['file_id'] )
            for device_name, cdrom_config in vm_config.get('cdroms', {}).items()
        }
        config = {
            # REQUIRED
            'name': vm_config['name'],
            'node_name': vm_config['node_name'] if vm_config.get('node_name') and vm_config['node_name'] != 'testnode' else self.get_default_proxmox_node(),
            # SIMPLE
            'description': vm_config['description'] if vm_config.get('description') else None,
            'tags': vm_config.get('tags') if vm_config.get('tags') else None,
            'template': vm_config.get('template') if vm_config.get('template') else None,
            'stop_on_destroy': vm_config.get('stop_on_destroy') if vm_config.get('stop_on_destroy') else None,
            # ADVANCED
            'cdrom': cdrom_args,
            'clone': proxmox.vm.VirtualMachine2CloneArgs(**vm_config['clone']) if vm_config.get('clone') else None,
            'cpu': proxmox.vm.VirtualMachine2CpuArgs(**vm_config['cpu']) if vm_config.get('cpu') else None,
            'rng': proxmox.vm.VirtualMachine2RngArgs(**vm_config['rng']) if vm_config.get('rng') else None,
            'timeouts': proxmox.vm.VirtualMachine2TimeoutsArgs(**vm_config['timeouts']) if vm_config.get('timeouts') else None,
            'vga': proxmox.vm.VirtualMachine2VgaArgs(**vm_config['vga']) if vm_config.get('vga') else None,
        }
        return config

    def add_vm2_test(self, vm_config: dict, name: str = None, depend_on=[] ) -> proxmox.vm.VirtualMachine2:
        """
        Add VM
        See doc: https://www.pulumi.com/registry/packages/proxmoxve/api-docs/vm/virtualmachine2/
        """
        config = self.read_vm2_test( vm_config )
        name = name if name else config.get('name')
        return proxmox.vm.VirtualMachine2(  resource_name=name, **config, opts=pulumi.ResourceOptions(provider=self.provider, depends_on=depend_on) )

    def add_lxc(self, lxc_config: dict, name: str = None, depend_on=[] ) -> proxmox.ct.Container:
        """
        Add LXC container
        See doc: https://www.pulumi.com/registry/packages/proxmoxve/api-docs/ct/container/
        """
        config = self.read_lxc( lxc_config )
        if not name: name = f"lxc-{lxc_config['vm_id']}"
        return proxmox.ct.Container( resource_name=name, **config, opts=pulumi.ResourceOptions(provider=self.provider, depends_on=depend_on) )

    def add_img(self, img_config: dict, content_type: str, method: str = "download") -> proxmox.download.File | proxmox.storage.File:
        """
        Download IMG/ISO into cluster
        @param img_config: Configuration YAML
        @param type: Type IMG ("vztmpl" for container / "iso" for VM or "snippets" for cloud-init.yaml or "dump" for backup file )
        """
        config = {
            "resource_name": img_config.get( "name" ),
            "source_file": { "path": img_config.get( "path", img_config.get( "url", "") ) },
            'node_name': img_config['node_name'] if img_config.get('node_name') and img_config['node_name'] != 'testnode' else self.get_default_proxmox_node(),
            "datastore_id": img_config.get( "datastore_id", "local" ),
            "content_type": img_config.get( "content_type", content_type ),

        }
        if img_config.get( "file_mode"):
            config["file_mode"] = img_config.get("file_mode")
        if method == "download" and not img_config.get("path", "") :
            if config.get('source_file'): del config['source_file']
            if config.get('file_mode'): del config['file_mode']
            config['url'] = img_config.get( "url" )
            config['file_name'] = img_config.get( "file_name" )
            # Default method "download": more faster for url
            return proxmox.download.File( **config, opts=pulumi.ResourceOptions(provider=self.provider) )
        else: # = "storage"
            # Fallback to "storage" method (slow for url but can UPLOAD file - usefull for copy from local to server an img/script )
            return proxmox.storage.File( **config, opts=pulumi.ResourceOptions(provider=self.provider) )

    def add_img2(self, img_config: dict[str,str], img_type: str = "images", img_method: str = "pull") -> proxmox.download.File | proxmox.storage.File:
        """
            Exemple (ISO): self.add_img2({
                'name': 'virtioWin1_ISO", 'url': 'https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso',
                "node_name": "mpro", "datastore_id": "local", 'file_name': '1-virtio-win.iso'
            }, "iso", "pull")
            Exemple (RAW): self.add_img2({
                'name': 'ubuntuLatestNoble", 'url': 'https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img',
                "node_name": "mpro", "datastore_id": "local", 'file_name': '1-noble-server-cloudimg-amd64.img'
            }, "images", "pull")
            Exemple (LXC): self.add_img2({
                'name': 'ubuntuLatestNoble", 'url': 'https://mirror.umd.edu/turnkeylinux/images/proxmox/debian-12-turnkey-core_18.1-1_amd64.tar.gz',
                "node_name": "mpro", "datastore_id": "local", 'file_name': '1-debian-12-turnkey-core_18.1-1_amd64.tar.gz'
            }, "vztmpl", "pull")
           Exemple (Backup+Push): self.add_img2({
                'name': 'ubuntuLatestNoble", 'path': './backup/vzdump-lxc-100-2023_11_08-23_10_05.tar.zst',
                "node_name": "mpro", "datastore_id": "local", 'file_name': '1-vzdump-lxc-100-2023_11_08-23_10_05.tar.zst'
            }, "backup", "push")
           Exemple (Snippets+Push): self.add_img2({
                'name': 'ci-snippet1", 'data': self.makeSnippetOne(),
                "node_name": "mpro", "datastore_id": "local", 'file_name': 'snippet1cloud-init_script1.yaml'
            }, "snippets", "push")
        """
        if not img_config.get("name"): raise ValueError("La clé 'name' est requise pour le nom de la ressource Pulumi.")
        node_name = img_config['node_name'] if img_config.get('node_name') and img_config['node_name'] != 'testnode' else self.get_default_proxmox_node(),
        base_config = { "resource_name": img_config.get("name"), "node_name": node_name, "datastore_id": img_config.get("datastore_id", "local")}
        if img_config.get("overwrite_unmanaged"): base_config["overwrite_unmanaged"] = img_config.get("overwrite_unmanaged")
        # If img_type not "auto" or ""
        if img_type and img_type != "auto":
            content_type_map = {
                "images": "import",  # Pour les images de VM comme .qcow2, .img
                "iso": "iso",
                "vztmpl": "vztmpl",  # Pour les templates de conteneurs LXC
                "backup": "backup",  # Pour les fichiers de sauvegarde vzdump
                "snippets": "snippets" # Pour les fichiers de configuration (ex: Cloud-Init)
            }
            content_type = content_type_map.get(img_type)
            if not content_type:
                raise ValueError(f"Type d'image invalide : '{img_type}'. Les valeurs possibles sont {list(content_type_map.keys())}.")
            else:
                base_config['content_type'] = content_type
        # Run...
        if img_method == "pull":
            # Utilise proxmox.download.File pour télécharger depuis une URL
            # https://www.pulumi.com/registry/packages/proxmoxve/api-docs/download/file/
                # Method structure:
                # file_resource = proxmoxve.download.File("fileResource",
                #     content_type="string", # ["import","iso","vztmpl"] # Must be iso or import for VM images (.img,.qcow2,..) or vztmpl for LXC images.
                #     datastore_id="string",
                #     node_name="string",
                #     url="string",
                #     checksum="string",
                #     checksum_algorithm="string",
                #     decompression_algorithm="string",
                #     file_name="string",
                #     overwrite=False,
                #     overwrite_unmanaged=False,
                #     upload_timeout=0,
                #     verify=False)
                # return proxmox.download.File( **config, opts=pulumi.ResourceOptions(provider=self.provider) )
            allowed_download_types = ["import", "iso", "vztmpl"]
            download_config = {**base_config, "url": img_config.get("url")}
            # Check
            if 'url' not in img_config: raise ValueError("Pour la méthode 'pull', la clé 'url' est requise dans img_config.")
            if content_type and content_type not in allowed_download_types: raise ValueError(f"Le type '{img_type}' n'est pas supporté pour la méthode 'pull'. Types autorisés: 'images', 'iso', 'vztmpl'.")
            # Download...
            if img_config.get("file_name"): download_config["file_name"] = img_config.get("file_name")
            if img_config.get("overwrite_unmanaged"): download_config["overwrite_unmanaged"] = img_config.get("overwrite_unmanaged")
            return proxmox.download.File(**download_config, opts=pulumi.ResourceOptions(provider=self.provider))
        elif img_method == "push":
            # Utilise proxmox.storage.File pour envoyer un fichier local, des données brutes ou une URL (download local puis push)
            # https://www.pulumi.com/registry/packages/proxmoxve/api-docs/storage/file/
                # Method structure:
                # proxmoxve_file_resource = proxmoxve.storage.File("proxmoxveFileResource",
                #     datastore_id="string",
                #     node_name="string",
                #     content_type="string", # ["import","iso","vztmpl", "backup"] # Must be iso or import for VM images (.img,.qcow2,..) or vztmpl for LXC images.
                #     file_mode="string",
                #     overwrite=False,
                #     source_file={
                #         "path": "string",
                #         "changed": False,
                #         "checksum": "string",
                #         "file_name": "string",
                #         "insecure": False,
                #         "min_tls": "string",
                #     },
                #     source_raw={
                #         "data": "string",
                #         "file_name": "string",
                #         "resize": 0,
                #     },
                #     timeout_upload=0)
                # return proxmox.storage.File( **config, opts=pulumi.ResourceOptions(provider=self.provider) )
            storage_config = base_config
            if img_config.get("path"):
                storage_config["source_file"] = {"path": img_config.get("path")}
                if img_config.get("file_name"): storage_config["source_file"]["file_name"] = img_config.get("file_name")
            elif img_config.get("data"):

                if not img_config.get("file_name"):
                    raise ValueError("Pour la méthode 'push' avec 'data', la clé 'file_name' est requise.")
                else:
                    storage_config["source_raw"] = { "data": img_config.get("data"), "file_name": img_config.get("file_name") }
            else:
                raise ValueError("Pour la méthode 'push', les clés 'path' ou 'data' sont requises dans img_config.")

            return proxmox.storage.File(**storage_config, opts=pulumi.ResourceOptions(provider=self.provider))
        else:
            raise ValueError(f"Méthode d'image invalide : '{img_method}'. Doit être 'pull' ou 'push'.")


    def provision(self, config_file: dict, post=None, type: str = None) -> None:
        """
        Provision VMs or LXCs
        @param config_file: Configuration YAML
        @param post: Optional callback function
        @param type: Optional type filter ("vms" or "lxcs")
        """
        result = []
        # Process VMs if present in config and type allows
        if type in (None, "vms"):
            depend_on=[]
            # Process IMG_VM
            for vm_config in config_file.get('vmimgs', []):
                vmimg = self.add_img(vm_config, "iso")
                depend_on.append(vmimg) # vmimg.id)
                if post: post(vmimg)
            # Process TPL2_VM
            for vm2_config in config_file.get('vmtpls2', []):
                vm2tpl = self.add_vm(vm2_config, depend_on=depend_on)
                depend_on.append(vm2tpl) # vmimg.id)
                if post: post(vm2tpl)
            # Process TPL_VM2
            #for vm2_config in config_file.get('vm2testpls', []):
            #    vm2tpl = self.add_vm2_test(vm2_config, depend_on=depend_on)
            #    depend_on.append(vm2tpl) # vmimg.id)
            #    if post: post(vm2tpl)
            # Process TPL_VM
            for vm_config in config_file.get('vmtpls', []):
                vmtpl = self.add_vm(vm_config, depend_on=depend_on)
                depend_on.append(vmtpl) # vmimg.id)
                if post: post(vmtpl)
            # Process VM
            for vm_config in config_file.get('vms', []):
                vm = self.add_vm(vm_config, depend_on=depend_on)
                result.append(vm)
                if post: post(vm)

        # Process LXCs if present in config and type allows
        if type in (None, "lxcs"):
            # Process IMG_CT
            depend_on=[]
            for lxc_config in config_file.get('lxcimgs', []):
                lxcimg = self.add_img(lxc_config, "vztmpl")
                depend_on.append(lxcimg) #lxcimg.id
                if post: post(lxcimg)
            # Process LXC_CT
            for lxc_config in config_file.get('lxcs', []):
                lxc = self.add_lxc(lxc_config, depend_on=depend_on)
                result.append(lxc)
                if post: post(lxc)

if __name__ == "__main__":
    pass
