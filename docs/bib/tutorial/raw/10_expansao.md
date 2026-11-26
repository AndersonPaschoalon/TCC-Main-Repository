# Parte 10: Expansão

**Objetivo desta parte:** levar o cluster além de uma máquina: declarar nós virtuais no mesmo host, distribuir a configuração de autenticação entre várias máquinas e ativar o histórico de jobs.

**Pré-requisito:** Partes 3 a 9 concluídas. O cluster de uma máquina valida com `sinfo` e com um job de `srun` e de `sbatch`. A topologia vem do inventário, como descrito na Parte 3 (abordagem B).

**Esta parte altera o sistema e pode envolver mais de uma máquina.** Use a simulação com `--check --diff` antes de cada execução. Cada seção pode ser aplicada de forma independente, nesta ordem: 10.1 não depende de outras máquinas, 10.2 exige pelo menos duas, e 10.3 pode ser feito a qualquer momento depois da Parte 9.

---

## 10.1 Nós simulados no mesmo host e o diretório de spool

Às vezes é útil ter mais nós do que máquinas. Por exemplo, para testar filas, partições e a lógica de reserva de recursos sem comprar hardware. Um **nó simulado** (ou **nó virtual**) é um processo `slurmd` adicional, rodando no mesmo host, que se apresenta ao controlador como se fosse uma máquina separada.

Um nó simulado tem limites que precisam ser entendidos antes do uso:

- **Não tem hardware próprio.** As GPUs declaradas com `Count` são unidades reservadas, não dispositivos reais. Programas CUDA não rodam nesses nós.
- **Não isola recursos reais.** O isolamento por cgroups (Parte 6) funciona apenas para dispositivos que existem. Dois nós simulados no mesmo host compartilham a memória e o processador reais da máquina.
- **Serve para testar o escalonador.** O uso correto é verificar filas, partições, pedidos de recursos e comportamento de estados. Medições de desempenho feitas nesses nós não são válidas.

### Declarando os nós virtuais

Os nós virtuais pertencem ao host que os executa. Por isso, a lista deles fica como variável do host, no inventário:

```yaml
    compute:
      hosts:
        <hostname>:
          ansible_connection: local
          cpus: 8
          real_memory: 7600
          gpu_count: 1
          gpu_device: /dev/nvidia0
          virtual_nodes:
            - name: vnode1
              port: 6819
              cpus: 2
              real_memory: 1500
              gpu_count: 2
            - name: vnode2
              port: 6820
              cpus: 2
              real_memory: 1500
              gpu_count: 0
```

Cada item descreve um nó simulado com nome, porta, CPUs, memória e GPUs. As portas precisam ser diferentes entre si e diferentes da porta do nó real, que vem de `slurmd_port`. A soma de memória dos nós simulados não deve passar da memória física da máquina. O Slurm não verifica isso, e o resultado seria lentidão e falhas por falta de memória.

### Atualizando o template de `slurm.conf`

O laço de nós passa a ter dois níveis: primeiro o nó real de cada host, depois os virtuais desse host. A lista de partição precisa incluir os dois tipos. O bloco abaixo substitui os trechos de nós e de partição no `slurm.conf.j2` da Parte 7:

```jinja
{% for h in groups['compute'] %}
NodeName={{ h }} NodeAddr={{ hostvars[h].node_addr | default('127.0.0.1') }} Port={{ slurmd_port }} CPUs={{ hostvars[h].cpus }} RealMemory={{ hostvars[h].real_memory }}{% if hostvars[h].gpu_count | default(0) > 0 %} Gres=gpu:{{ hostvars[h].gpu_count }}{% endif %} State=UNKNOWN
{% for v in hostvars[h].virtual_nodes | default([]) %}
NodeName={{ v.name }} NodeAddr=127.0.0.1 Port={{ v.port }} CPUs={{ v.cpus }} RealMemory={{ v.real_memory }}{% if v.gpu_count | default(0) > 0 %} Gres=gpu:{{ v.gpu_count }}{% endif %} State=UNKNOWN
{% endfor %}
{% endfor %}

{% set ns = namespace(nomes=[]) %}
{% for h in groups['compute'] %}
{% set ns.nomes = ns.nomes + [h] %}
{% for v in hostvars[h].virtual_nodes | default([]) %}
{% set ns.nomes = ns.nomes + [v.name] %}
{% endfor %}
{% endfor %}
PartitionName=debug Nodes={{ ns.nomes | join(',') }} Default=YES MaxTime=INFINITE State=UP
```

