# Parte 11: Solução de problemas

**Objetivo desta parte:** organizar o diagnóstico de falhas em um método que funciona para qualquer sintoma: observar, localizar a camada responsável, ler a mensagem de erro e corrigir a fonte.

**Pré-requisito:** Partes 3 a 10 lidas. Para os exemplos de log, o cluster precisa ter pelo menos um serviço em execução ou falhando.

**Esta parte não altera a configuração por si só.** Os comandos de diagnóstico são de leitura. As correções indicadas devem ser aplicadas pela fonte, seguindo o fluxo da seção 8.4.

---

## 11.1 Tabela de sintomas e causas

Quase todo problema do cluster se encaixa em uma das camadas que a apostila já percorreu: o hardware e o driver, a autenticação, a configuração gerada, os serviços, ou a execução de jobs. A tabela abaixo começa pelo sintoma observado e aponta a camada provável, com a forma de confirmar a causa.

| Sintoma | Camada provável | Como confirmar | Correção |
|---|---|---|---|
| `nvidia-smi` não responde, ou o módulo não aparece em `lsmod` | Driver | `lsmod` e `dmesg \| grep -i nvidia` | Instalar o driver recomendado, ou tratar o Secure Boot (Parte 2) |
| Nó aparece como `down` ou `unk` em `sinfo` | Comunicação ou configuração | `scontrol show node <nome>`, campo `Reason` | Ver as linhas seguintes deste quadro |
| Nó `down` com motivo de hardware | Declaração de recursos | Comparar `CPUTot` e `RealMemory` com `slurmd -C` | Ajustar `cpus` e `real_memory` no inventário, com o valor de `slurmd -C` |
| `slurmctld` não inicia | Configuração do controlador | `journalctl -u slurmctld -n 50` | Confirmar que `SlurmctldHost` é o hostname real da máquina |
| `slurmd` não inicia | Autenticação ou configuração | `journalctl -u slurmd -n 50` e `munge -n \| unmunge` | Corrigir a chave ou o relógio (linhas seguintes) e rodar o playbook de novo |
| `Invalid credential` ou erro de munge | Chave ou relógio | `md5sum /etc/munge/munge.key` nas máquinas e `date` em cada uma | Distribuir a mesma chave e sincronizar o horário com NTP |
| Job fica pendente com motivo `Resources` | Capacidade | `squeue` e `scontrol show job <numero>` | Esperar ou cancelar jobs anteriores, ou reduzir o pedido |
| Job fica pendente com motivo `ReqNodeNotAvail` | Estado do nó | `sinfo -N -l` | Corrigir o nó indisponível antes de reenviar o job |
| `--gres=gpu:1` é rejeitado na submissão | Declaração de GRES | Conferir `GresTypes` e `Gres=` em `slurm.conf` | Declarar `GresTypes=gpu` antes das linhas de nó |
| Job roda, mas a GPU não aparece | Dispositivo | `nvidia-smi -L` dentro do job, e `File=` em `gres.conf` | Apontar o caminho correto do dispositivo |
| Job sem `--gres` enxerga a GPU | Isolamento | Teste negativo da seção 9.3 | Usar `File=` em vez de `Count=`, confirmar `ConstrainDevices=yes` e reiniciar `slurmd` |
| `sacct` informa que o histórico está desativado | Accounting | `grep Accounting /etc/slurm/slurm.conf` | Confirmar `AccountingStorageType` e que `slurmdbd` está ativo |
| Playbook sempre mostra `changed` | Idempotência | Repetir `--check --diff` e ler o item que muda | Substituir `command` ou `shell` por um módulo específico |
| Erro `the requested handler could not be found` | Nome de handler | Comparar `notify` com o nome em `handlers/main.yml` | Corrigir o nome para coincidir exatamente |
| Erro de sintaxe em um template | Jinja2 | A mensagem indica o arquivo e a linha | Corrigir a marcação, usando `--check --diff` para validar |
| `Permission denied` em `/var/spool` ou `/etc/slurm` | Dono ou permissão | `ls -ld <caminho>` | Ajustar `owner`, `group` e `mode` na tarefa de criação |
| Nó virtual não inicia | Porta ou spool | `journalctl -u slurmd-<nome> -n 50` | Confirmar porta distinta e diretório de spool próprio (Parte 10) |

Duas observações sobre a tabela:

- **A ordem importa.** Se o driver não responde, nada acima dele funciona. Se o munge falha, o Slurm falha por consequência. Corrija a camada mais baixa primeiro.
- **A causa aparece antes do sintoma.** Um erro de configuração geralmente se manifesta depois, em um serviço ou em um job. Quando o sintoma não bate com a tabela, volte uma camada e observe a anterior.

> **Referência:** SchedMD. *Slurm Troubleshooting Guide*. slurm.schedmd.com. Diagnóstico de nós, jobs e serviços.

---

## 11.2 Como ler logs (`journalctl` e logs do Slurm)

Um log registra o que um programa fez e os erros que encontrou. Quando algo falha, a mensagem de erro costuma estar no log, e não na tela. Há duas fontes de log neste cluster.

### O journal do systemd

Todos os serviços da apostila (`munge`, `slurmctld`, `slurmd`, `slurmdbd` e os nós virtuais) são gerenciados pelo systemd, que guarda os registros no **journal**. O comando `journalctl` lê esse registro.

