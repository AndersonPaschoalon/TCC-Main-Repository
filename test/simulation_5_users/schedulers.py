"""
Os tres escalonadores usados no experimento de 5 usuarios (five_user_demo.py).

1. spt_schedule        -> Shortest Processing Time First. Extensao (list
   scheduling) do Problema 16-2 de Cormen et al. para N GPUs identicas:
   a cada passo de tempo, roda o job de MENOR duracao que couber nas GPUs
   livres. E o limite teorico de eficiencia (nao tem compromisso nenhum
   com equidade entre usuarios).

2. fcfs_schedule       -> fila ingenua, estritamente por ordem de
   chegada, bloqueante. Representa o limite teorico superior de um
   laboratorio SEM nenhum escalonador.

3. slurm_like_schedule -> simulacao simplificada do Slurm: prioridade
   multifator (idade + fairshare + tamanho do job) + heuristica de
   backfill. NAO e o Slurm real -- e uma aproximacao didatica.
"""


def spt_schedule(jobs, total_gpus):
    """
    A cada passo de tempo, entre os jobs ja chegados e ainda nao rodados,
    roda o de MENOR duracao que couber nas GPUs livres. Respeitar a ordem
    real de chegada e a disputa por GPU e essencial para o resultado
    fazer sentido (um list scheduling estatico, ordenado so por duracao
    sem respeitar a chegada, distorce o resultado).
    """
    remaining = sorted(jobs, key=lambda j: j["arrival_time"])
    gpu_free_at = [0.0] * total_gpus
    results = []
    t = 0.0

    while remaining:
        t = max(t, min(j["arrival_time"] for j in remaining))
        ready = [j for j in remaining if j["arrival_time"] <= t]
        ready.sort(key=lambda j: j["duration"])  # SPT: mais curto primeiro

        free_slots = [i for i in range(total_gpus) if gpu_free_at[i] <= t]
        progressed = False
        for job in ready:
            needed = job["gpu_required"]
            if len(free_slots) >= needed:
                chosen = free_slots[:needed]
                free_slots = free_slots[needed:]
                finish = t + job["duration"]
                for i in chosen:
                    gpu_free_at[i] = finish
                results.append(_job_result(job, t, finish))
                remaining.remove(job)
                progressed = True

        if not progressed:
            future_times = [j["arrival_time"] for j in remaining if j["arrival_time"] > t]
            future_times += [f for f in gpu_free_at if f > t]
            t = min(future_times) if future_times else t + 1

    return results


def fcfs_schedule(jobs, total_gpus):
    """
    jobs: lista de dicts com job_id, user_id, arrival_time, duration,
    gpu_required. Ordem estrita de chegada; so avanca para o proximo job
    quando ha GPUs livres suficientes.
    """
    jobs_sorted = sorted(jobs, key=lambda j: j["arrival_time"])
    gpu_free_at = [0.0] * total_gpus
    results = []
    for job in jobs_sorted:
        needed = job["gpu_required"]
        slot_indices = sorted(range(total_gpus), key=lambda i: gpu_free_at[i])[:needed]
        start = max(job["arrival_time"], max(gpu_free_at[i] for i in slot_indices))
        finish = start + job["duration"]
        for i in slot_indices:
            gpu_free_at[i] = finish
        results.append(_job_result(job, start, finish))
    return results


def _priority(job, now, max_wait, w_age=0.3, w_fair=0.5, w_size=0.2):
    age_factor = min((now - job["arrival_time"]) / max_wait, 1.0) if max_wait > 0 else 0.0
    fairshare_factor = 1.0 - job["user_fairshare_score"]  # menos uso recente -> mais prioridade
    size_factor = 1.0 - min(job["gpu_required"] / 4.0, 1.0)  # jobs menores sobem um pouco
    return w_age * age_factor + w_fair * fairshare_factor + w_size * size_factor


def slurm_like_schedule(jobs, total_gpus):
    """
    Lista de prontidao ordenada por prioridade a cada passo de tempo;
    preenche GPUs ociosas com o job de maior prioridade que couber
    (efeito equivalente a um backfill simples).
    """
    gpu_free_at = [0.0] * total_gpus
    results = []
    t = 0.0
    total_gpu_time = sum(j["duration"] * j["gpu_required"] for j in jobs)
    max_wait = max(total_gpu_time / total_gpus, 1.0)

    remaining = sorted(jobs, key=lambda j: j["arrival_time"])

    while remaining:
        t = max(t, min(j["arrival_time"] for j in remaining))
        ready = [j for j in remaining if j["arrival_time"] <= t]
        ready.sort(key=lambda j: _priority(j, t, max_wait), reverse=True)

        free_slots = [i for i in range(total_gpus) if gpu_free_at[i] <= t]
        progressed = False
        for job in ready:
            needed = job["gpu_required"]
            if len(free_slots) >= needed:
                chosen = free_slots[:needed]
                free_slots = free_slots[needed:]
                finish = t + job["duration"]
                for i in chosen:
                    gpu_free_at[i] = finish
                results.append(_job_result(job, t, finish))
                remaining.remove(job)
                progressed = True

        if not progressed:
            future_times = [j["arrival_time"] for j in remaining if j["arrival_time"] > t]
            future_times += [f for f in gpu_free_at if f > t]
            t = min(future_times) if future_times else t + 1

    return results


def _job_result(job, start, finish):
    return {
        "job_id": job["job_id"],
        "user_id": job.get("user_id", "?"),
        "arrival_time": job["arrival_time"],
        "start": start,
        "finish": finish,
        "wait": start - job["arrival_time"],
        "duration": job["duration"],
        "gpu_required": job["gpu_required"],
    }


def totals_by_user(results):
    """Soma o wait de cada job por user_id -- a unidade de analise de equidade."""
    by_user = {}
    for r in results:
        u = r.get("user_id", "?")
        by_user[u] = by_user.get(u, 0) + r["wait"]
    return by_user
