# Parte 1: Introdução

Esta parte apresenta, uma por vez, as tecnologias que compõem um cluster pequeno automatizado. Cada item traz a definição, o problema que resolve e um exemplo curto. Os exemplos ilustram o conceito. As partes seguintes usam os mesmos conceitos na prática.

---

## 1.1 O que é um cluster de computação e por que usar um

Um **cluster** é um conjunto de máquinas conectadas em rede que funcionam como um sistema único para os usuários. Em vez de cada pessoa usar uma máquina quando ela está livre, os usuários enviam **tarefas** (chamadas *jobs*) para uma fila, e um programa decide em qual máquina e com quais recursos cada tarefa roda.

Quando o cluster é usado para cálculo intensivo, como treino de modelos de aprendizado de máquina, a área se chama **HPC** (*High Performance Computing*, computação de alto desempenho). Os problemas que um cluster resolve são de três tipos:

- **Ociosidade:** equipamentos caros ficam parados enquanto outros esperam por eles.
- **Falta de ordem:** sem fila, quem chega primeiro ocupa o recurso, e os demais esperam sem previsão.
- **Falta de reprodutibilidade:** a configuração de cada máquina é feita à mão, e ninguém lembra exatamente o que foi feito.

Os dois primeiros problemas são tratados pelo gerenciador de recursos, o Slurm. O terceiro é tratado pela Infraestrutura como Código, com o Ansible.

---

## 1.2 Sistema operacional Linux e o gerenciador de pacotes apt

**Linux** é um sistema operacional. **Ubuntu** é uma distribuição Linux, ou seja, uma versão do Linux com um conjunto de programas e um modo próprio de instalar software. Outras distribuições, como o **Linux Mint**, são derivadas do Ubuntu e usam os mesmos pacotes.

Para descobrir qual distribuição e versão está instalada:

```bash
cat /etc/os-release
```

Em sistemas Debian e Ubuntu, os programas são instalados pelo **apt**, o gerenciador de pacotes, a partir de repositórios oficiais:

```bash
sudo apt update                 # atualiza a lista de pacotes disponíveis
sudo apt install slurm-wlm      # instala um pacote
apt policy slurm-wlm            # mostra a versão disponível e a instalada
```

O prefixo `sudo` concede privilégio de administrador. Instalar serviços e editar arquivos em `/etc/` exige esse privilégio, e isso aparece com frequência ao longo da apostila.

---

## 1.3 GPU, driver e ferramentas de estado

A **GPU** (*Graphics Processing Unit*) é um processador com muitos núcleos pequenos, adequado para executar muitas operações iguais em paralelo. Esse tipo de cálculo é a base do treino de redes neurais, por isso as GPUs são recursos valiosos em um cluster.

O sistema operacional não conversa diretamente com a placa. Quem faz essa ponte é o **driver**, um módulo do kernel Linux. Quando o driver está ativo, a placa aparece como um dispositivo de arquivo, como `/dev/nvidia0` no caso das placas NVIDIA.

Para consultar o estado de uma placa NVIDIA, use a ferramenta de linha de comando:

```bash
nvidia-smi
```

A saída mostra o modelo da placa, a versão do driver, a versão de CUDA suportada (CUDA é a plataforma de programação usada pelos programas que rodam na GPU) e a memória de vídeo.

Os rótulos da saída mudam entre versões do driver. Guias antigos mostram `Driver Version` e `CUDA Version`, e versões recentes usam outros nomes, como `KMD Version` e `CUDA UMD Version`. O conceito é o mesmo. Não decore os rótulos: leia a saída e procure o conceito.

Para o nome completo do modelo, sem truncamento:

```bash
nvidia-smi -L
```

Para placas de outros fabricantes, as ferramentas equivalentes são `rocm-smi` (AMD) e `intel_gpu_top` (Intel). A lógica de verificação é a mesma.

---

## 1.4 O que é Infraestrutura como Código (IaC)

Infraestrutura como Código é a prática de descrever a configuração de máquinas em arquivos de texto, em vez de configurá-las à mão. Esses arquivos podem ser executados novamente e guardados em um sistema de controle de versão, que registra o que mudou, quando e por quê.

Compare duas formas de instalar um serviço:

**Forma manual (difícil de repetir):**
```bash
sudo apt install munge
sudo systemctl enable --now munge
sudo nano /etc/slurm/slurm.conf   # e edita à mão, lembrando de cada linha
```

