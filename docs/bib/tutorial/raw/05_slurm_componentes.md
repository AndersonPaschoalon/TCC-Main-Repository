# Parte 5: Slurm, componente por componente

**Objetivo desta parte:** entender cada componente do Slurm, o papel de cada arquivo de configuração e as decisões de escalonamento que o arquivo principal controla, antes de gerar esse arquivo com o Ansible.

**Pré-requisito:** Parte 4 concluída. Os pacotes do Slurm e do munge estão instalados, e o munge autentica localmente.

**Esta parte é de estudo.** Os exemplos de configuração são ilustrativos e não são aplicados ao sistema. A geração do arquivo real acontece na Parte 7, por meio de templates. Nenhum arquivo do Slurm deve ser editado à mão.

---

## 5.1 Arquitetura: `slurmctld`, `slurmd`, `slurmdbd` e os comandos do usuário

O Slurm é composto por processos (chamados *daemons*) que rodam em segundo plano, e por comandos que o usuário digita. Cada daemon tem um papel e fica em um tipo de máquina diferente.

| Componente | Tipo | Onde roda | Papel |
|---|---|---|---|
| `slurmctld` | Daemon | Controlador | Mantém a fila de jobs, decide quais recursos cada job recebe e acompanha o estado de todos os nós. |
| `slurmd` | Daemon | Cada nó de computação | Recebe ordens do controlador, executa os jobs e informa ao controlador o estado do próprio nó. |
| `slurmdbd` | Daemon | Controlador ou máquina dedicada | Grava o histórico de jobs em um banco de dados. É opcional e será usado na Parte 10. |
| `sinfo`, `squeue`, `sbatch`, `srun`, `scancel`, `sacct` | Comandos | Qualquer máquina do cluster | Consultam o estado, enviam jobs e cancelam jobs. |

Um fluxo típico, de quando o usuário envia um job até o término:

```
usuário ── sbatch ──► slurmctld ──► escolhe o nó e os recursos
                          │
                          ▼
                       slurmd (no nó escolhido) ──► executa o job
                          │
                          ▼
                 slurmctld registra o término
```

O usuário nunca fala diretamente com o `slurmd`. Todo pedido passa pelo controlador, que é o único componente com visão completa do cluster. Essa centralização é o que permite à fila funcionar como uma fila única.

### Como verificar se um daemon está ativo

Os daemons são serviços do systemd, e o diagnóstico começa pelo mesmo caminho de qualquer outro serviço:

```bash
systemctl status slurmctld
systemctl status slurmd
```

Para ler os registros de um serviço, use o `journalctl`, detalhado na Parte 11:

```bash
journalctl -u slurmctld --no-pager -n 20
```

Quando um daemon falha ao iniciar, é comum que o motivo esteja no registro, e não na linha de status. O comando acima mostra as últimas vinte linhas do registro.

### Modo de primeiro plano

Para depurar um daemon, é útil rodá-lo no terminal, em vez de em segundo plano. A opção `-D` mantém o processo em primeiro plano, e `-vvv` aumenta o nível de detalhe das mensagens. Exemplo com o `slurmd`:

```bash
sudo slurmd -D -vvv
```

Para interromper, use `Ctrl+C`. Esse modo é usado apenas para diagnóstico, porque o serviço do systemd precisa estar parado para não haver dois processos disputando a mesma porta. Pare o serviço antes:

```bash
sudo systemctl stop slurmd
```

> **Referência:** SchedMD. *Slurm Quick Start Administrator Guide*. slurm.schedmd.com/quickstart_admin.html. Descreve a arquitetura de daemons e as máquinas em que cada um roda.
> **Referência:** Yoo, A. B.; Jette, M. A.; Grondona, M. *SLURM: Simple Linux Utility for Resource Management*. In: Job Scheduling Strategies for Parallel Processing (JSSPP), Springer, 2003. Artigo científico que descreve a arquitetura original do Slurm.

---

## 5.2 `slurm.conf`: o arquivo principal de configuração

O arquivo `/etc/slurm/slurm.conf` é lido por todos os daemons e comandos do Slurm. Ele descreve o cluster inteiro: quem são as máquinas, quais recursos cada uma tem, como as filas são organizadas e como o escalonador decide. Como todos os componentes leem o mesmo arquivo, ele precisa ser idêntico em todas as máquinas do cluster.

As opções do arquivo se agrupam em áreas. A tabela abaixo mostra as áreas que esta parte explica, com o nome da opção e o assunto da seção em que ela é detalhada:

| Área | Exemplos de opções | Detalhado em |
|---|---|---|
| Identificação | `ClusterName`, `SlurmctldHost` | Esta seção |
| Usuário e caminhos | `SlurmUser`, `StateSaveLocation`, `SlurmdSpoolDir` | Esta seção |
| Processos e isolamento | `ProctrackType`, `TaskPlugin` | Seção 5.4 e Parte 6 |
| Escalonador | `SchedulerType`, `SelectType`, `SelectTypeParameters` | Seção 5.4 |
| Recursos genéricos | `GresTypes` | Parte 6 |
| Histórico | `AccountingStorageType`, `JobAcctGatherType` | Parte 10 |
| Nós e partições | `NodeName`, `PartitionName` | Seção 5.3 |

Um trecho ilustrativo do início do arquivo, para entender o formato:

```ini
ClusterName=mini-cluster
SlurmctldHost=nome-da-maquina
SlurmUser=slurm
StateSaveLocation=/var/spool/slurmctld
SlurmdSpoolDir=/var/spool/slurmd
```

Leitura:

- **`ClusterName`** é um nome livre para o cluster. Aparece em relatórios e em algumas mensagens de log.
- **`SlurmctldHost`** informa em qual máquina o controlador roda. O valor deve ser o nome real da máquina, o mesmo retornado por `hostname -s`. Se o nome estiver diferente, o `slurmctld` não reconhece a própria máquina como controlador e não inicia.
- **`SlurmUser`** é o usuário sob o qual o `slurmctld` roda. É por isso que o diretório de estado, na Parte 4, pertence a esse usuário.
- **`StateSaveLocation`** é o diretório onde o controlador grava a fila e o estado dos jobs. Se esse diretório for apagado, a fila em andamento é perdida.
- **`SlurmdSpoolDir`** é o diretório de trabalho temporário do nó de computação.

Formato geral do arquivo: cada linha define uma opção no formato `Nome=valor`. Opções são case-sensitive, ou seja, `ClusterName` e `clustername` são diferentes. Comentários começam com `#`.

Para consultar o significado de qualquer opção, use o manual do arquivo:

```bash
man slurm.conf
```

> **Atenção:** o arquivo `slurm.conf` será gerado pelo Ansible a partir de um template (Parte 7). Edições feitas diretamente no arquivo gerado são sobrescritas na próxima execução do playbook. Para alterar a configuração, altere a fonte, que são as variáveis do inventário e de `group_vars/all.yml`.

> **Referência:** SchedMD. *slurm.conf: Slurm configuration file*. slurm.schedmd.com/slurm.conf.html. Documentação completa de todas as opções.

---

## 5.3 Nós (`NodeName`) e partições (`PartitionName`)

Dois conceitos organizam o cluster dentro do `slurm.conf`:

- **Nó** é uma máquina de computação, descrita pela linha `NodeName`. A linha informa quanto hardware a máquina tem.
- **Partição** é um grupo de nós com regras comuns, descrito pela linha `PartitionName`. Um usuário escolhe em qual partição o job será enviado, e a partição limita quais nós podem recebê-lo.

Um exemplo ilustrativo com um nó e uma partição:

```ini
NodeName=node01 NodeAddr=127.0.0.1 Port=6818 CPUs=8 RealMemory=7900 Gres=gpu:1 State=UNKNOWN
PartitionName=debug Nodes=node01 Default=YES MaxTime=INFINITE State=UP
```

Leitura da linha de nó:

- **`NodeName`** é o nome do nó. Deve coincidir com o nome que o próprio nó usa para se identificar.
- **`NodeAddr`** e **`Port`** indicam onde o controlador encontra o `slurmd` desse nó. Em uma máquina só, o endereço é `127.0.0.1`, que aponta para a própria máquina.
- **`CPUs`** e **`RealMemory`** são os recursos declarados. Como visto na Parte 4, eles não devem exceder o que a máquina realmente tem.
- **`Gres=gpu:1`** declara uma GPU. A declaração do dispositivo físico fica em outro arquivo, detalhado na Parte 6.
- **`State=UNKNOWN`** é o estado inicial. O controlador troca esse estado para `IDLE` quando o `slurmd` do nó responde corretamente.

Leitura da linha de partição:

- **`Nodes=node01`** lista os nós que pertencem à partição. Pode ser uma lista separada por vírgulas.
- **`Default=YES`** faz desta a partição usada quando o usuário não escolhe outra.
- **`MaxTime=INFINITE`** não limita o tempo de execução dos jobs. Em clusters compartilhados, costuma-se usar um limite, como `MaxTime=24:00:00`. Esse ajuste é uma decisão de política do cluster, e não um valor técnico obrigatório.
- **`State=UP`** deixa a partição aceitando jobs. Com `DOWN`, a partição recusa novos envios.

