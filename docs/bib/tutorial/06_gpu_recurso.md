# Parte 6: GPU como recurso agendável

**Objetivo desta parte:** fazer com que o Slurm reconheça GPUs como recurso que pode ser pedido e reservado, e entender como o isolamento por cgroups garante que cada job use apenas as GPUs que recebeu.

**Pré-requisito:** Parte 5 concluída. Você conhece as opções `GresTypes`, `Gres`, `SelectType` e `ProctrackType`.

**Esta parte é de estudo, e a seção 6.3 descreve um teste de conferência.** Os arquivos de exemplo são ilustrativos. A geração dos arquivos reais acontece na Parte 7. Se o sistema não tiver GPU, leia esta parte mesmo assim, porque a lógica se aplica a qualquer recurso genérico, e substitua os exemplos de GPU por outro recurso, como um dispositivo de vídeo ou uma interface de rede.

---

## 6.1 GRES: declarando GPUs

Por padrão, o Slurm gerencia CPUs e memória, porque o sistema operacional já informa esses valores. Uma GPU não é reconhecida dessa forma. O Slurm precisa que alguém declare que ela existe, qual é o nome do recurso e onde está o dispositivo.

Essa declaração é feita com um **GRES** (*Generic RESource*), um recurso genérico com nome livre. Neste tutorial, o nome escolhido é `gpu`. O nome é uma escolha de quem configura: poderia ser `acelerador` ou qualquer outro. O que importa é que o mesmo nome apareça em todos os lugares em que o recurso é mencionado.

A declaração envolve três pontos:

1. **Tipo de recurso no cluster:** `GresTypes` em `slurm.conf` registra o nome do recurso para o cluster inteiro.
2. **Quantidade por nó:** `Gres` em `slurm.conf` informa quantas unidades cada nó possui.
3. **Dispositivo físico por nó:** `gres.conf` aponta o arquivo que representa cada GPU na máquina.

### Em `slurm.conf`

```ini
GresTypes=gpu
NodeName=node01 ... Gres=gpu:1
```

- **`GresTypes=gpu`** registra o tipo. Essa linha precisa vir antes das linhas de nó. Sem ela, o Slurm não reconhece o nome `gpu`, e a linha de nó é rejeitada.
- **`Gres=gpu:1`** declara uma unidade de `gpu` no nó. O formato é `nome:quantidade`. Para duas GPUs, use `Gres=gpu:2`.

### Em `gres.conf`

```ini
NodeName=node01 Name=gpu File=/dev/nvidia0
```

- **`Name=gpu`** deve ser o mesmo nome registrado em `GresTypes`.
- **`File=/dev/nvidia0`** aponta o arquivo de dispositivo da GPU. O caminho depende do fabricante e do sistema. Em placas NVIDIA, o padrão é `/dev/nvidia0`, `/dev/nvidia1` e assim por diante. Em placas AMD, os dispositivos de renderização ficam em `/dev/dri/`. Para descobrir os arquivos disponíveis, use `ls /dev/dri` ou `ls /dev | grep nvidia`.

Se o nó tiver mais de uma GPU, cada uma ganha uma linha, ou um intervalo de nomes pode ser usado. Exemplo com duas placas NVIDIA:

```ini
NodeName=node01 Name=gpu File=/dev/nvidia[0-1]
```

### Quando o dispositivo não pode ser apontado

Em alguns casos, o dispositivo não tem um arquivo próprio que possa ser apontado, como em nós simulados (Parte 10). Nesse caso, a declaração usa `Count` em vez de `File`:

```ini
NodeName=node02 Name=gpu Count=2
```

Com `Count`, o Slurm controla a quantidade de unidades reservadas, mas não isola nenhum dispositivo real. Essa diferença tem consequências no isolamento, tratadas na seção 6.3.

### Detecção automática

O Slurm pode detectar GPUs sozinho, sem listar os arquivos de dispositivo. Para isso, `gres.conf` aceita a opção `AutoDetect`, com valores como `nvml` (NVIDIA) ou `rsmi` (AMD). Essa detecção depende de o pacote do Slurm ter sido compilado com suporte à biblioteca do fabricante. Para saber se a sua instalação tem esse suporte, consulte a documentação da versão instalada antes de usar a opção. Neste tutorial, a declaração explícita com `File` é usada, porque ela é mais fácil de verificar.

> **Referência:** SchedMD. *Generic Resource (GRES) Scheduling*. slurm.schedmd.com/gres.html. Descreve `GresTypes`, `Gres`, `gres.conf`, `File`, `Count` e `AutoDetect`.
> **Referência:** SchedMD. *gres.conf: Generic Resource configuration file*. slurm.schedmd.com/gres.conf.html. Referência das opções do arquivo.

---

## 6.2 Pedindo GPUs em um job

Com o recurso declarado, o usuário pede GPUs no momento de enviar o job. Dois formatos são comuns:

| Opção | Significado |
|---|---|
| `--gres=gpu:1` | Pede uma unidade do recurso `gpu` no nó. |
| `--gpus=1` | Pede uma GPU, em uma sintaxe mais recente que mapeia para o mesmo recurso. |

Os dois são válidos, e o resultado é o mesmo no caso simples. A opção `--gres` é mais geral, porque aceita qualquer recurso declarado. A opção `--gpus` é mais específica e mais legível para quem só usa GPUs.

Exemplo de script de job, com comentários explicativos:

```bash
#!/bin/bash
#SBATCH --job-name=teste-gpu
#SBATCH --partition=debug
#SBATCH --gres=gpu:1
#SBATCH --output=saida_%j.log

hostname
nvidia-smi -L
```

Leitura das diretivas:

- **`--job-name`** dá um nome ao job, exibido em `squeue`.
- **`--partition`** escolhe a partição (Parte 5, seção 5.3).
- **`--gres=gpu:1`** pede uma GPU. Sem essa linha, o job roda sem GPU, mesmo que o nó tenha uma.
- **`--output`** grava a saída em um arquivo. `%j` é substituído pelo número do job.

Para enviar, acompanhar e ver o resultado:

```bash
sbatch teste-gpu.sh
squeue
cat saida_<numero-do-job>.log
```

Para executar um comando diretamente, sem script, use `srun`. Ele bloqueia o terminal até o comando terminar:

```bash
srun --gres=gpu:1 nvidia-smi -L
```

Use `srun` para testes rápidos e `sbatch` para trabalhos que podem demorar. A diferença completa entre os dois aparece na Parte 9.

> **Referência:** SchedMD. *sbatch: Submit a batch script to Slurm*. slurm.schedmd.com/sbatch.html. Descreve as diretivas `#SBATCH` e as opções de recursos.
> **Referência:** SchedMD. *srun: Run parallel jobs*. slurm.schedmd.com/srun.html. Descreve a execução interativa e bloqueante.

---

## 6.3 cgroups e isolamento de dispositivos

Declarar uma GPU não impede que um job acesse GPUs que não pediu. Se os processos de um job puderem abrir qualquer arquivo de dispositivo, eles enxergarão todas as placas. O isolamento é tarefa dos **cgroups** (*control groups*), um recurso do kernel Linux que limita o que cada grupo de processos pode usar.

A configuração do Slurm para cgroups fica em `cgroup.conf`:

```ini
CgroupPlugin=autodetect
ConstrainCores=yes
ConstrainRAMSpace=yes
ConstrainDevices=yes
```

Cada opção controla um tipo de limite:

- **`CgroupPlugin=autodetect`** deixa o Slurm escolher a versão do cgroup que o kernel oferece. Sistemas recentes usam a versão 2 (cgroup v2), que é a versão unificada.
- **`ConstrainCores=yes`** limita os processos de um job aos núcleos de CPU que ele recebeu.
- **`ConstrainRAMSpace=yes`** limita a memória do job ao valor pedido. Um job que ultrapassar esse valor é encerrado pelo sistema.
- **`ConstrainDevices=yes`** limita os dispositivos de arquivo (como `/dev/nvidia0`) aos que o job recebeu. Esta é a opção que isola as GPUs.

### Verificando a versão do cgroup

Antes de depender do isolamento, confirme qual versão de cgroup o sistema usa:

```bash
stat -fc %T /sys/fs/cgroup
```

A saída `cgroup2fs` indica cgroup v2, a versão unificada. A saída `tmpfs` indica a versão antiga, que tem outro conjunto de recursos. O comando apenas lê o sistema de arquivos e não altera nada.

Para entender o que cada versão oferece, consulte a documentação do kernel (ver referências ao fim da seção).

### Como o isolamento de GPU funciona

O isolamento de dispositivos depende de a declaração ter sido feita com `File` (seção 6.1). Com `File`, o Slurm sabe exatamente qual arquivo de dispositivo corresponde a qual GPU, e o cgroup pode liberar apenas esse arquivo para o job. Com `Count`, o Slurm sabe quantas unidades foram reservadas, mas não tem o arquivo de dispositivo para liberar. Nesse caso, o isolamento de dispositivo não se aplica, e a reserva é apenas contábil.

Esse ponto é importante para a interpretação de resultados: um nó com `Count` pode parecer isolado no `sinfo`, mas o isolamento real só existe com `File`.

### Mudanças na configuração de cgroups

Alterações em `cgroup.conf` só têm efeito depois que os serviços do Slurm são reiniciados, e os jobs em andamento podem ser afetados. Por isso, a mudança deve ser feita com a fila vazia, ou com os jobs em andamento já encerrados. A reinicialização é tratada pelo playbook na Parte 8.

> **Atenção:** o arquivo `cgroup.conf` também é gerado pelo Ansible (Parte 7). Não o edite à mão.

> **Referência:** SchedMD. *cgroup.conf: Slurm cgroup support configuration file*. slurm.schedmd.com/cgroup.conf.html. Descreve as opções `ConstrainCores`, `ConstrainRAMSpace` e `ConstrainDevices`.
> **Referência:** Linux kernel. *Control Group v2*. docs.kernel.org/admin-guide/cgroup-v2.html. Documentação oficial da versão unificada dos cgroups.
> **Referência:** Heo, T. *Control Group v2*. Documentação do kernel Linux, na mesma página acima, com a motivação da versão 2. (Confirme a autoria no documento antes de citar.)

---

## Resumo da Parte 6

Ao final, você entende como uma GPU vira um recurso do Slurm, por meio de três declarações (`GresTypes`, `Gres` e `gres.conf`), e como o usuário a pede no job com `--gres` ou `--gpus`. Também entende que o isolamento real depende de cgroups e da declaração com `File`, e sabe como verificar a versão de cgroup do sistema.

Nada foi aplicado ao sistema nesta parte. Os valores reais serão gerados a partir das variáveis do projeto, na Parte 7, e o teste de isolamento completo será feito na Parte 9.

**Próxima:** Parte 7, Templates: gerando configuração a partir de variáveis.
