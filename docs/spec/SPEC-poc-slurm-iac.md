# SPEC: PoC de Mini-HPC com Slurm, GPU e Infraestrutura como Código (IaC)

**Status:** rascunho vivo
**Dono do projeto:** Anderson Paschoalon (TCC, FEEC/UNICAMP)
**Destinatário:** agente de IA que vai auxiliar no desenvolvimento
**Escopo deste documento:** fase de prova de conceito (PoC) em uma única máquina física com uma GPU NVIDIA, com expansão progressiva para múltiplos nós simulados e máquinas virtuais.

---

## 0. Como um agente deve usar esta spec

1. Leia as seções 1 a 4 antes de sugerir qualquer código. Elas definem o problema, as restrições e os princípios.
2. Antes de propor mudanças em arquivos, verifique a seção 8 (arquivos) e a seção 12 (correções já aplicadas). Não reintroduza os erros corrigidos.
3. Não invente valores de hardware. CPUs, memória, nome de host e modelo de GPU devem ser confirmados pelo usuário com `slurmd -C`, `hostname -s` e `nvidia-smi`.
4. Não altere a fonte da verdade (`group_vars/all.yml`) sem explicar o impacto nos templates.
5. Qualquer código novo deve ser idempotente e manter o padrão IaC da seção 3.
6. Quando faltar informação, pergunte. A seção 13 lista as lacunas conhecidas.
7. O usuário é desenvolvedor de software com experiência em Ansible, mas pouca experiência com infraestrutura de HPC e GPU. Explique o porquê das decisões, não só o comando.
8. O usuário tem aversão a decorar sequências de comandos. Prefira automação e scripts a instruções manuais.

---

## 1. Contexto do projeto

### 1.1 Motivação

O laboratório da FEEC não tem gerenciamento de recursos computacionais. O uso de GPUs é manual e informal. Isso leva a:
- GPUs antigas ociosas, pois não há fila nem alocação;
- filas informais e disputa entre pesquisadores;
- ausência de políticas justas de uso (fairshare).

Este projeto é um TCC cujo objetivo é construir uma prova de conceito de um pequeno sistema HPC, com gerenciador de jobs, políticas de alocação e infraestrutura reproduzível via IaC.

### 1.2 Escopo

**Dentro do escopo:**
- Gerenciador de jobs e recursos com Slurm (decisão de projeto, justificada por revisão bibliográfica).
- Reconhecimento de GPUs como recurso escalonável (GRES).
- Automação completa do provisionamento com Ansible.
- Demonstração de fairshare por simulação controlada (jobs sintéticos, sem usuários reais).
- Expansão progressiva: nós simulados, VMs, accounting.

**Fora do escopo:**
- Implantação em todo o laboratório.
- Virtualização com GPU passthrough.
- Kubernetes como camada de escalonamento.
- Pesquisa de satisfação de usuários.
- Medição de ociosidade antes da implantação (justificada pela literatura, não medida).

**Em aberto (decisão do autor, ainda não tomada):**
- Armazenamento em rede (NAS/NFS/Ceph). Está previsto como parte do mini-HPC, mas não faz parte deste documento até que a pesquisa correspondente seja concluída.
- Comparação Slurm vs. SGE. Slurm é o gerenciador adotado para a implementação. A justificativa vem da revisão bibliográfica.
- Treinamento distribuído heterogêneo. É uma etapa avançada e opcional.

### 1.3 Ambiente do autor

- Sistema operacional: Linux Mint 22 (base Ubuntu 24.04 "noble").
- Uma GPU NVIDIA física instalada na máquina. O modelo ainda não foi informado.
- Experiência prévia com Ansible e shell scripting. Experiência limitada com Slurm, GPU e HPC.
- Preferência explícita por IaC em vez de configuração manual.

---

## 2. Objetivos e critérios de aceite por fase

