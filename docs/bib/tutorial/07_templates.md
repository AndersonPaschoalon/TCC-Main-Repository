# Parte 7: Templates: gerando configuração a partir de variáveis

**Objetivo desta parte:** entender como o Jinja2 transforma as variáveis do projeto em arquivos de configuração do Slurm, e escrever os três templates que a role `slurm` usa.

**Pré-requisito:** Partes 3 a 6 concluídas. O arquivo `group_vars/all.yml` existe e contém os valores reais da máquina, e você conhece as opções de `slurm.conf`, `gres.conf` e `cgroup.conf`.

**Esta parte cria arquivos, mas não os instala.** Os templates ficam dentro da role, em `roles/slurm/templates/`. A geração no sistema acontece na Parte 8, quando o playbook os executa. Você pode testar a renderização antes, como mostrado na seção 7.2.

---

## 7.1 Jinja2: variáveis, laços e condicionais

Um **template** é um texto que contém espaços reservados. Quando o template é processado, cada espaço reservado é substituído por um valor. O Jinja2 é a linguagem de templates usada pelo Ansible. Ele tem três construções básicas.

### Variáveis

A sintaxe `{{ nome }}` insere o valor de uma variável:

```jinja
ClusterName={{ cluster_name }}
```

Se `cluster_name` valer `mini-cluster`, o resultado é `ClusterName=mini-cluster`. Se a variável não existir, o Ansible falha com a mensagem `'cluster_name' is undefined`. Essa falha é desejada: um arquivo com valor vazio ou ausente seria mais difícil de diagnosticar.

Para acessar um campo de um item de dicionário, use ponto:

```jinja
NodeAddr={{ node.addr }}
```

### Laços

A construção `{% for %}` repete um trecho para cada item de uma lista:

```jinja
{% for node in slurm_nodes %}
NodeName={{ node.name }} CPUs={{ node.cpus }}
{% endfor %}
```

Se `slurm_nodes` tiver dois itens, o trecho é gerado duas vezes. É esse mecanismo que permite declarar os nós uma única vez, em `group_vars/all.yml`, e obter uma linha por nó no arquivo final.

### Condicionais

A construção `{% if %}` inclui um trecho apenas quando a condição é verdadeira:

```jinja
{% if node.gpu_device is defined %}File={{ node.gpu_device }}{% else %}Count={{ node.gpu_count }}{% endif %}
```

O teste `is defined` verifica se a chave existe no item. Sem essa verificação, acessar uma chave inexistente causaria erro. Um teste muito usado é `default(valor)`, que substitui o valor ausente por um padrão:

```jinja
{{ node.gpu_count | default(0) }}
```

O símbolo `|` aplica um **filtro** ao valor. Filtros transformam valores: `default` substitui ausentes, e `join` junta uma lista em um texto, como visto na seção 7.2.

### Espaços em branco

Cada `{% ... %}` deixa uma quebra de linha no arquivo gerado. Para evitar linhas vazias, o Jinja2 aceita um traço nas bordas da marcação: `{%- ... %}` remove os espaços antes, e `{% ... -%}` remove os espaços depois. Neste capítulo, os templates usam as marcações sem traço, porque as linhas vazias não atrapalham a leitura do Slurm.

> **Referência:** Pallets. *Jinja Documentation*. jinja.palletsprojects.com. Sintaxe de variáveis, laços, condicionais e filtros.
> **Referência:** Ansible. *Templating (Jinja2)*. docs.ansible.com. Como o Ansible usa o Jinja2 e quais variáveis estão disponíveis em um template.

---

## 7.2 `slurm.conf.j2` passo a passo

O template de `slurm.conf` fica em `roles/slurm/templates/slurm.conf.j2`. Ele combina dois tipos de conteúdo: valores fixos, que valem para qualquer cluster desta apostila, e valores vindos das variáveis, que mudam conforme a máquina e o número de nós.

Versão completa do template:

```jinja
# Gerado pelo Ansible a partir de templates/slurm.conf.j2.
# Não editar à mão: alterações são sobrescritas na próxima execução.
ClusterName={{ cluster_name }}
SlurmctldHost={{ controller_host }}
SlurmUser=slurm
StateSaveLocation=/var/spool/slurmctld
SlurmdSpoolDir=/var/spool/slurmd
SlurmctldPidFile=/run/slurmctld.pid
SlurmdPidFile=/run/slurmd.pid
ReturnToService=2
SlurmdParameters=config_overrides

ProctrackType=proctrack/cgroup
TaskPlugin=task/cgroup,task/affinity
SchedulerType=sched/backfill
SelectType=select/cons_tres
SelectTypeParameters=CR_Core
GresTypes=gpu

AccountingStorageType=accounting_storage/none
JobAcctGatherType=jobacct_gather/none

{% for node in slurm_nodes %}
NodeName={{ node.name }} NodeAddr={{ node.addr }} Port={{ node.port }} CPUs={{ node.cpus }} RealMemory={{ node.real_memory }}{% if node.gpu_count | default(0) > 0 %} Gres=gpu:{{ node.gpu_count }}{% endif %} State=UNKNOWN
{% endfor %}

PartitionName=debug Nodes={{ slurm_nodes | map(attribute='name') | join(',') }} Default=YES MaxTime=INFINITE State=UP
```

### Parte fixa e parte variável

As linhas sem marcação Jinja são fixas. Elas aparecem idênticas em qualquer cluster gerado por este template. O valor de `ReturnToService`, por exemplo, foi apresentado na Parte 5 e não depende da máquina.

As linhas com marcação são variáveis. Elas dependem de `group_vars/all.yml`:

- **`ClusterName`** recebe o nome do cluster.
- **`SlurmctldHost`** recebe o nome do controlador. Como visto na Parte 5, o valor precisa coincidir com o nome real da máquina.
- **As linhas `NodeName`** são geradas uma por nó, a partir da lista `slurm_nodes`.
- **A linha `PartitionName`** lista todos os nós na partição `debug`.

### O laço dos nós

O trecho central é este:

```jinja
{% for node in slurm_nodes %}
NodeName={{ node.name }} NodeAddr={{ node.addr }} Port={{ node.port }} CPUs={{ node.cpus }} RealMemory={{ node.real_memory }}{% if node.gpu_count | default(0) > 0 %} Gres=gpu:{{ node.gpu_count }}{% endif %} State=UNKNOWN
{% endfor %}
```

O laço gera uma linha para cada item de `slurm_nodes`. Dentro dele, a condição `if node.gpu_count | default(0) > 0` acrescenta `Gres=gpu:N` apenas para nós com GPU. Um nó sem GPU recebe uma linha sem a parte `Gres`, e não uma declaração com zero unidades. Isso evita uma linha de GPU que não corresponde a nada real.

### A lista de partição

```jinja
PartitionName=debug Nodes={{ slurm_nodes | map(attribute='name') | join(',') }} Default=YES MaxTime=INFINITE State=UP
```

Esta linha usa dois filtros. O `map(attribute='name')` extrai apenas o campo `name` de cada item da lista, e o `join(',')` junta os nomes separados por vírgula. Com dois nós chamados `node01` e `node02`, o resultado é `Nodes=node01,node02`.

### Testando a renderização sem instalar

A renderização completa é observada com a opção `--diff`, que mostra o conteúdo que seria gravado em cada arquivo. Essa opção só produz saída útil quando a tarefa de renderização existe, e ela é escrita na Parte 8. Até lá, o comando abaixo apenas confirma que o playbook continua válido:

```bash
ansible-playbook site.yml --check --diff -K
```

Na Parte 8, a mesma linha de comando passa a mostrar o texto exato de `slurm.conf`, `gres.conf` e `cgroup.conf` antes de qualquer gravação. Se houver erro de sintaxe em um template, a mensagem aponta o arquivo e a linha.

> **Referência:** Ansible. *ansible.builtin.template module*. docs.ansible.com. Parâmetros `src`, `dest`, `mode` e a opção de renderização.
> **Referência:** Ansible. *Using filters to manipulate data*. docs.ansible.com. Filtros `default`, `map` e `join`.

---

## 7.3 `gres.conf.j2` e a diferença entre nó com GPU física e nó sem GPU física

O template de `gres.conf` fica em `roles/slurm/templates/gres.conf.j2`. Ele declara os dispositivos de GPU, e só deve gerar linhas para nós que têm GPU.

```jinja
# Gerado pelo Ansible a partir de templates/gres.conf.j2.
{% for node in slurm_nodes if node.gpu_count | default(0) > 0 %}
NodeName={{ node.name }} Name=gpu {% if node.gpu_device is defined %}File={{ node.gpu_device }}{% else %}Count={{ node.gpu_count }}{% endif %}
{% endfor %}
```

### O filtro no laço

