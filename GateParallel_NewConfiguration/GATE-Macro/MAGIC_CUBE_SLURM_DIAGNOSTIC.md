# Magic-Cube Slurm Diagnostic

## 1. Purpose

This diagnostic tests only UB CCR/Slurm scheduling access for the existing Magic-Cube Step-4 job.  It does not test or modify GATE, detector geometry, materials, or any other scientific implementation.

## 2. Prior Failure

Earlier Step-4 submission attempts reported `Unable to contact slurm controller (connect failure)`.  GATE was never executed during those attempts.

## 3. Local Slurm Environment

- Host: `cpn-d03-20.core.ccr.buffalo.edu`
- User: `kmparmar`
- `SLURM_CONF`: `/var/spool/slurmd/conf-cache/slurm.conf`
- Local allocation environment: cluster `ub-hpc`, partition `general-compute`, QOS `general-compute`, job `25688300`
- `sbatch`: `/opt/software/slurm/bin/sbatch` (`slurm 25.11.7`)
- `srun`: `/opt/software/slurm/bin/srun` (`slurm 25.11.7`)

## 4. Explicit UB-HPC Query

Command:

```text
timeout 45s sinfo -M ub-hpc
```

Result: exit code `1` without timeout.  The relevant scheduler output was:

```text
sinfo: error: _open_persist_conn: failed to open persistent connection to host:slurmctl-prod:6819: Resource temporarily unavailable
sinfo: error: DBD_GET_CLUSTERS failure: Resource temporarily unavailable
sinfo: error: There is a problem talking to the database: Resource temporarily unavailable.  Only local cluster communication is available, remove --cluster from your command line or contact your admin to resolve the problem.
sinfo: fatal: Could not get cluster information
```

Explicit `ub-hpc` query status: **FAIL**.

## 5. Partition/QOS

- `general-compute` partition: **UNKNOWN** through an explicit `-M ub-hpc` query; the query failed before returning partition information.
- `general-compute` QOS: **UNKNOWN** through an explicit `-M ub-hpc` query; no QOS lookup was run after the fail-fast query failure.

The current local allocation environment reports these values, but that does not prove that explicit cluster submission is available from this session.

## 6. Tiny Allocation Probe

Not executed.  The required explicit cluster query failed, so no probe script was created and no job was submitted.

## 7. Step-4 Header Change

Modified: **NO**.  `magiccube_step4_job.sh` was not inspected or changed because scheduler connectivity/allocation was not proven.

## 8. Conclusion

**UB_HPC_QUERY_FAILED**

The explicit controller/database path for `sinfo -M ub-hpc` was unavailable from this session.  No claim is made about Magic-Cube runtime behavior.