| Fase | Objetivo | Critério de aceite |
|---|---|---|
| **1. Nó único real** | Slurm controlador e nó de computação na mesma máquina, com a GPU física reconhecida como GRES | `sinfo` mostra o nó em estado `idle`; `sbatch --gres=gpu:1 --wrap="nvidia-smi"` executa e grava saída |
| **2. Nós simulados** | Vários `slurmd` no mesmo host, com GPUs virtuais, para testar filas, partições e lógica de escalonamento | `sinfo` lista todos os nós; jobs com `--gres=gpu:N` são alocados nos nós corretos |
| **3. Múltiplas VMs** | Topologia de rede real com VMs Ubuntu sem GPU, orquestradas pelo mesmo playbook | `sinfo` mostra nós em VMs distintas; munge autentica entre eles; playbook idempotente |
| **4. Accounting** | `slurmdbd` com MariaDB, para histórico de jobs | `sacct` retorna jobs executados; base para fairshare |

Cada fase deve ser alcançada apenas alterando o inventário e as variáveis, sem reescrever a automação. Esse é o critério de reuso que justifica a escolha de IaC.

---

## 3. Princípios de IaC que devem ser respeitados

1. **Fonte única da verdade.** Toda topologia (nós, CPUs, memória, GPUs, portas) vive em `group_vars/all.yml`. Nenhum valor de hardware é repetido em templates ou tarefas.
2. **Arquivos gerados não se editam à mão.** `slurm.conf`, `gres.conf` e `cgroup.conf` são gerados por templates Jinja2. Cabeçalhos dos templates dizem isso explicitamente.
3. **Idempotência.** Rodar `ansible-playbook site.yml` duas vezes deve resultar em `changed=0` na segunda execução (ou, no máximo, mudanças esperadas em serviços reiniciados).
4. **Versionamento desde o dia 1.** O projeto é um repositório git. Cada fase vira um commit (ou tag).
5. **Teste no mesmo código que vai para produção.** O playbook roda contra `localhost` na fase 1 e contra VMs nas fases seguintes. Só o inventário muda.
6. **Medições de desempenho só em hardware real.** Nós simulados servem para validar agendamento. Qualquer métrica de throughput ou tempo de treino obtida em nó simulado é inválida e deve ser marcada como tal.

---

## 4. Restrições técnicas conhecidas

- **GPU real:** só um nó pode ter `/dev/nvidia0`. Nós simulados não executam CUDA.
- **Controle de dispositivos:** `ConstrainDevices=yes` em `cgroup.conf` só isola GPUs reais. Em nós simulados, o isolamento não existe.
- **Hostname:** o nome do nó em `slurm.conf` precisa coincidir com `hostname -s` (ou ser tolerado via `SlurmdParameters=config_overrides` para divergências de hardware, não de nome).
- **Divergência de hardware:** `slurm.conf` declara CPUs e memória. Se forem maiores que as reais, o nó fica `down` ou `unk`. `SlurmdParameters=config_overrides` tolera divergências menores.
- **Versão do Slurm:** Ubuntu 24.04 entrega Slurm 23.11.x via `slurm-wlm`. Verifique a versão instalada com `slurmd -V` antes de assumir sintaxe de versões mais novas.
- **Spool compartilhado em nós simulados:** vários `slurmd` no mesmo host não podem compartilhar `SlurmdSpoolDir`. Cada nó simulado precisa do seu próprio diretório de spool (ver fase 2).
- **Mínimo de memória:** o nó real precisa ter `RealMemory` menor ou igual à memória física disponível. Use o valor de `slurmd -C`.

---

## 5. Pilha tecnológica mínima

| Componente | Função | Origem |
|---|---|---|
| Linux Mint 22 (Ubuntu 24.04) | Sistema operacional do host | Instalado |
| Driver NVIDIA | Acesso à GPU física | Instalado; `nvidia-smi` precisa responder |
| `slurm-wlm`, `slurm-client` | Controlador, daemon de nó e comandos do usuário | apt |
| `munge` | Autenticação entre daemons do Slurm | apt |
| `ansible` | Automação da configuração | apt |
| `git` | Versionamento da infraestrutura | apt |
| Multipass | VMs Ubuntu para a fase 3 | snap |
| MariaDB + `slurmdbd` | Accounting, fase 4 | apt |

Não usar nesta fase: Terraform, OpenTofu, Kubernetes, Docker, coleções externas do Ansible Galaxy. Essas ferramentas podem ser avaliadas depois, e a decisão deve ser registrada.

---

## 6. Topologia por fase