A diferença em relação ao laço do `slurm.conf` está na própria declaração do `for`:

```jinja
{% for node in slurm_nodes if node.gpu_count | default(0) > 0 %}
```

A cláusula `if` no laço filtra os itens antes da iteração. Nós sem GPU são ignorados, e o arquivo nunca contém uma linha para eles.

### Dois casos de declaração

O bloco condicional dentro da linha escolhe a forma de declarar a GPU:

- **Nó com dispositivo real** (`gpu_device` definido): a linha usa `File=`, e o Slurm pode isolar o dispositivo com cgroups, como visto na Parte 6.
- **Nó sem dispositivo real** (`gpu_device` ausente): a linha usa `Count=`, e o Slurm apenas reserva unidades, sem isolar nada.

Em `group_vars/all.yml`, a distinção é feita pela presença ou ausência da chave `gpu_device`:

```yaml
slurm_nodes:
  - name: node01
    addr: 127.0.0.1
    port: 6818
    cpus: 8
    real_memory: 7900
    gpu_count: 1
    gpu_device: /dev/nvidia0

  - name: node02
    addr: 127.0.0.1
    port: 6819
    cpus: 2
    real_memory: 1000
    gpu_count: 2
```

O `node01` tem GPU física e recebe `File=/dev/nvidia0`. O `node02` declara duas GPUs sem dispositivo real e recebe `Count=2`. Esse segundo caso é o que a Parte 10 usa para nós simulados.

> **Atenção:** o número de linhas `File=` deve bater com o `gpu_count` do nó. Se `gpu_count` for `2` e `gpu_device` apontar para um único arquivo, o Slurm recebe menos dispositivos do que declarou. Confira a correspondência antes de aplicar.

> **Referência:** SchedMD. *gres.conf: Generic Resource configuration file*. slurm.schedmd.com/gres.conf.html. Sintaxe de `File=` e `Count=`.

---

## 7.4 Por que nunca editar arquivos gerados

Os arquivos `/etc/slurm/slurm.conf`, `/etc/slurm/gres.conf` e `/etc/slurm/cgroup.conf` são gerados pelo Ansible. Editar um deles diretamente parece mais rápido, mas tem três problemas:

1. **A mudança desaparece.** Na próxima execução do playbook, o template é aplicado de novo e o arquivo volta ao estado do repositório. Isso é a propriedade de idempotência funcionando: o estado desejado vence o estado manual.
2. **A mudança fica fora do histórico.** Como o arquivo gerado não está no repositório, ninguém consegue ver o que foi alterado nem quando.
3. **A mudança não se repete.** Se o cluster for recriado em outra máquina, a edição manual se perde, porque ela não está descrita em nenhum arquivo versionado.

A regra prática é: altere a fonte, e não o resultado. Para mudar o número de CPUs de um nó, altere `cpus` em `group_vars/all.yml`. Para mudar a forma como o escalonador funciona, altere o template em `roles/slurm/templates/`.

Os cabeçalhos dos templates trazem o aviso `Gerado pelo Ansible`. Ele existe para quem abrir o arquivo gerado sem saber de onde ele vem.

Para verificar se um arquivo gerado foi alterado fora do Ansible, compare-o com a saída do template. A execução com `--check --diff` mostra a diferença entre o que está no sistema e o que o template produziria:

```bash
ansible-playbook site.yml --check --diff -K
```

Se houver diferença em um arquivo gerado, a saída mostra as linhas que mudariam. Isso é a forma de detectar edições manuais esquecidas.

> **Referência:** Morris, K. *Infrastructure as Code: Managing Servers in the Cloud*. O'Reilly. Capítulo sobre configuração declarativa e o problema da deriva de configuração (*configuration drift*). (Verifique a edição antes de citar.)

---

## Resumo da Parte 7

Ao final, você entende como o Jinja2 usa variáveis, laços e condicionais para gerar texto, e escreveu os três templates da role `slurm`. O `slurm.conf.j2` combina uma parte fixa com linhas geradas por nó, o `gres.conf.j2` declara apenas os nós com GPU, e a diferença entre `File=` e `Count=` depende da presença de `gpu_device`. Você também sabe por que os arquivos gerados não devem ser editados à mão.

Os templates ainda não foram aplicados ao sistema. A tarefa que os renderiza, e os handlers que reiniciam os serviços, são escritos na Parte 8.

**Próxima:** Parte 8, Integração do playbook ao cluster funcionando.