Pontos a entender:

- **O laço interno** percorre `virtual_nodes` do host atual. O filtro `default([])` garante que um host sem nós virtuais produza zero linhas, sem erro.
- **`NodeAddr=127.0.0.1`** é fixo, porque os nós simulados rodam na própria máquina.
- **`namespace`** é um recurso do Jinja2 que permite alterar uma variável dentro de um laço. Sem ele, cada `set` dentro do `for` criaria uma variável local que some ao fim do laço. Ele é o único jeito de montar a lista de nomes em duas etapas.

### Atualizando o template de `gres.conf`

Os nós virtuais com GPUs recebem `Count`, porque não têm dispositivo próprio. O nó real continua recebendo `File`:

```jinja
# Gerado pelo Ansible a partir de templates/gres.conf.j2.
{% for h in groups['compute'] %}
{% if hostvars[h].gpu_count | default(0) > 0 %}
NodeName={{ h }} Name=gpu {% if hostvars[h].gpu_device is defined %}File={{ hostvars[h].gpu_device }}{% else %}Count={{ hostvars[h].gpu_count }}{% endif %}
{% endif %}
{% for v in hostvars[h].virtual_nodes | default([]) if v.gpu_count | default(0) > 0 %}
NodeName={{ v.name }} Name=gpu Count={{ v.gpu_count }}
{% endfor %}
{% endfor %}
```

### Uma unidade do systemd para cada nó virtual

Cada nó virtual precisa de um processo próprio, iniciado com a opção `-N`, que dá ao `slurmd` o nome do nó que ele representa. A forma padrão de manter um processo ativo no Linux é uma unidade do systemd. O template abaixo gera uma unidade por nó virtual, e fica em `roles/slurm/templates/slurmd-virtual.service.j2`:

```ini
# Gerado pelo Ansible a partir de templates/slurmd-virtual.service.j2.
[Unit]
Description=Nó virtual {{ item.name }} do Slurm
After=network-online.target munge.service
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/sbin/slurmd -D -N {{ item.name }}
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Leitura:

- **`-D`** mantém o `slurmd` em primeiro plano, que é o modo esperado por uma unidade do tipo `simple`.
- **`-N`** informa o nome do nó que esse processo representa.
- **`Restart=on-failure`** reinicia o processo se ele cair por erro.
- **`After=munge.service`** garante que a autenticação esteja disponível antes do início.

As tarefas que renderizam e reiniciam essas unidades são adicionadas ao final de `roles/slurm/tasks/main.yml`:

```yaml
- name: Renderizar unidades dos nós virtuais
  ansible.builtin.template:
    src: slurmd-virtual.service.j2
    dest: "/etc/systemd/system/slurmd-{{ item.name }}.service"
    owner: root
    group: root
    mode: "0644"
  loop: "{{ virtual_nodes | default([]) }}"
  register: unidades_virtuais

- name: Reiniciar as unidades que mudaram
  ansible.builtin.systemd:
    name: "slurmd-{{ item.item.name }}"
    state: restarted
    enabled: true
    daemon_reload: true
  loop: "{{ unidades_virtuais.results }}"
  when: item.changed