**Fase 1: um nó real**
```
Linux Mint (host)
├── munge
├── slurmctld   (controlador)
├── slurmd      (nó de computação: localhost, 1 GPU física /dev/nvidia0)
└── comandos: sbatch, srun, squeue, sinfo
```

**Fase 2: nós simulados no mesmo host**
```
Linux Mint (host, GPU física)
├── slurmctld
├── slurmd  <hostname>   GPU física   (porta 6818)
├── slurmd  vnode1       GPUs virtuais (porta 6819)
└── slurmd  vnode2       GPUs virtuais (porta 6820)
```

**Fase 3: VMs**
```
Host (Linux Mint, GPU física)
├── VM ctl    (controlador, sem GPU)
├── VM vnode1 (computação, sem GPU)
└── nó real   (host, com GPU física, opcional)
```

**Fase 4: accounting**
```
ctl ── slurmctld ──► slurmdbd ──► MariaDB
```

---

## 7. Estrutura de arquivos

```
slurm-lab/
├── ansible.cfg
├── inventory/
│   └── hosts.yml              # quais máquinas existem e como acessá-las
├── group_vars/
│   └── all.yml                # FONTE DA VERDADE: nós, CPUs, GPUs, portas
├── site.yml                   # playbook principal
└── roles/
    ├── base/
    │   └── tasks/main.yml     # pacotes e diretórios
    ├── munge/
    │   └── tasks/main.yml     # chave de autenticação
    └── slurm/
        ├── tasks/main.yml     # templates, serviços
        ├── handlers/main.yml  # reinício de serviços quando a configuração muda
        └── templates/
            ├── slurm.conf.j2
            ├── gres.conf.j2
            └── cgroup.conf.j2
```

Arquivos previstos para fases futuras (ainda não especificados): `roles/munge/tasks/distribute.yml` (fase 3), `roles/slurmdbd/` e `roles/mariadb/` (fase 4), `scripts/validate.sh` (validação pós-deploy).

---

## 8. Especificação dos arquivos

### 8.1 `ansible.cfg`

Configura o Ansible para este projeto: inventário padrão, detecção automática do Python e desativa arquivos de retry.

```ini
[defaults]
inventory = inventory/hosts.yml
interpreter_python = auto_silent
retry_files_enabled = False
```

### 8.2 `inventory/hosts.yml` (fase 1: tudo no próprio host)

Define os grupos `controller` e `compute`. Na fase 1 o host é ao mesmo tempo controlador e nó de computação. `ansible_connection: local` evita SSH.

```yaml
all:
  children:
    controller:
      hosts:
        localhost:
          ansible_connection: local
    compute:
      hosts:
        localhost:
          ansible_connection: local
```

### 8.3 `group_vars/all.yml`

Fonte única da verdade. Cada entrada de `slurm_nodes` vira um `NodeName` no `slurm.conf` e uma linha no `gres.conf`.

Observação: `controller_host` usa `ansible_hostname`, e não `localhost`. O `slurmctld` compara o nome configurado com o hostname real do host, então `localhost` causa falha de inicialização.

```yaml
cluster_name: mini-hpc
controller_host: "{{ ansible_hostname }}"

# Cada entrada vira um NodeName no slurm.conf.
# Nó real: 1 GPU física (gpu_device). Nó simulado: GPUs virtuais (gpu_count).
slurm_nodes:
  - name: "{{ ansible_hostname }}"   # deve bater com `hostname -s`
    addr: 127.0.0.1
    port: 6818
    cpus: 8                          # ajuste com o resultado de `slurmd -C`
    real_memory: 8000                # em MB, também de `slurmd -C`
    gpu_count: 1
    gpu_device: /dev/nvidia0         # só o nó real tem device file

  # Fase 2: nós simulados (descomentar depois)
  # - name: vnode1
  #   addr: 127.0.0.1
  #   port: 6819
  #   cpus: 2
  #   real_memory: 1000
  #   gpu_count: 2                   # GPUs virtuais, sem device file
```

### 8.4 `site.yml`

Playbook principal. Aplica as três roles em todos os hosts do inventário, com escalonamento de privilégio.

```yaml
- name: PoC Slurm mínimo
  hosts: all
  become: true
  roles:
    - base
    - munge
    - slurm
```