**Forma IaC (descrita em arquivo):**
```yaml
- name: Instalar munge
  ansible.builtin.apt:
    name: munge
    state: present

- name: Iniciar munge
  ansible.builtin.systemd:
    name: munge
    state: started
    enabled: true
```

A segunda forma descreve **o que deve existir**, e não **como chegar lá passo a passo**. Se o serviço for removido e o arquivo for executado de novo, o resultado é o mesmo. Essa é a principal vantagem.

Duas propriedades são centrais:

- **Idempotência:** aplicar a mesma configuração várias vezes produz o mesmo estado final.
- **Fonte única da verdade:** a topologia (quantas máquinas, quantas GPUs, quais portas) fica em um lugar só, e os demais arquivos são gerados a partir dele.

> **Recomendação:** mantenha a pasta do projeto construído nesta apostila sob controle de versão, com uma ferramenta como o Git, e registre uma versão a cada mudança relevante. Se algo quebrar, é possível voltar à configuração que funcionava. O uso do Git não faz parte desta apostila, e nenhum passo depende dele.

Existem várias ferramentas de IaC. Algumas são mais adequadas para **configurar máquinas que já existem** (como o Ansible, o Puppet, o Chef e o SaltStack). Outras são mais adequadas para **criar infraestrutura em nuvem**, como o Terraform e o OpenTofu. Esta apostila usa o Ansible, que atende ao caso de máquinas físicas ou virtuais já disponíveis.

---

## 1.5 O que é Ansible

O **Ansible** executa tarefas de configuração em máquinas a partir de arquivos YAML. Ele não exige programa instalado nas máquinas gerenciadas: usa SSH para acessá-las, ou execução local quando o alvo é a própria máquina.

Os quatro conceitos centrais:

| Conceito | O que é | Exemplo de arquivo |
|---|---|---|
| **Inventário** | Lista das máquinas e seus grupos | `inventory/hosts.yml` |
| **Variáveis** | Valores usados pelas tarefas e pelos templates | `group_vars/all.yml` e variáveis de host no inventário |
| **Playbook** | Lista ordenada de roles ou tarefas, com os hosts-alvo | `site.yml` |
| **Role** | Pasta com tarefas, handlers e templates de um assunto | `roles/slurm/` |

Teste de conexão com o modo *ad hoc* (um comando único, sem arquivo de playbook). O padrão `all` aponta para todos os hosts do inventário:

```bash
ansible all -m ping
```

Se responder `pong`, o Ansible consegue operar na máquina. Aqui, `ping` é um módulo do Ansible, não o comando de rede.

Inventário mínimo para executar tudo na própria máquina. O nome do host é o nome curto da máquina, que `hostname -s` retorna:

```yaml
all:
  children:
    controller:
      hosts:
        <hostname>:
          ansible_connection: local
```

`ansible_connection: local` diz ao Ansible para executar na própria máquina, sem SSH. Isso permite testar a automação completa em um único computador antes de aplicá-la a outras máquinas.

---

## 1.6 O que são YAML e Jinja2

### YAML

**YAML** é um formato de texto para dados estruturados. A regra mais importante é a **indentação com espaços**. Tabulações não são permitidas.

```yaml
cluster_name: mini-cluster      # chave: valor
nodes:                          # lista (itens começam com traço)
  - name: node01
    cpus: 8
    gpu_count: 1
```

Os traços (`-`) indicam itens de lista. A indentação indica pertencimento: `name`, `cpus` e `gpu_count` pertencem ao item da lista.

### Jinja2

**Jinja2** é uma linguagem de templates. Um template é um texto com espaços marcados para valores variáveis. O Ansible usa Jinja2 para gerar arquivos de configuração. Há dois tipos de marcação:

- `{{ variavel }}`: insere um valor.
- `{% ... %}`: controla o fluxo, com laços (`for`) e condicionais (`if`).

```jinja
{% for node in nodes %}
NodeName={{ node.name }} CPUs={{ node.cpus }}
{% endfor %}
```

Se a lista `nodes` tiver dois itens, o arquivo gerado terá duas linhas `NodeName=...`. Os nós são declarados uma vez, e o template produz quantas linhas forem necessárias. É esse mecanismo que permite que a configuração cresça sem ser reescrita.

---

## 1.7 O que é Slurm

O **Slurm** (*Slurm Workload Manager*) é um gerenciador de recursos e escalonador de jobs de código aberto, muito usado em supercomputadores e clusters acadêmicos. Ele faz três coisas:

1. **Recebe** jobs dos usuários.
2. **Decide** quando e onde cada job roda, respeitando os recursos pedidos (CPUs, memória, GPUs) e as políticas configuradas.
3. **Executa** o job no nó escolhido e registra o resultado.

Os componentes principais, detalhados na Parte 5:

| Componente | Papel |
|---|---|
| `slurmctld` | Controlador central. Mantém a fila e decide as alocações. |
| `slurmd` | Daemon de cada nó de computação. Executa os jobs e informa os recursos do nó. |
| `slurmdbd` | Serviço de histórico (accounting). Registra o que rodou, quem rodou e por quanto tempo. |

Comandos que o usuário utiliza:

```bash
sinfo                        # mostra os nós e seus estados
squeue                       # mostra a fila de jobs
sbatch treino.sh             # envia um script como job, em segundo plano
srun --gres=gpu:1 nvidia-smi # executa um comando diretamente, com GPU alocada
scancel 1234                 # cancela o job de número 1234
```

Um script de job (`sbatch`) é um arquivo shell com diretivas `#SBATCH` no início:

```bash
#!/bin/bash
#SBATCH --job-name=teste-gpu
#SBATCH --gres=gpu:1
#SBATCH --output=saida_%j.log

hostname
nvidia-smi
```

- `--gres=gpu:1` solicita uma GPU.
- `--output=saida_%j.log` grava a saída em arquivo. `%j` é substituído pelo número do job.

Envio e acompanhamento:

```bash
sbatch teste-gpu.sh          # Submitted batch job 1234
squeue                       # mostra o job na fila ou em execução
cat saida_1234.log           # lê o resultado quando o job termina
```

Slurm é uma entre várias alternativas para gerenciar filas de jobs. Outras opções conhecidas incluem o Open Grid Scheduler (continuação de código aberto do Sun Grid Engine), o PBS/Torque e o LSF, além de soluções baseadas em Kubernetes. A escolha depende do tipo de carga, do suporte a GPUs e da maturidade da comunidade.

---

## 1.8 O que é munge

Os componentes do Slurm precisam confiar uns nos outros. Quando o `slurmctld` envia um job ao `slurmd`, o `slurmd` precisa ter certeza de que a mensagem veio de um participante legítimo. Essa autenticação é feita pelo **munge** (*MUNGE Uid 'N' Gid Emporium*).

Funcionamento, em termos simples:

- Todas as máquinas do cluster compartilham a **mesma chave**, guardada em `/etc/munge/munge.key`.
- O munge usa essa chave para assinar pequenas credenciais trocadas pelos programas.
- Um programa só é aceito pelo outro se a credencial for válida.

Teste isolado, sem o Slurm:

```bash
munge -n | unmunge
```

Saída esperada (resumida):

```
STATUS:          Success (0)
ENCODE_HOST:     nome-da-maquina
UID:             root
```

`munge -n` cria uma credencial e `unmunge` a valida. Se aparecer `Success`, a autenticação local funciona. O campo `UID` mostra o usuário que executou o comando: `root` no exemplo, ou o seu próprio usuário quando o comando é executado sem `sudo`.

Quando há várias máquinas, todas precisam ter **exatamente a mesma chave**. Para comparar:

```bash
sudo md5sum /etc/munge/munge.key
```

Valores diferentes significam que os nós não se autenticam. É um dos erros mais comuns em clusters.

---

## 1.9 O que são GRES e cgroups

### GRES

Por padrão, o Slurm conhece CPUs e memória. Para recursos adicionais, como GPUs, é preciso declarar um **GRES** (*Generic RESource*), um recurso genérico com nome livre. Neste tutorial, o recurso é chamado `gpu`.

A declaração acontece em dois arquivos:

1. Em `slurm.conf`, o tipo de recurso é registrado para o cluster inteiro com `GresTypes`, e cada nó informa quantas unidades possui com `Gres`:
```
GresTypes=gpu
NodeName=node01 ... Gres=gpu:1
```

A linha `GresTypes` vem antes das linhas de nó. Sem ela, o Slurm não reconhece o nome `gpu`, e a linha `NodeName` com `Gres=gpu:1` é rejeitada.

2. Em `gres.conf`, o dispositivo físico é apontado:
```
NodeName=node01 Name=gpu File=/dev/nvidia0
```

Com isso, `--gres=gpu:1` passa a ser uma requisição válida no job.

### cgroups

