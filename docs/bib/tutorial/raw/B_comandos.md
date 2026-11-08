# Apêndice B: Comandos de referência

Os comandos estão agrupados pela tarefa que realizam. Os que alteram o sistema são marcados com **(altera)**. Os demais apenas leem o estado.

Todos os comandos do Ansible são executados a partir da raiz do projeto.

---

## Verificar o hardware

```bash
nvidia-smi -L                       # lista as GPUs NVIDIA com o modelo completo
lspci | grep -iE 'vga|3d|display'   # dispositivos gráficos no barramento
lsmod | grep -i nvidia              # módulo do driver carregado
hostname -s                         # nome curto da máquina
nproc                               # número de CPUs disponíveis
free -m                             # memória total e em uso
slurmd -C                           # configuração de hardware vista pelo Slurm
```

## Verificar o sistema

```bash
cat /etc/os-release                 # distribuição e versão
mokutil --sb-state                  # estado do Secure Boot
apt policy <pacote>                 # versão disponível e instalada de um pacote
stat -fc %T /sys/fs/cgroup          # versão do cgroup (cgroup2fs indica a versão unificada)
```

## Ansible: inventário e variáveis

```bash
ansible-inventory --graph           # grupos e hosts, como o Ansible os interpreta
ansible-inventory --host <hostname> # variáveis de um host específico
ansible all -m ansible.builtin.debug -a "var=cluster_name"   # valor de uma variável
ansible-config dump --only-changed  # opções do ansible.cfg em uso
ansible-doc <modulo>                # documentação de um módulo
```

## Ansible: execução

```bash
ansible-playbook site.yml --syntax-check       # valida a sintaxe
ansible-playbook site.yml --list-tasks         # lista as tarefas
ansible-playbook site.yml --check --diff -K    # simula e mostra as diferenças
ansible-playbook site.yml -K                   # (altera) aplica o playbook
ansible-playbook site.yml -K -vvv              # (altera) aplica com saída detalhada
```

A opção `-K` pede a senha do `sudo` antes de começar.

## Ansible: comandos avulsos

```bash
ansible all -m ansible.builtin.ping                              # testa a conexão
ansible all -m ansible.builtin.setup -a "filter=ansible_hostname"   # fatos de um host
ansible all -b -m ansible.builtin.command -a "md5sum /etc/munge/munge.key"   # consulta
```

## Pacotes e serviços

```bash
sudo apt update                                  # (altera) atualiza a lista de pacotes
sudo apt install -y <pacote>                     # (altera) instala um pacote
systemctl status <servico>                       # estado de um serviço
sudo systemctl restart <servico>                 # (altera) reinicia um serviço
systemctl list-units --type=service | grep slurm # serviços do Slurm
```

## Autenticação (munge)

```bash
munge -n | unmunge                              # testa a autenticação local
munge -n | ssh <host> unmunge                   # testa a autenticação entre máquinas
sudo ls -l /etc/munge/munge.key                 # dono e permissões da chave
```

## Estado do cluster (Slurm)

```bash
sinfo                               # partições e estados dos nós
sinfo -N -l                         # um nó por linha, com detalhes
scontrol show node <nome>           # recursos e motivo de estado de um nó
scontrol show job <numero>          # detalhes de um job
squeue                              # fila de jobs
```

## Enviar e controlar jobs

```bash
srun hostname                       # executa um comando de imediato
srun --gres=gpu:1 nvidia-smi -L     # executa com uma GPU alocada
sbatch <script>.sh                  # envia um script para a fila
sbatch --gres=gpu:1 --wrap="<comando>"   # envia um comando direto
scancel <numero>                    # cancela um job
sudo scontrol update nodename=<nome> state=resume   # (altera) devolve um nó ao serviço
```

## Histórico (accounting)

```bash
sacct -X --format=JobID,User,Partition,Elapsed,State   # jobs concluídos
sacctmgr show cluster                                  # clusters cadastrados
sacctmgr show user                                     # usuários cadastrados
sudo sacctmgr -i add cluster <nome>                    # (altera) cadastra um cluster
```

## Logs e diagnóstico

```bash
journalctl -u slurmctld -n 50 --no-pager          # últimas linhas de um serviço
journalctl -u slurmd -f                           # acompanha um serviço em tempo real
journalctl -u slurmctld --no-pager | grep -iE "error|fatal"   # filtra erros
sudo slurmd -D -vvv                               # executa o slurmd em primeiro plano
scontrol show config | grep -i logfile            # onde o Slurm grava logs
```

## Versionamento

```bash
git status                          # mudanças pendentes
git diff                            # o que mudou desde o último commit
git add <arquivos>                  # (altera o histórico local) prepara arquivos
git commit -m "<mensagem>"          # (altera o histórico local) registra a versão
git log --oneline                   # histórico de versões
```