### 8.5 `roles/base/tasks/main.yml`

Instala os pacotes e cria os diretórios de estado. A criação de diretórios vem depois da instalação, pois o usuário `slurm` só existe após o pacote ser instalado.

```yaml
- name: Instalar pacotes do Slurm e munge
  ansible.builtin.apt:
    name:
      - slurm-wlm
      - slurm-client
      - munge
    state: present
    update_cache: true

- name: Criar diretórios de estado do Slurm
  ansible.builtin.file:
    path: "{{ item }}"
    state: directory
    owner: slurm
    group: slurm
    mode: "0755"
  loop:
    - /var/spool/slurmctld
    - /var/spool/slurmd
```

### 8.6 `roles/munge/tasks/main.yml`

Garante que o serviço munge está rodando. O pacote munge gera a chave `/etc/munge/munge.key` na instalação. Na fase 3, esta role passa a distribuir a mesma chave para todos os nós.

```yaml
- name: Garantir que o munge está rodando
  ansible.builtin.systemd:
    name: munge
    state: started
    enabled: true
```

### 8.7 `roles/slurm/tasks/main.yml`

Renderiza os três arquivos de configuração e inicia os serviços conforme o papel do host. Cada template notifica o handler de reinício.

Observação: os handlers são notificados de forma uniforme, e cada um é protegido por `when`, para que um host só reinicie o serviço que ele executa.

```yaml
- name: Renderizar slurm.conf
  ansible.builtin.template:
    src: slurm.conf.j2
    dest: /etc/slurm/slurm.conf
    mode: "0644"
  notify:
    - restart slurmctld
    - restart slurmd

- name: Renderizar gres.conf
  ansible.builtin.template:
    src: gres.conf.j2
    dest: /etc/slurm/gres.conf
    mode: "0644"
  notify:
    - restart slurmctld
    - restart slurmd

- name: Renderizar cgroup.conf
  ansible.builtin.template:
    src: cgroup.conf.j2
    dest: /etc/slurm/cgroup.conf
    mode: "0644"
  notify:
    - restart slurmctld
    - restart slurmd

- name: Habilitar e iniciar slurmctld
  ansible.builtin.systemd:
    name: slurmctld
    state: started
    enabled: true
  when: "'controller' in group_names"

- name: Habilitar e iniciar slurmd
  ansible.builtin.systemd:
    name: slurmd
    state: started
    enabled: true
  when: "'compute' in group_names"
```

### 8.8 `roles/slurm/handlers/main.yml`

Reinicia os serviços somente quando a configuração muda. Cada handler verifica o papel do host.

Observação: a versão anterior deste handler usava uma expressão de `loop` com concatenação de listas Jinja2 em uma só string, o que não é válido. Esta versão substitui por dois handlers simples.

```yaml
- name: restart slurmctld
  ansible.builtin.systemd:
    name: slurmctld
    state: restarted
  when: "'controller' in group_names"

- name: restart slurmd
  ansible.builtin.systemd:
    name: slurmd
    state: restarted
  when: "'compute' in group_names"
```

### 8.9 `roles/slurm/templates/slurm.conf.j2`

Gera o arquivo principal do Slurm a partir de `group_vars/all.yml`. Define plugins de cgroup, agendador com backfill, seleção de recursos com GRES, accounting desativado (fase 4 ativa), a lista de nós e a partição padrão.

```jinja
# Gerado pelo Ansible. Não editar à mão.
ClusterName={{ cluster_name }}
SlurmctldHost={{ controller_host }}
SlurmUser=slurm
StateSaveLocation=/var/spool/slurmctld
SlurmdSpoolDir=/var/spool/slurmd
SlurmctldPidFile=/run/slurmctld.pid
SlurmdPidFile=/run/slurmd.pid

ProctrackType=proctrack/cgroup
TaskPlugin=task/cgroup,task/affinity
SchedulerType=sched/backfill
SelectType=select/cons_tres
SelectTypeParameters=CR_Core
GresTypes=gpu
ReturnToService=2
SlurmdParameters=config_overrides

AccountingStorageType=accounting_storage/none
JobAcctGatherType=jobacct_gather/none

{% for node in slurm_nodes %}
NodeName={{ node.name }} NodeAddr={{ node.addr }} Port={{ node.port }} CPUs={{ node.cpus }} RealMemory={{ node.real_memory }} Gres=gpu:{{ node.gpu_count }} State=UNKNOWN
{% endfor %}

PartitionName=debug Nodes={{ slurm_nodes | map(attribute='name') | join(',') }} Default=YES MaxTime=INFINITE State=UP
```

