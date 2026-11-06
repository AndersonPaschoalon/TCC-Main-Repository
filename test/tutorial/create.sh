#!/usr/bin/env bash
# Cria a estrutura de pastas e arquivos vazios do repositório slurm-lab.
# Pode ser executado várias vezes: não sobrescreve arquivos existentes.
set -euo pipefail

PROJETO="slurm-lab"

mkdir -p "$PROJETO"/{inventory,group_vars,docs} \
         "$PROJETO"/roles/{base,munge,slurm}/{tasks,handlers} \
         "$PROJETO"/roles/slurm/templates

cd "$PROJETO"

# Cria arquivos vazios apenas se ainda não existirem.
touch -a ansible.cfg inventory/hosts.yml group_vars/all.yml site.yml docs/ambiente-host.md
for role in base munge slurm; do
  [ -f "roles/$role/tasks/main.yml" ] || echo "[]" > "roles/$role/tasks/main.yml"
done
[ -f roles/slurm/handlers/main.yml ] || echo "[]" > roles/slurm/handlers/main.yml

# Git: inicia o repositório apenas uma vez.
if [ ! -d .git ]; then
  git init -q
  printf '%s\n' '*.retry' '.vault_pass' > .gitignore
fi

echo "Estrutura criada em ./$PROJETO"