Dois nomes diferentes para dois conceitos diferentes, e uma regra prática: o nó é o hardware, e a partição é a regra de acesso ao hardware. Um mesmo nó pode pertencer a mais de uma partição.

> **Referência:** SchedMD. *slurm.conf: NodeName and PartitionName*. slurm.schedmd.com/slurm.conf.html. Seções sobre nós e partições.

---

## 5.4 Escalonador e seleção de recursos

Esta seção trata de três decisões que o `slurm.conf` controla: quando um job começa, quais recursos ele recebe e como o Slurm rastreia os processos de cada job.

### Escalonador: `SchedulerType`

Um escalonador decide a ordem em que os jobs da fila começam. Duas políticas básicas são importantes:

- **FIFO (*first in, first out*):** o primeiro job da fila é o primeiro a começar. É simples e justo na ordem de chegada, mas um job grande pode bloquear a fila inteira enquanto espera recursos que demorarão a liberar.
- **Backfill:** permite que jobs menores, que cabem no tempo livre antes de um job grande começar, sejam executados antes dele, sem atrasá-lo. Isso aumenta o uso dos recursos.

A linha correspondente no arquivo é:

```ini
SchedulerType=sched/backfill
```

O valor `sched/backfill` ativa a política de backfill. A barra separa o tipo de plugin do nome do plugin, um padrão que se repete em várias opções do Slurm.

### Seleção de recursos: `SelectType` e `SelectTypeParameters`

A seleção de recursos decide quais partes de cada nó um job recebe. Duas opções definem isso:

```ini
SelectType=select/cons_tres
SelectTypeParameters=CR_Core
```

- **`select/cons_tres`** trata CPUs, memória e recursos genéricos (como GPUs) como recursos consumíveis. Um job reserva o que pediu, e o restante continua disponível para outros jobs. É a opção que permite declarar GPUs como recurso (Parte 6).
- **`CR_Core`** significa que a unidade de alocação de CPU é o núcleo físico. Um job que pede uma CPU recebe um núcleo inteiro, e não uma parte dele. Essa escolha evita que dois jobs disputem o mesmo núcleo.

### Rastreamento de processos: `ProctrackType` e `TaskPlugin`

Para cancelar um job e garantir que nenhum processo dele sobreviva, o Slurm precisa identificar todos os processos que pertencem a esse job. Duas opções tratam disso:

```ini
ProctrackType=proctrack/cgroup
TaskPlugin=task/cgroup,task/affinity
```

- **`proctrack/cgroup`** identifica os processos de um job por meio de cgroups (apresentados na Parte 6). Um processo que tente escapar do grupo continua sendo rastreado.
- **`task/cgroup`** aplica os limites de recursos do cgroup a cada tarefa do job.
- **`task/affinity`** vincula cada tarefa a núcleos específicos, o que evita que o sistema operacional mova processos entre núcleos durante a execução.

### Retomada após falha: `ReturnToService`

```ini
ReturnToService=2
```

Essa opção define como um nó que estava indisponível volta a receber jobs. O valor `2` faz o nó voltar quando o `slurmd` se reapresenta ao controlador com a configuração declarada. Os valores `0` e `1` exigem intervenção manual ou aceitam o retorno de nós com configuração diferente da declarada, o que pode esconder erros de hardware. Para este tutorial, `2` é o valor adequado.

> **Referência:** SchedMD. *slurm.conf: SchedulerType, SelectType, ProctrackType, TaskPlugin, ReturnToService*. slurm.schedmd.com/slurm.conf.html. Descrição de cada opção e dos valores aceitos.
> **Referência:** Feitelson, D. G.; Rudolph, L.; Schwiegelshohn, U.; Sevcik, K. C.; Wong, P. *Theory and Practice in Parallel Job Scheduling*. In: Job Scheduling Strategies for Parallel Processing (JSSPP), Springer, 1997. Artigo científico sobre a teoria por trás de políticas como FIFO e backfill. (Verifique a referência exata antes de citar.)

---

## Resumo da Parte 5

Ao final, você entende os três daemons do Slurm e os comandos que o usuário usa, sabe o que cada área do `slurm.conf` controla, e conhece a diferença entre nó e partição. Também entende as decisões de escalonamento que o arquivo define: política de fila, seleção de recursos consumíveis e rastreamento de processos.

Nada foi aplicado ao sistema nesta parte. Os valores de exemplo serão substituídos pelos seus valores reais na geração do arquivo, na Parte 7.

**Próxima:** Parte 6, GPU como recurso agendável.