### 8.10 `roles/slurm/templates/gres.conf.j2`

Declara as GPUs de cada nó. O nó real usa `File=` apontando para o device. Nós simulados usam `Count=`, sem device.

```jinja
# Gerado pelo Ansible. Não editar à mão.
{% for node in slurm_nodes %}
NodeName={{ node.name }} Name=gpu {% if node.gpu_device is defined %}File={{ node.gpu_device }}{% else %}Count={{ node.gpu_count }}{% endif %}
{% endfor %}
```

### 8.11 `roles/slurm/templates/cgroup.conf.j2`

Configura o isolamento por cgroup. `ConstrainDevices=yes` faz o job enxergar apenas as GPUs que recebeu.

```jinja
# Gerado pelo Ansible. Não editar à mão.
CgroupPlugin=autodetect
ConstrainCores=yes
ConstrainRAMSpace=yes
ConstrainDevices=yes
```

---

## 9. Sequência de execução (fase 1)

```bash
# 0. Pré-requisitos
sudo apt install ansible git
nvidia-smi                       # precisa responder antes de tudo
hostname -s                      # nome do nó real, usado em slurm_nodes
slurmd -C                        # após instalar slurm-wlm; CPUs e memória reais

# 1. Versionar desde o início
cd slurm-lab && git init && git add . && git commit -m "PoC Slurm: fase 1"

# 2. Validar sintaxe e simular
ansible-playbook site.yml --syntax-check
ansible-playbook site.yml --check -K

# 3. Aplicar
ansible-playbook site.yml -K

# 4. Idempotência: segunda execução deve mostrar changed=0 (ou quase)
ansible-playbook site.yml -K

# 5. Validar o cluster
sinfo
scontrol show node
srun --gres=gpu:1 nvidia-smi
sbatch --gres=gpu:1 --wrap="hostname; nvidia-smi"
squeue
```

### 9.1 Checklist de aceite da fase 1

- [ ] `nvidia-smi` responde no host.
- [ ] `slurmd -C` retorna CPUs e memória, e os valores foram copiados para `group_vars/all.yml`.
- [ ] `hostname -s` coincide com `slurm_nodes[0].name`.
- [ ] `ansible-playbook site.yml --syntax-check` passa.
- [ ] `ansible-playbook site.yml -K` termina sem erro.
- [ ] Segunda execução tem `changed=0` ou mudanças explicáveis.
- [ ] `sinfo` mostra o nó em `idle` (não `down`, `drain` ou `unk`).
- [ ] `srun --gres=gpu:1 nvidia-smi` mostra a GPU dentro do job.

---

## 10. Fases seguintes

### 10.1 Fase 2: nós simulados

Adicionar entradas em `slurm_nodes` com portas distintas. Cada `slurmd` simulado precisa ser iniciado com `-N <nome>` e precisa de um diretório de spool próprio, pois `SlurmdSpoolDir` não pode ser compartilhado entre instâncias.

Requisito para o playbook: criar uma unidade systemd por nó simulado (por exemplo, `slurmd-<nome>.service`) com o parâmetro `-N`, e um diretório de spool por nó. Esta parte ainda não está especificada em código e deve ser projetada com o agente antes de implementar.

Limitação: jobs em nós simulados não executam CUDA. Testes de fila e partição são válidos; testes de desempenho não.

### 10.2 Fase 3: máquinas virtuais com Multipass

Criar VMs `ctl` e `vnode1` sem GPU (`multipass launch`). Trocar o inventário para hosts reais, definir `controller_host: ctl`, preencher `/etc/hosts` no papel `base`, e fazer a role `munge` copiar a chave do controlador para os demais nós.

Mecanismo sugerido para distribuir a chave: ler `/etc/munge/munge.key` no controlador com o módulo `ansible.builtin.slurp`, e gravá-la nos outros nós com `ansible.builtin.copy`, com permissões `0400` e dono `munge`.

