import subprocess, os, yaml

class LoadFile():
    def __init__(self):
      self.encrypted_find_word = "encrypted"
      self.age_key = "$SOPS_AGE_RECIPIENTS"
      pass

    def yaml(self, file_path):
        try:
            file_name = os.path.basename(file_path).lower()
            # Gestion des fichiers chiffrés
            if self.encrypted_find_word in file_name:
                input_format = "json" if "json" in file_name else "yaml" # json2yaml or yaml2yaml
                return yaml.safe_load( self.decrypt_sops( file_path=file_path, age=self.age_key, input=input_format, output="yaml" ) )
            # Fallback: Lecture directe du fichier YAML
            with open(file_path, 'r') as file: return yaml.safe_load(file)
        except Exception as e:
            raise RuntimeError(f"Error loading YAML file '{file_path}': {str(e)}")

    def decrypt_sops(self, file_path, age="$SOPS_AGE_RECIPIENTS", input="json", output="json" ):
      result = subprocess.run(
        ['sops', '--decrypt', f'--age={age}', f'--input-type={input}', f'--output-type={output}', file_path],
        capture_output=True, text=True
      )
      if result.returncode != 0:
        raise RuntimeError(f"SOPS error: {result.stderr}")
      else:
        return result.stdout


def run_ansible(playbook, inventory="localhost,", working_dir= ".", extra_vars={}, tags="", verbosity=3):
    """
    Exécute un playbook Ansible en utilisant ansible_runner avec gestion des paramètres.
    # Documentation: https://ansible.readthedocs.io/projects/runner/en/latest/ansible_runner/#ansible_runner.interface.run

    :param playbook: Le(s) fichier(s) playbook Ansible à exécuter (chaîne ou liste de chaînes).
    :param inventory: L'inventaire à utiliser pour Ansible (chaîne, dictionnaire ou liste).
    :param extra_vars: Variables supplémentaires pour Ansible (dictionnaire).
    :param tags: Tags à filtrer dans le playbook (chaîne ou liste de chaînes).
    :param verbosity: Niveau de verbosité pour la sortie (entier entre 0 et 4).
    """
    #if not isinstance(playbook, (str, list)) or (isinstance(playbook, str) and not os.path.isfile(os.path.abspath(playbook))):
    #    raise ValueError("Le paramètre 'playbook' doit être une chaîne de caractères valide ou une liste de chaînes.")
    #if not isinstance(inventory, (str, dict, list)):
    #    raise ValueError("Le paramètre 'inventory' doit être une chaîne, un dictionnaire ou une liste.")
    #if not isinstance(extra_vars, dict) or not isinstance(tags, (str, list)) or not isinstance(verbosity, int) or not (0 <= verbosity <= 4):
    #    raise ValueError("Les paramètres 'extra_vars', 'tags' et 'verbosity' doivent être du bon type.")

    def resolve_path(param):
        return os.path.abspath(param) if isinstance(param, str) and os.path.isfile(param) else param
    playbook = resolve_path(playbook)
    inventory = resolve_path(inventory)

    result = ansible_runner.run(
        private_data_dir=working_dir,
        playbook=playbook,
        inventory=inventory, tags=tags, extravars=extra_vars,
        verbosity=verbosity,  # 3 Equivalent de -vvv
    )
    print(f"Ansible Results: {result.status}")