```

A primeira tarefa grava uma unidade por nó virtual e guarda o resultado de cada uma em `unidades_virtuais`. A segunda reinicia somente as unidades que mudaram. `daemon_reload: true` pede ao systemd que releia as unidades antes de reiniciar, o que é necessário quando um arquivo de unidade muda.

### O diretório de spool

Cada `slurmd` grava arquivos temporários em um diretório de spool, configurado por `SlurmdSpoolDir`. Esse valor é único no `slurm.conf`, e todas as instâncias do `slurmd` leem o mesmo arquivo. Se todos os nós virtuais usarem o mesmo diretório, eles disputarão os mesmos arquivos, e o comportamento fica imprevisível.

Há duas saídas:

1. **Caminho de spool distinto por instância.** Algumas versões do Slurm aceitam, na opção `SlurmdSpoolDir`, uma substituição que gera um caminho diferente para cada nó. Antes de usar essa forma, confirme na documentação da versão instalada (`man slurm.conf`) se a sintaxe é suportada. Esta apostila não assume essa sintaxe, porque ela depende da versão.
2. **Nós virtuais em máquinas separadas.** Se a sintaxe não estiver disponível, cada nó simulado pode rodar em uma máquina virtual própria, como descrito na seção 10.2. Esse caminho não tem o problema do spool compartilhado, porque cada máquina tem o próprio sistema de arquivos.

Antes de escolher, verifique qual opção a sua versão suporta. Escolher a primeira sem confirmar leva a um cluster que parece funcionar, mas falha em jobs concorrentes.

### Verificando os nós virtuais

```bash
ansible-playbook site.yml --check --diff -K
ansible-playbook site.yml -K
sinfo -N -l
```

O `sinfo -N -l` deve listar o nó real e os virtuais, cada um com seu estado. Para um nó específico, confira os recursos declarados:

```bash
scontrol show node vnode1
```

Para verificar que um job chega ao nó virtual, use a opção `-w`, que escolhe o nó:

```bash
srun -w vnode1 hostname
```

A saída deve ser o nome do host real, porque o `slurmd` virtual roda na mesma máquina. Isso é esperado. O que muda é o nó que o Slurm reporta como alocado, que aparece em `squeue` durante a execução.

> **Referência:** SchedMD. *slurmd: Slurm compute node daemon*. slurm.schedmd.com. Descrição da opção `-N`, usada para representar nós simulados.
> **Referência:** Jinja Documentation. *Assignments: namespace objects*. jinja.palletsprojects.com. Uso de `namespace` para alterar variáveis dentro de laços.
> **Referência:** systemd. *systemd.service(5)*. freedesktop.org. Tipos de serviço, `Restart` e `ExecStart`.

---

## 10.2 Múltiplas máquinas virtuais e distribuição da chave munge

Com várias máquinas, o cluster deixa de ser simulado e passa a ter topologia de rede real. Nesta seção, as máquinas são máquinas virtuais criadas com o Multipass, sem GPU. Elas servem para validar a orquestração, a comunicação entre nós e a autenticação. O mesmo procedimento vale para máquinas físicas, desde que elas sejam alcançáveis por SSH.

### Preparando o acesso por SSH

O Ansible acessa cada máquina por SSH. Para isso, é preciso uma chave, criada uma vez na máquina de controle:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_cluster -N ""
```

A chave pública é colocada nas máquinas virtuais durante a criação, por meio de um arquivo de inicialização. Crie `cloud-init.yaml` com o conteúdo da chave pública:

```yaml
#cloud-config
ssh_authorized_keys:
  - <conteúdo de ~/.ssh/id_ed25519_cluster.pub>
```

Crie as máquinas com esse arquivo:

```bash
multipass launch --name ctl --cpus 2 --memory 2G --cloud-init cloud-init.yaml
multipass launch --name node01 --cpus 2 --memory 2G --cloud-init cloud-init.yaml
multipass list
```

A saída de `multipass list` mostra o endereço de cada máquina. Esses endereços vão para o inventário.

### Inventário com várias máquinas

Com máquinas separadas, cada host recebe o endereço de conexão com `ansible_host`, e o acesso é feito por SSH:

```yaml
all:
  children:
    controller:
      hosts:
        ctl:
          ansible_host: <ip-do-ctl>
    compute:
      hosts:
        node01:
          ansible_host: <ip-do-node01>
          cpus: 2
          real_memory: 1500
          gpu_count: 0
  vars:
    ansible_user: ubuntu
    ansible_ssh_private_key_file: ~/.ssh/id_ed25519_cluster
```

Pontos a notar:

- **O nome de cada host é o hostname da máquina.** No Multipass, o hostname é o próprio nome dado no `launch`. Essa regra mantém a abordagem B da Parte 3: o nome no inventário é o nome do nó.
- **`gpu_count: 0`** faz o template não gerar nenhuma linha `Gres` para o host, como visto na Parte 7.
- **`vars`** no nível do grupo `all` aplica a conexão SSH a todos os hosts.
- **`controller_host`** continua sendo `groups['controller'][0]`, que aqui resolve para `ctl`.

### Resolução de nomes entre as máquinas

Os nós precisam se encontrar pelo nome. Quando o `node01` procurar o `ctl`, o nome precisa resolver para o endereço certo. A forma mais simples, para um cluster pequeno, é registrar os hosts do inventário no arquivo `/etc/hosts` de cada máquina. Essa tarefa vai à role `base`:

```yaml
- name: Registrar os hosts do inventário em /etc/hosts
  ansible.builtin.lineinfile:
    path: /etc/hosts
    regexp: "^.*\\s{{ item }}$"
    line: "{{ hostvars[item].ansible_host }} {{ item }}"
  loop: "{{ groups['all'] }}"
  when: hostvars[item].ansible_host is defined
```

A tarefa percorre todos os hosts do inventário e grava uma linha por host no `/etc/hosts`. `lineinfile` com `regexp` substitui a linha existente em vez de duplicá-la, o que mantém a tarefa idempotente. A condição `when` pula hosts sem `ansible_host`, como a própria máquina de controle quando ela é conectada localmente.

### Distribuindo a chave do munge

A chave do munge precisa ser a mesma em todas as máquinas (Parte 4). A chave é gerada no controlador, e cada nó de computação recebe uma cópia. A distribuição usa três passos, executados na role `munge`:

1. O controlador copia a chave para a máquina de controle do Ansible, em uma pasta de segredos.
2. Cada nó de computação recebe a chave dessa pasta.
3. A pasta temporária é apagada ao final.

Antes da role, crie o arquivo de handlers, que ainda não existe. Ele tem a mesma forma dos outros:

```yaml
# roles/munge/handlers/main.yml
- name: restart munge
  ansible.builtin.systemd:
    name: munge
    state: restarted
```

As tarefas da role `munge` ficam assim:

```yaml
- name: Criar a pasta local de segredos
  ansible.builtin.file:
    path: "{{ playbook_dir }}/.segredos"
    state: directory
    mode: "0700"
  delegate_to: localhost
  run_once: true

- name: Copiar a chave do munge do controlador para a máquina de controle
  ansible.builtin.fetch:
    src: /etc/munge/munge.key
    dest: "{{ playbook_dir }}/.segredos/munge.key"
    flat: true
  when: inventory_hostname == groups['controller'][0]
  no_log: true

- name: Distribuir a chave do munge para os nós de computação
  ansible.builtin.copy:
    src: "{{ playbook_dir }}/.segredos/munge.key"
    dest: /etc/munge/munge.key
    owner: munge
    group: munge
    mode: "0400"
  when: "'compute' in group_names"
  no_log: true
  notify: restart munge

- name: Apagar a cópia local da chave
  ansible.builtin.file:
    path: "{{ playbook_dir }}/.segredos/munge.key"
    state: absent
  delegate_to: localhost
  run_once: true
  no_log: true
```

Leitura dos pontos que exigem atenção:

- **`fetch` e `copy` com `src`** são usados em vez de `content`, porque a chave é um arquivo binário. Um texto convertido para UTF-8 corromperia os bytes.
- **`no_log: true`** impede que o conteúdo das tarefas apareça na saída do Ansible. Sem isso, partes da chave ficariam no log do terminal.
- **A pasta `.segredos`** deve ficar fora do controle de versão. Se o projeto usar Git, acrescente essa pasta ao `.gitignore`.
- **`delegate_to: localhost`** executa a tarefa na máquina de controle, e não no host remoto.
- **A tarefa de cópia só roda nos nós de computação.** No controlador, a chave já está correta, porque foi gerada ali.

Esta abordagem é didática. Ela deixa a chave, por um instante, no disco da máquina de controle. Em ambientes que exigem mais proteção, a chave deve ficar em um cofre de segredos, como o Ansible Vault descrito na seção 10.3. A alternativa mais segura não está descrita nesta apostila.

### Verificação

A chave deve ser idêntica nas máquinas. Compare a soma de verificação em cada uma:

```bash
ansible all -b -m ansible.builtin.command -a "md5sum /etc/munge/munge.key"
```

Os valores devem ser iguais. A autenticação entre máquinas é testada com o munge, enviando uma credencial por SSH:

```bash
munge -n | ssh node01 unmunge
```

A saída deve mostrar `STATUS: Success (0)`. Se mostrar erro de credencial, as chaves são diferentes, ou os relógios das máquinas estão muito distantes. O munge rejeita credenciais com diferença de tempo acima do limite configurado. Mantenha as máquinas com sincronização de horário (NTP), que é o padrão em Ubuntu.

Por fim, confirme que o controlador enxerga o nó de computação:

```bash
sinfo -N -l
```

O `node01` deve aparecer em `idle`. Se aparecer `down`, verifique a conectividade nas portas padrão do Slurm, que são 6817 para o controlador e 6818 para os nós, e o motivo registrado em `scontrol show node node01`.

> **Referência:** Multipass. *Multipass documentation: cloud-init*. multipass.run. Uso de `--cloud-init` para configurar chaves e usuários na criação da máquina.
> **Referência:** Ansible. *ansible.builtin.fetch module*. docs.ansible.com. Parâmetro `flat` e cópia de arquivos do host remoto para a máquina de controle.
> **Referência:** Ansible. *Keeping secrets: no_log and Ansible Vault*. docs.ansible.com. Uso de `no_log` e cofres de segredos.
> **Referência:** Dun, C. *MUNGE Uid 'N' Gid Emporium*. dun.github.io/munge. Requisitos de sincronização de relógio e formato de credenciais.

---

## 10.3 Accounting com slurmdbd e MariaDB

Até aqui, o Slurm registra apenas o estado atual. O **accounting** (contabilidade) guarda o histórico de cada job: quem o enviou, quando começou, quanto tempo durou e em que estado terminou. Esse histórico é o que permite consultas como `sacct` e análises de uso do cluster.

A arquitetura tem três partes, como vista na Parte 1:

```
slurmctld ──► slurmdbd ──► MariaDB
                 ▲
           sacct (consulta)
```

- **MariaDB** é o banco de dados que armazena os registros.
- **slurmdbd** é o daemon que recebe os registros do controlador e os grava no banco.
- **sacct** consulta os registros por meio do slurmdbd.

Nesta seção, o slurmdbd roda no controlador. Em clusters maiores, ele pode rodar em outra máquina.

### Pacotes

Instale o banco e o daemon de accounting. Eles são pacotes separados do `slurm-wlm`:

```yaml
- name: Instalar MariaDB e slurmdbd
  ansible.builtin.apt:
    name:
      - mariadb-server
      - slurmdbd
    state: present
    update_cache: true
  when: "'controller' in group_names"
```

Confirme os nomes na sua versão com `apt policy slurmdbd`, como visto na Parte 2.

### Banco e usuário

O Ansible tem módulos próprios para criar bancos e usuários no MariaDB. Eles fazem parte da coleção `community.mysql`, instalada com:

```bash
ansible-galaxy collection install community.mysql
```

As tarefas usam a senha do usuário do banco, que deve ser tratada como segredo. O Ansible Vault guarda valores sensíveis cifrados dentro do repositório. Para gerar o valor cifrado:

```bash
ansible-vault encrypt_string 'senha-do-banco' --name slurm_db_password
```

O resultado é um bloco cifrado, que pode ser colado em `group_vars/all.yml`. Ele só pode ser lido com a senha do cofre. Guarde essa senha fora do repositório.

As tarefas de banco ficam em uma role própria, `slurmdbd`, criada nesta parte. Ela tem a mesma estrutura das outras roles (tarefas, handlers e templates), e precisa ser incluída no playbook antes da role `slurm`, porque o slurmdbd deve estar pronto antes do controlador:

```yaml
- name: Configuração mínima do cluster
  hosts: all
  become: true
  roles:
    - base
    - munge
    - slurmdbd
    - slurm
```

Dentro da role `slurmdbd`, o handler que reinicia o serviço segue o mesmo padrão dos demais:

```yaml
# roles/slurmdbd/handlers/main.yml
- name: restart slurmdbd
  ansible.builtin.systemd:
    name: slurmdbd
    state: restarted
  when: "'controller' in group_names"
```

As tarefas de banco são:

```yaml
- name: Criar o banco do histórico
  community.mysql.mysql_db:
    name: slurm_acct_db
    state: present
    login_unix_socket: /run/mysqld/mysqld.sock
  when: "'controller' in group_names"

- name: Criar o usuário do histórico
  community.mysql.mysql_user:
    name: slurm
    password: "{{ slurm_db_password }}"
    priv: "slurm_acct_db.*:ALL"
    host: localhost
    state: present
    login_unix_socket: /run/mysqld/mysqld.sock
  no_log: true
  when: "'controller' in group_names"
```

Os dois módulos são idempotentes: criar um banco ou um usuário que já existe não causa alteração.

### Configuração do slurmdbd

O slurmdbd lê o arquivo `/etc/slurm/slurmdbd.conf`. Ele contém a senha do banco, por isso tem permissões restritas. O template fica em `roles/slurmdbd/templates/slurmdbd.conf.j2`:

```jinja
# Gerado pelo Ansible a partir de templates/slurmdbd.conf.j2.
AuthType=auth/munge
DbdHost={{ controller_host }}
SlurmUser=slurm
LogFile=/var/log/slurm/slurmdbd.log
PidFile=/run/slurmdbd.pid
StorageType=accounting_storage/mysql
StorageHost=localhost
StorageUser=slurm
StoragePass={{ slurm_db_password }}
StorageLoc=slurm_acct_db
```

Leitura:

- **`DbdHost`** informa em qual máquina o slurmdbd roda.
- **`StorageType=accounting_storage/mysql`** indica o banco usado.
- **`StorageLoc`** é o nome do banco criado acima.
- **`StoragePass`** recebe a senha, que o Ansible decifra na execução.

O arquivo precisa de permissões restritas, e o Slurm exige que apenas o usuário `slurm` consiga lê-lo:

```yaml
- name: Renderizar slurmdbd.conf
  ansible.builtin.template:
    src: slurmdbd.conf.j2
    dest: /etc/slurm/slurmdbd.conf
    owner: slurm
    group: slurm
    mode: "0600"
  no_log: true
  when: "'controller' in group_names"
  notify: restart slurmdbd
```

A pasta de logs também precisa existir, com dono `slurm`:

```yaml
- name: Criar a pasta de logs do slurmdbd
  ansible.builtin.file:
    path: /var/log/slurm
    state: directory
    owner: slurm
    group: slurm
    mode: "0755"
  when: "'controller' in group_names"
```

### Mudanças no `slurm.conf`

O controlador precisa saber que o histórico está ativo. A forma mais simples é uma variável que liga e desliga o accounting, em `group_vars/all.yml`:

```yaml
slurm_accounting: true
```

