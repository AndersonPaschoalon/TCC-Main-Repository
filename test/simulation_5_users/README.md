# five-user-demo

Exercício mockado mínimo: 5 usuários (2 "gulosos", 3 "magros"), 3 regimes
de escalonamento sobre os mesmos jobs — SPT (limite teórico inferior),
Slurm simulado (fair-share + backfill), e FCFS (limite teórico superior,
inferido sobre os mesmos jobs).

## Rodar

```
./run.sh
```

Cria um venv, instala a única dependência (matplotlib) e roda o
experimento. Gera `five_user_gantt.png`, `five_user_wait_by_user.png`
e `five_user_fairness_by_group.png`.

## Arquivos
- `schedulers.py` — as três implementações de escalonador
- `five_user_demo.py` — gera os jobs, roda os três regimes, plota
- `pyproject.toml` / `run.sh` — ambiente e execução