Para ver as últimas linhas de um serviço:

```bash
journalctl -u slurmctld -n 50 --no-pager
```

Para ver o que aconteceu desde um momento específico:

```bash
journalctl -u slurmd --since "10 minutes ago" --no-pager
```

Para acompanhar um serviço em tempo real, enquanto você reproduz o problema em outro terminal:

```bash
journalctl -u slurmd -f
```

A opção `-f` continua exibindo as novas linhas até você pressionar `Ctrl+C`.

### Os logs do próprio Slurm

O Slurm também pode gravar logs em arquivos próprios, indicados em `slurm.conf` pelas opções `SlurmctldLogFile` e `SlurmdLogFile`. Se essas opções não estiverem definidas, as mensagens vão para o journal, e a seção anterior basta.

Para descobrir onde o Slurm está gravando, consulte a configuração em uso:

```bash
scontrol show config | grep -i logfile
```

O nível de detalhe das mensagens é controlado pela opção `SlurmctldDebug` e `SlurmdDebug`, e pode ser aumentado temporariamente. Para diagnóstico pontual, o modo de primeiro plano apresentado na Parte 5 (`-D -vvv`) costuma ser mais útil do que mudar o nível do serviço.

### Como ler uma mensagem de erro

Uma mensagem de erro tem quatro partes que merecem atenção:

1. **O nome do componente** (`slurmctld`, `slurmd`, `munge`). Ele indica a camada.
2. **O tipo de erro** (`error`, `fatal`, `warning`). `fatal` encerra o processo, e `warning` costuma ser inofensivo, a menos que se repita.
3. **O objeto afetado** (um nó, um arquivo, um job). Ele indica onde procurar.
4. **O texto da causa**, geralmente no fim da linha.

Ao procurar uma mensagem em um log extenso, filtre pelo tipo de erro:

```bash
journalctl -u slurmctld --no-pager | grep -iE "error|fatal"
```

Leia a primeira mensagem de erro de uma sequência, e não a última. As mensagens seguintes costumam ser consequência da primeira.

### Logs do Ansible

Quando o problema está na execução do playbook, a própria saída do Ansible é o log. Para mais detalhes, aumente o nível de verbosidade com `-v`, `-vv` ou `-vvv`:

```bash
ansible-playbook site.yml -K -vvv
```

A opção `--diff` mostra o conteúdo gerado, e é a forma mais rápida de comparar o que deveria ser com o que está no sistema.

> **Referência:** systemd. *journalctl(1)*. freedesktop.org. Opções de filtro por unidade, tempo e prioridade.
> **Referência:** SchedMD. *slurm.conf: SlurmctldLogFile, SlurmdLogFile, SlurmctldDebug, SlurmdDebug*. slurm.schedmd.com. Configuração de logs e níveis de detalhe.
> **Referência:** Ansible. *Debugging Ansible playbooks*. docs.ansible.com. Verbosidade e `--diff`.

---

## 11.3 Hábitos de depuração

A tabela e os logs resolvem a maioria dos problemas. Os hábitos abaixo resolvem o resto, e evitam que um problema pequeno vire um problema maior.

**Mude uma coisa por vez.** Quando várias alterações são feitas juntas, não se sabe qual delas causou o efeito, nem qual corrigiu o problema. Aplique uma mudança, rode a verificação, e só então passe para a próxima.

**Reproduza antes de corrigir.** Um problema que você não consegue provocar de novo não pode ser confirmado como resolvido. Anote o comando exato que falha, para repeti-lo depois da correção.

**Corrija a fonte, nunca o resultado.** Se um arquivo gerado está errado, a causa está no template ou nas variáveis. Editar o arquivo gerado resolve o sintoma por um instante e o desfaz na execução seguinte (seção 7.4).

**Compare o esperado com o real.** O `--check --diff` mostra a diferença entre o que o template produziria e o que está no sistema. Essa comparação encontra a maior parte dos desvios de configuração.

**Confirme o hardware antes de culpar o software.** Muitos erros de nó são declarações de recursos maiores que a máquina. Compare sempre com `slurmd -C`, `nproc` e `free -m`.

**Mantenha o histórico.** Se o projeto está sob controle de versão, uma mudança que quebrou o cluster pode ser desfeita com um comando. Sem histórico, o caminho de volta depende da memória.

**Feche o ciclo.** Depois de corrigir, rode a validação completa da Parte 9, e não apenas o comando que falhava. Um conserto pode quebrar outra parte do cluster.

**Registre o que aconteceu.** Uma nota curta com o sintoma, a causa e a correção evita repetir a investigação. Ela também é útil para quem vier depois.

> **Referência:** Zeller, A. *Why Programs Fail: A Guide to Systematic Debugging*. Morgan Kaufmann. Método sistemático de depuração, da reprodução à isolação da causa. (Verifique a edição antes de citar.)

---

## Resumo da Parte 11

Ao final, você tem um método de diagnóstico: observar o sintoma, localizar a camada, ler a primeira mensagem de erro nos logs e corrigir a fonte. A tabela de sintomas cobre os casos mais comuns, e os hábitos de depuração cobrem o restante.

**Próxima:** Parte 12, Conclusão.
