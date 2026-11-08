# Parte 9: Validação do cluster

**Objetivo desta parte:** confirmar, com os comandos do próprio Slurm, que o controlador enxerga os nós, que os nós estão disponíveis, que um job é aceito e executado, e que o job recebe apenas as GPUs que pediu.

**Pré-requisito:** Partes 3 a 8 concluídas e aplicadas. O playbook termina com `failed=0`, e a segunda execução mostra `changed=0`.

**Esta parte não altera a configuração.** Os comandos consultam o estado do cluster e enviam jobs de teste. Os jobs de teste são curtos e não modificam o sistema.

---

## 9.1 `sinfo`, `scontrol show node` e `squeue`

Três comandos mostram o estado do cluster, cada um com um foco diferente:

| Comando | Pergunta que responde |
|---|---|
| `sinfo` | Quais partições e nós existem, e em qual estado estão? |
| `scontrol show node <nome>` | Quais recursos esse nó declara, e por que ele está no estado atual? |
| `squeue` | Quais jobs estão na fila ou em execução? |

### `sinfo`: visão geral

```bash
sinfo
```

Saída ilustrativa, com um nó:

```
PARTITION AVAIL  TIMELIMIT  NODES  STATE NODELIST
debug*       up   infinite      1   idle node01
```

Leitura:

- **`PARTITION`** é o nome da partição. O asterisco indica a partição padrão.
- **`AVAIL`** mostra se a partição aceita jobs. `up` significa que aceita.
- **`NODES`** é a quantidade de nós nesse estado.
- **`STATE`** é o estado dos nós. O estado esperado é `idle`, que significa disponível e sem jobs.
- **`NODELIST`** lista os nós.

Para ver um nó por linha, com mais detalhes:

```bash
sinfo -N -l
```

### Estados mais comuns

| Estado | Significado |
|---|---|
| `idle` | Disponível e sem jobs. É o estado desejado após a configuração. |
| `alloc` | Totalmente alocado a jobs. |
| `mix` | Parcialmente alocado. Parte dos recursos está livre. |
| `down` | Indisponível. O controlador não consegue se comunicar com o `slurmd`, ou a configuração declarada não corresponde ao hardware. |
| `drain` | Retirado de uso pelo administrador. Não recebe novos jobs, mas os atuais continuam. |
| `unk` ou `UNKNOWN` | Estado inicial. O controlador ainda não recebeu resposta do nó. |

Se o nó aparecer como `down` ou `unk` logo após a aplicação, espere alguns segundos e consulte de novo. O `slurmd` pode ainda estar se registrando. Se o estado persistir, o motivo está registrado no próprio nó, como mostrado a seguir.

### `scontrol show node`: detalhes de um nó

```bash
scontrol show node node01
```

Saída ilustrativa, resumida:

```
NodeName=node01 Arch=x86_64 CoresPerSocket=4
   CPUAlloc=0 CPUTot=8 CPULoad=0.02
   Gres=gpu:1
   RealMemory=7800 AllocMem=0
   State=IDLE ThreadsPerCore=2
   Reason=Not responding [slurm@2026-01-01T10:00:00]
```

Os campos que importam nesta etapa são:

- **`CPUTot`** deve corresponder ao valor declarado em `cpus` (Parte 3).
- **`RealMemory`** deve corresponder ao valor declarado em `real_memory`.
- **`Gres`** deve mostrar `gpu:1` se o nó tem uma GPU declarada (Parte 6).
- **`State`** deve ser `IDLE`.
- **`Reason`** aparece apenas quando o nó está em estado anômalo, e explica o motivo.

Se `CPUTot` ou `RealMemory` não baterem com o que foi declarado, o Slurm ignorou a declaração ou o nó foi rejeitado. Verifique o valor de `slurmd -C` (Parte 4) e a configuração gerada.

Quando um nó está em `DOWN` ou `DRAIN` por um motivo já resolvido, o administrador pode devolvê-lo ao serviço. Esse comando altera o estado e exige privilégio:

```bash
sudo scontrol update nodename=node01 state=resume
```

Use esse comando apenas depois de entender por que o nó saiu de serviço. Devolver um nó com problema real faz jobs falharem.

### `squeue`: a fila

```bash
squeue
```

Saída ilustrativa, sem jobs:

```
             JOBID PARTITION     NAME     USER ST       TIME  NODES NODELIST(REASON)
```

Um cabeçalho sem linhas abaixo significa fila vazia, que é o estado esperado neste ponto. Os campos mais importantes são `ST` (o estado do job, como `PD` para pendente e `R` para em execução) e `NODELIST(REASON)`, que mostra o nó onde o job roda ou o motivo de estar parado.

> **Referência:** SchedMD. *sinfo: View information about Slurm nodes and partitions*. slurm.schedmd.com/sinfo.html. Campos de saída e estados de nós.
> **Referência:** SchedMD. *scontrol: View or modify Slurm configuration and state*. slurm.schedmd.com/scontrol.html. Comandos `show node` e `update`.
> **Referência:** SchedMD. *squeue: View information about jobs in the scheduling queue*. slurm.schedmd.com/squeue.html. Campos e estados de jobs.

---

## 9.2 Primeiro job: `srun` e `sbatch`

O Slurm oferece duas formas de executar um job, com comportamentos diferentes.

| Comando | Comportamento | Quando usar |
|---|---|---|
| `srun` | Executa imediatamente, bloqueia o terminal até terminar, e mostra a saída na tela. | Testes rápidos e comandos curtos. |
| `sbatch` | Coloca o job na fila e devolve o controle ao terminal. A saída vai para um arquivo. | Trabalhos que podem demorar, ou que devem sobreviver ao fechamento do terminal. |