O template de `slurm.conf` escolhe a configuração conforme essa variável. O bloco abaixo substitui as linhas fixas de accounting da Parte 7:

```jinja
{% if slurm_accounting | default(false) %}
AccountingStorageType=accounting_storage/slurmdbd
AccountingStorageHost={{ controller_host }}
JobAcctGatherType=jobacct_gather/linux
{% else %}
AccountingStorageType=accounting_storage/none
JobAcctGatherType=jobacct_gather/none
{% endif %}
```

O filtro `default(false)` mantém o comportamento anterior quando a variável não existe. Assim, o cluster sem accounting continua válido.

### Ordem de inicialização

O slurmdbd precisa estar ativo antes do controlador, porque o controlador tenta conectar-se a ele no início. Por isso, a última tarefa da role `slurmdbd` garante que o serviço esteja iniciado. Como a role `slurmdbd` vem antes de `slurm` no playbook, o `slurmctld` só é iniciado depois que o histórico já está disponível:

```yaml
- name: Garantir que slurmdbd está ativo
  ansible.builtin.systemd:
    name: slurmdbd
    state: started
    enabled: true
  when: "'controller' in group_names"
```

### Cadastro do cluster e de usuários

O histórico exige que o cluster, as contas e os usuários estejam cadastrados no banco. Essa etapa usa o comando `sacctmgr`:

```bash
sudo sacctmgr -i add cluster mini-cluster
sudo sacctmgr -i add account pesquisa description="Conta de teste" organization="exemplo"
sudo sacctmgr -i add user <usuario> account=pesquisa
```

Substitua `mini-cluster` pelo valor de `cluster_name`, e `<usuario>` pelo nome de quem enviará os jobs. A opção `-i` pede confirmação automática.

Esta etapa ainda não é idempotente nesta apostila. Execute-a uma vez, depois confira o resultado:

```bash
sacctmgr show cluster
sacctmgr show user
```

### Verificando o histórico

Envie um job de teste, espere ele terminar, e consulte o histórico:

```bash
srun hostname
sacct -X --format=JobID,User,Partition,Elapsed,State
```

A consulta deve listar o job com o estado `COMPLETED`. Se o comando responder que o armazenamento de histórico está desativado, o `slurmctld` não está apontado para o slurmdbd. Confira `AccountingStorageType` no `slurm.conf` gerado e o estado de `slurmdbd`:

```bash
systemctl status slurmdbd
```

> **Referência:** SchedMD. *Accounting: Slurm Accounting*. slurm.schedmd.com. Arquitetura de contabilidade e papel do slurmdbd.
> **Referência:** SchedMD. *slurmdbd.conf: Slurm Database Daemon configuration file*. slurm.schedmd.com. Opções de banco e permissões.
> **Referência:** SchedMD. *sacctmgr: Slurm Accounting Manager*. slurm.schedmd.com. Cadastro de clusters, contas e usuários.
> **Referência:** Ansible Community. *community.mysql collection*. docs.ansible.com. Módulos `mysql_db` e `mysql_user`.
> **Referência:** Ansible. *Using Ansible Vault to encrypt sensitive data*. docs.ansible.com. Criação e uso de valores cifrados.
> **Referência:** MariaDB Foundation. *MariaDB Documentation*. mariadb.org. Instalação e administração do servidor.

---

## Resumo da Parte 10

Ao final, você sabe declarar nós virtuais no mesmo host e entende seus limites, inclusive o problema do diretório de spool. Você distribui a chave do munge entre máquinas sem expô-la na saída e sem deixá-la no repositório, e valida a autenticação entre elas. Você também ativa o accounting, com o slurmdbd, o MariaDB e o cadastro de cluster, contas e usuários, e confirma o histórico com `sacct`.

Cada uma dessas funções acrescenta uma dependência. Por isso, a ordem recomendada é validar cada seção antes de seguir para a próxima.

**Próxima:** Parte 11, Solução de problemas.