### 10.3 Fase 4: accounting

Adicionar `slurmdbd` e MariaDB. Trocar `AccountingStorageType` para `accounting_storage/slurmdbd`, e ativar `JobAcctGatherType` com um plugin adequado. Esta fase é pré-requisito para `sacct` e para a demonstração de fairshare.

---

## 11. Riscos e troubleshooting

| Sintoma | Causa provável | Ação |
|---|---|---|
| `sinfo` mostra nó `down` ou `unk` | CPUs ou memória declaradas maiores que as reais | Ajustar `cpus` e `real_memory` com `slurmd -C` |
| `slurmctld` não inicia | `SlurmctldHost` diferente do hostname | Verificar `hostname -s` e `controller_host` |
| Nó com nome diferente no `sinfo` | `slurm_nodes[0].name` não bate com o hostname | Corrigir o nome para `ansible_hostname` |
| `srun --gres=gpu:1` falha | `gres.conf` não encontra `/dev/nvidia0` ou driver não carregado | Verificar `nvidia-smi` e o caminho do device |
| Jobs executam, mas `nvidia-smi` não mostra GPU | `ConstrainDevices` ou `gres.conf` mal configurado | Verificar `cgroup.conf` e `scontrol show job` |
| `munge` falha entre nós | Chaves diferentes | Comparar `md5sum /etc/munge/munge.key` nos nós |
| Playbook não é idempotente | Tarefa que altera estado sem `creates`, `when` ou módulo idempotente | Revisar tarefas com `shell` ou `command` |
| Driver NVIDIA não carrega no Mint | Secure Boot ativo bloqueando módulo não assinado | Desativar Secure Boot ou assinar o módulo; decisão do autor |

---

## 12. Correções aplicadas em relação ao plano anterior

Esta seção registra o que foi corrigido para que o agente não reintroduza os erros.

1. **Handler inválido.** A versão anterior de `roles/slurm/handlers/main.yml` tinha uma expressão de `loop` com concatenação de listas Jinja2 em uma string, o que não é sintaxe válida. Substituído por dois handlers independentes com `when`.
2. **`controller_host: localhost`.** Substituído por `"{{ ansible_hostname }}"`. Com `localhost`, o `slurmctld` não consegue confirmar que é o controlador configurado.
3. **Reinício de serviço.** Os templates agora notificam ambos os handlers, e cada handler é protegido por `when`.
4. **Fase 2 apresentada como "o playbook passa a criar unidades systemd".** Isso é um requisito, não código. Está registrado como pendência na seção 10.1, com a ressalva sobre spool compartilhado.

---

## 13. Lacunas abertas e perguntas ao autor

Um agente deve perguntar ao autor antes de assumir estes pontos:

1. **Modelo da GPU** e versão do driver NVIDIA (`nvidia-smi`).
2. **Valores de hardware** do host: `slurmd -C` (CPUs, memória).
3. **Secure Boot** está ativo? Afeta o carregamento do driver NVIDIA.
4. **Versão do Slurm** instalada (`slurmd -V`). A sintaxe deste documento assume 23.11.x.
5. **Autodetecção de GPU:** `AutoDetect=nvml` no `gres.conf` reduz a declaração manual de dispositivos, mas depende de o pacote do Slurm ter sido compilado com NVML. Verificar antes de adotar.
6. **Fairshare:** qual política de fairshare será demonstrada e quais métricas serão coletadas (depende da fase 4).
7. **Armazenamento:** a decisão sobre NAS ainda não foi tomada. Não incluir na implementação até que o autor decida.

---

## 14. Referências técnicas (para consulta do agente)

- Documentação do Slurm: `slurm.conf`, `gres.conf`, `cgroup.conf`, `slurmd`, `slurmctld`, `slurmdbd`, `sbatch`, `srun`, `sinfo`, `sacct`.
- Documentação do Ansible: `apt`, `file`, `template`, `systemd`, `slurp`, `copy`, `handlers`, `when`.
- Documentação do Multipass: `launch`, `exec`, `transfer`.
- Documentação do munge: geração e permissões da `munge.key`.

Antes de citar comandos ou sintaxe específica, confirme a versão instalada, pois a documentação muda entre versões.