### Teste com `srun`

```bash
srun hostname
```

Saída esperada: o nome da máquina, impresso no terminal. Se o comando ficar esperando indefinidamente, verifique com `squeue` se o job está pendente e o motivo. Um job pendente com motivo `Resources` significa que não há recursos livres. Um motivo como `ReqNodeNotAvail` indica que o nó não está disponível, e o estado do nó deve ser investigado com `scontrol show node`.

### Teste com `sbatch`

Crie o arquivo `teste-basico.sh`:

```bash
#!/bin/bash
#SBATCH --job-name=teste-basico
#SBATCH --output=saida_%j.log

echo "Executando em: $(hostname)"
echo "Data: $(date)"
```

Envie o job:

```bash
sbatch teste-basico.sh
```

A saída do comando mostra o número do job:

```
Submitted batch job 1
```

O número varia. Acompanhe com `squeue` até o job sumir da fila, o que indica término. Depois, leia o arquivo de saída, substituindo `<numero>` pelo número mostrado:

```bash
cat saida_<numero>.log
```

O arquivo deve conter o nome da máquina e a data. Se o job terminou sem gerar o arquivo, o problema está quase sempre no caminho do `--output` ou em permissões do diretório onde o `sbatch` foi executado.

### Cancelando um job

Um job pode ser cancelado enquanto está na fila ou em execução:

```bash
scancel <numero>
```

Use `squeue` antes para confirmar o número. O cancelamento de um job não afeta os outros.

> **Referência:** SchedMD. *srun: Run parallel jobs*. slurm.schedmd.com/srun.html. Execução interativa e bloqueante.
> **Referência:** SchedMD. *sbatch: Submit a batch script to Slurm*. slurm.schedmd.com/sbatch.html. Diretivas `#SBATCH` e o arquivo de saída.
> **Referência:** SchedMD. *scancel: Signal or cancel jobs, job arrays, or job steps*. slurm.schedmd.com/scancel.html.

---

## 9.3 Verificando a GPU dentro de um job

Até aqui, o Slurm confirmou que o nó existe e que o job executa. Falta confirmar o ponto central da configuração: o job recebe a GPU que pediu, e somente ela.

### Teste positivo: o job vê a GPU pedida

```bash
srun --gres=gpu:1 nvidia-smi -L
```

Saída esperada, ilustrativa:

```
GPU 0: NVIDIA ... (UUID: GPU-...)
```

O comando lista uma GPU. Se a máquina tiver mais de uma, o job recebe apenas a quantidade pedida em `--gres`.

Para placas de outros fabricantes, substitua a ferramenta pela equivalente (`rocm-smi` para AMD). A ideia do teste é a mesma: a ferramenta do fabricante, executada dentro do job, lista as GPUs visíveis para ele.

### Teste negativo: o job sem GPU não a enxerga

Este é o teste que demonstra o isolamento. Execute o mesmo comando sem pedir GPU:

```bash
srun nvidia-smi -L
```

Com `ConstrainDevices=yes` (Parte 6), o job não tem acesso ao dispositivo, e a ferramenta deve falhar ou reportar que não encontrou GPUs. A mensagem exata depende da versão do driver, mas o resultado esperado é o mesmo: nenhuma GPU listada.

Se o comando sem `--gres` listar a GPU normalmente, o isolamento não está funcionando. Os motivos mais comuns são:

- o nó foi declarado com `Count` em vez de `File` (Parte 6, seção 6.3), o que impede o isolamento de dispositivo;
- `cgroup.conf` não contém `ConstrainDevices=yes`;
- o `slurmd` não foi reiniciado depois da mudança de `cgroup.conf`.

Verifique cada um, na ordem, antes de considerar o problema resolvido.

### Teste de consistência: o que o Slurm declarou

Para confirmar que o Slurm alocou a GPU que o job pediu, consulte o job enquanto ele está em execução. Use um job que dure alguns segundos:

```bash
sbatch --gres=gpu:1 --wrap="sleep 30"
squeue
scontrol show job <numero>
```

A linha `Gres=gpu:1` no campo de alocação mostra que o job recebeu uma GPU. Essa informação vem do controlador, e complementa o teste com `nvidia-smi`, que vem da própria máquina.

A opção `--wrap` permite enviar um comando direto, sem criar um arquivo de script. É útil para testes rápidos com `sbatch`.

### Histórico de jobs

Para consultar jobs já terminados, o comando `sacct` é usado. Nesta etapa, o histórico ainda não está ativo, porque o armazenamento de contabilidade foi desligado na configuração. Se você executar:

```bash
sacct
```

a mensagem indicará que o armazenamento de histórico está desativado. Esse comportamento é esperado. O histórico é habilitado na Parte 10.

> **Referência:** NVIDIA. *nvidia-smi: NVIDIA System Management Interface*. Guia do usuário, docs.nvidia.com. Opção `-L` para listar dispositivos.
> **Referência:** SchedMD. *Generic Resource (GRES) Scheduling*. slurm.schedmd.com/gres.html. Como o Slurm aloca recursos genéricos a jobs.

---

## Resumo da Parte 9

Ao final, você confirmou quatro pontos com o próprio Slurm: o controlador enxerga o nó, o nó está em `idle` com os recursos declarados, um job executa com `srun` e com `sbatch`, e o job recebe apenas as GPUs que pediu. O teste negativo, sem `--gres`, é a prova de que o isolamento por cgroups funciona.

Se algum teste falhar, a Parte 11 reúne os sintomas mais comuns e a forma de diagnosticar cada um.

**Próxima:** Parte 10, Expansão.