**cgroups** (*control groups*) é um recurso do kernel Linux que limita e isola o uso de recursos por processo. O Slurm usa cgroups para que cada job veja apenas os recursos que recebeu. Com `ConstrainDevices=yes`, por exemplo, um job que pediu uma GPU não enxerga as outras.

Configuração correspondente, em `cgroup.conf`:
```
CgroupPlugin=autodetect
ConstrainCores=yes
ConstrainRAMSpace=yes
ConstrainDevices=yes
```

Sem cgroups, um job com problema pode consumir a memória de todos os outros. Com cgroups, ele fica confinado aos seus recursos.

---

## 1.10 O que é Multipass

**Multipass** é uma ferramenta da Canonical (a empresa que mantém o Ubuntu) para criar máquinas virtuais Ubuntu rapidamente. Uma máquina virtual é um computador simulado dentro de outro computador.

Ela é útil para simular várias máquinas em rede sem precisar de hardware adicional:

```bash
multipass launch --name ctl --cpus 2 --memory 2G      # máquina controladora
multipass launch --name node01 --cpus 2 --memory 2G   # máquina de computação
multipass list                                        # mostra as VMs e seus IPs
multipass shell ctl                                   # abre um terminal dentro da VM
```

Máquinas virtuais comuns não têm acesso a GPU física. Elas servem para testar a orquestração e a comunicação entre nós. Testes de desempenho com GPU precisam ser feitos em máquinas com a GPU real.

---

## 1.11 O que são MariaDB e slurmdbd

**MariaDB** é um banco de dados relacional, derivado do MySQL, com licença livre. Ele armazena dados em tabelas.

**slurmdbd** é o serviço do Slurm que grava o histórico de jobs nesse banco. Comandos de consulta, como `sacct`, leem os dados por meio do slurmdbd.

Fluxo com accounting ativo:

```
sbatch → slurmctld → slurmd (executa o job)
                  ↓
              slurmdbd → MariaDB (guarda o histórico)
                  ↑
           sacct (consulta)
```

Exemplo de consulta:

```bash
sacct -X --format=JobID,User,Partition,Elapsed,State
```

A consulta mostra, para cada job, quem o enviou, em qual partição, quanto tempo levou e em que estado terminou. Esses dados são a base para analisar o uso do cluster e para políticas de justiça entre usuários (fairshare).

Sem accounting, `sacct` não tem o que mostrar.

---

## 1.12 O que é NAS e o protocolo NFS

**NAS** (*Network Attached Storage*, armazenamento conectado à rede) é um servidor de arquivos acessado pela rede. Em um cluster, ele permite que todas as máquinas leiam os mesmos dados, sem copiá-los para cada uma.

No Linux, o protocolo mais comum para isso é o **NFS** (*Network File System*). Uma pasta remota é montada em um caminho local:

```bash
sudo mount -t nfs servidor:/dados /mnt/datasets
ls /mnt/datasets        # os arquivos aparecem como se fossem locais
```

A versão do protocolo é negociada entre cliente e servidor, e pode ser fixada com a opção `vers=` do comando `mount`, conforme a configuração do servidor. Para que a montagem sobreviva a uma reinicialização, ela é registrada em `/etc/fstab`, ou gerenciada pela automação. Do ponto de vista de um job, o caminho `/mnt/datasets` é uma pasta comum.

Um NAS é uma escolha de armazenamento, não um requisito do Slurm. Ele é útil quando vários nós precisam dos mesmos dados. A escolha da solução (NFS, Ceph, outras) depende do tamanho do cluster, da rede e do tipo de carga.

---

## 1.13 Como as peças se encaixam

Fluxo de uma mudança na configuração:

```
Você edita o inventário (por exemplo, adiciona uma máquina)
        │
        ▼
ansible-playbook site.yml
        │
        ├── role base:    instala slurm-wlm e munge
        ├── role munge:   garante o serviço munge em execução
        └── role slurm:   gera slurm.conf, gres.conf e cgroup.conf
                          a partir dos templates Jinja2
                          reinicia slurmctld/slurmd se algo mudou
        │
        ▼
Slurm pronto: sinfo mostra o nó, sbatch executa o job na GPU
```

Você não edita `slurm.conf` diretamente. Você altera a fonte (o inventário ou `group_vars/all.yml`), e o Ansible regenera o arquivo. As próximas partes detalham cada etapa desse fluxo.

---

## Próximo passo

A **Parte 2** começa pelo ambiente: confirmar que a GPU responde (se houver) e levantar os dados da máquina. Nada é instalado antes dessa verificação.