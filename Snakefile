import glob
import os

configfile: "configs/config.yaml"

P = config["polarizations"]
N_JOBS = int(config["splitting"]["nJobs"])
EVENTS_PER_JOB = int(config["splitting"]["eventsPerJob"])
JOBS = [f"{i:04d}" for i in range(N_JOBS)]

# Bulky outputs can live outside the repo (e.g. on EOS); job options and
# MCValidation always stay in the repo.
STORAGE = config["paths"].get("storage_base", "") or ""
def out_dir(d):
    return os.path.join(STORAGE, d) if STORAGE else d

JO_DIR = config["paths"]["generation_dir"]
GEN_DIR = out_dir(config["paths"]["generation_dir"])
DER_DIR = out_dir(config["paths"]["derivation_dir"])
SIM_DIR = out_dir(config["paths"]["simulation_dir"])
DIGI_DIR = out_dir(config["paths"]["digitization_dir"])
RECO_DIR = out_dir(config["paths"]["reconstruction_dir"])
JO_SUBDIR = config["paths"]["jobconfig_subdir"]
VAL_DIR = config["paths"]["validation_dir"]

ALRB_BASE = "/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase"
ALRB_SETUP = f"{ALRB_BASE}/user/atlasLocalSetup.sh"

def alrb_container_run(payload_path):
    # Runs a payload script inside an el9 apptainer (matches the OS the
    # CVMFS-provided ATLAS releases are built/tested against), avoiding
    # host-vs-EL9 library mismatches (glibc layout, ICU version, etc).
    # $PWD is bind-mounted to /srv and is also the container's default cwd,
    # so host-relative paths keep working unchanged inside the payload.
    # With container: none the payload runs natively (EL9 hosts only).
    if config.get("container", "el9") == "none":
        return f'export ATLAS_LOCAL_ROOT_BASE={ALRB_BASE}; source {ALRB_SETUP} -q; source {payload_path}'
    mounts = f"-m {STORAGE}" if os.path.isabs(STORAGE) else ""
    return f'export ATLAS_LOCAL_ROOT_BASE={ALRB_BASE}; source {ALRB_SETUP} -c el9 {mounts} -q -r "source {payload_path}"'

def res(rule_name):
    return config["resources"][rule_name]

def rel_to(paths, d):
    # Payloads cd into their job directory, so repo-relative inputs are
    # rewritten relative to it; absolute (e.g. EOS) paths pass through.
    return ",".join(p if os.path.isabs(p) else os.path.relpath(p, d) for p in paths)

def mt_flags(threads):
    return f"--multithreaded=True" if threads > 1 else ""

wildcard_constraints:
    p = r"[A-Za-z0-9]+",
    j = r"\d{4}"

localrules: all, daod_files, daod_phys

rule all:
    input:
        expand(
            [
                f"{VAL_DIR}/run/{{p}}_ttbar/hist-{{p}}_ttbar.root",
                f"{DER_DIR}/{{p}}_ttbar_PHYS/DAOD_PHYS.mcval.pool.root",
            ],
            p=P
        )

# Wildcard-free targets so DAOD production can be requested directly,
# e.g. `snakemake --cores 16 daod_files` (TRUTH3 from EVNT, fast) or
# `snakemake --cores 16 daod_phys` (full sim/digi/reco chain, slow).
rule daod_files:
    input:
        expand(f"{DER_DIR}/{{p}}_ttbar/job{{j}}/DAOD_{{fmt}}.mcval.pool.root", p=P, j=JOBS, fmt=["TRUTH1", "TRUTH3"])

rule daod_phys:
    input:
        expand(f"{DER_DIR}/{{p}}_ttbar_PHYS/DAOD_PHYS.mcval.pool.root", p=P)

rule generateEvgen:
    input:
        f"{JO_DIR}/mc.MGPy8EG_A14_NNPDF23LO_SM_{{p}}_ttbar.py"
    output:
        f"{GEN_DIR}/{{p}}_ttbar/job{{j}}/evgen.root"
    params:
        dir=lambda w: f"{GEN_DIR}/{w.p}_ttbar/job{w.j}",
        seed=lambda w: int(config["generation"]["randomSeed"]) + int(w.j),
        first=lambda w: int(w.j) * EVENTS_PER_JOB + 1
    threads: res("generateEvgen")["threads"]
    resources:
        mem_mb=res("generateEvgen")["mem_mb"],
        runtime=res("generateEvgen")["runtime"]
    shell:
        f"""
        set +eu
        rm -rf {{params.dir}}
        mkdir -p {{params.dir}}/{JO_SUBDIR}
        cp {{input}} {{params.dir}}/{JO_SUBDIR}
        cat > {{params.dir}}/.alrb_payload.sh << 'EOF'
        cd {{params.dir}}
        asetup {config["generation"]["asetupRelease"]}
        export ATHENA_PROC_NUMBER={{threads}}
        Gen_tf.py --ecmEnergy={config["generation"]["ecmEnergy"]} --maxEvents={EVENTS_PER_JOB} --firstEvent={{params.first}} --randomSeed={{params.seed}} --outputEVNTFile=evgen.root --jobConfig={JO_SUBDIR}
EOF
        {alrb_container_run("{params.dir}/.alrb_payload.sh")}
        """

rule derivation:
    input:
        f"{GEN_DIR}/{{p}}_ttbar/job{{j}}/evgen.root"
    output:
        # TRUTH1 (full truth record) feeds MCValidation; TRUTH3 is kept alongside
        f"{DER_DIR}/{{p}}_ttbar/job{{j}}/DAOD_TRUTH1.mcval.pool.root",
        f"{DER_DIR}/{{p}}_ttbar/job{{j}}/DAOD_TRUTH3.mcval.pool.root"
    params:
        dir=lambda w: f"{DER_DIR}/{w.p}_ttbar/job{w.j}",
        inp=lambda w, input: rel_to(input, f"{DER_DIR}/{w.p}_ttbar/job{w.j}")
    threads: res("derivation")["threads"]
    resources:
        mem_mb=res("derivation")["mem_mb"],
        runtime=res("derivation")["runtime"]
    shell:
        f"""
        set +eu
        rm -rf {{params.dir}}
        mkdir -p {{params.dir}}
        cat > {{params.dir}}/.alrb_payload.sh << 'EOF'
        cd {{params.dir}}
        asetup {config["derivation"]["asetupRelease"]}
        Derivation_tf.py --inputEVNTFile={{params.inp}} --outputDAODFile=mcval.pool.root --formats TRUTH1 TRUTH3
EOF
        {alrb_container_run("{params.dir}/.alrb_payload.sh")}
        """

rule simulation:
    input:
        f"{GEN_DIR}/{{p}}_ttbar/job{{j}}/evgen.root"
    output:
        f"{SIM_DIR}/{{p}}_ttbar/job{{j}}/HITS.pool.root"
    params:
        dir=lambda w: f"{SIM_DIR}/{w.p}_ttbar/job{w.j}",
        inp=lambda w, input: rel_to(input, f"{SIM_DIR}/{w.p}_ttbar/job{w.j}"),
        mt=lambda w, threads: mt_flags(threads)
    threads: res("simulation")["threads"]
    resources:
        mem_mb=res("simulation")["mem_mb"],
        runtime=res("simulation")["runtime"]
    shell:
        f"""
        set +eu
        rm -rf {{params.dir}}
        mkdir -p {{params.dir}}
        cat > {{params.dir}}/.alrb_payload.sh << 'EOF'
        cd {{params.dir}}
        asetup {config["simulation"]["asetupRelease"]}
        export ATHENA_CORE_NUMBER={{threads}}
        Sim_tf.py {{params.mt}} --inputEVNTFile={{params.inp}} --outputHITSFile=HITS.pool.root --conditionsTag={config["simulation"]["conditionsTag"]} --geometryVersion={config["simulation"]["geometryVersion"]} --simulator={config["simulation"]["simulator"]} --physicsList={config["simulation"]["physicsList"]} --preInclude 'EVNTtoHITS:Campaigns/MC23SimulationSingleIoV.py'
EOF
        {alrb_container_run("{params.dir}/.alrb_payload.sh")}
        """

rule digitization:
    input:
        f"{SIM_DIR}/{{p}}_ttbar/job{{j}}/HITS.pool.root"
    output:
        f"{DIGI_DIR}/{{p}}_ttbar/job{{j}}/RDO.pool.root"
    params:
        dir=lambda w: f"{DIGI_DIR}/{w.p}_ttbar/job{w.j}",
        inp=lambda w, input: rel_to(input, f"{DIGI_DIR}/{w.p}_ttbar/job{w.j}")
    threads: res("digitization")["threads"]
    resources:
        mem_mb=res("digitization")["mem_mb"],
        runtime=res("digitization")["runtime"]
    shell:
        f"""
        set +eu
        rm -rf {{params.dir}}
        mkdir -p {{params.dir}}
        cat > {{params.dir}}/.alrb_payload.sh << 'EOF'
        cd {{params.dir}}
        asetup {config["digitization"]["asetupRelease"]}
        Digi_tf.py --inputHITSFile={{params.inp}} --outputRDOFile=RDO.pool.root --conditionsTag={config["simulation"]["conditionsTag"]} --geometryVersion={config["simulation"]["geometryVersion"]} --digiSteeringConf='StandardSignalOnlyTruth'
EOF
        {alrb_container_run("{params.dir}/.alrb_payload.sh")}
        """

rule reconstruction:
    input:
        f"{DIGI_DIR}/{{p}}_ttbar/job{{j}}/RDO.pool.root"
    output:
        f"{RECO_DIR}/{{p}}_ttbar/job{{j}}/AOD.pool.root"
    params:
        dir=lambda w: f"{RECO_DIR}/{w.p}_ttbar/job{w.j}",
        inp=lambda w, input: rel_to(input, f"{RECO_DIR}/{w.p}_ttbar/job{w.j}"),
        mt=lambda w, threads: mt_flags(threads)
    threads: res("reconstruction")["threads"]
    resources:
        mem_mb=res("reconstruction")["mem_mb"],
        runtime=res("reconstruction")["runtime"]
    shell:
        f"""
        set +eu
        rm -rf {{params.dir}}
        mkdir -p {{params.dir}}
        cat > {{params.dir}}/.alrb_payload.sh << 'EOF'
        cd {{params.dir}}
        asetup {config["reconstruction"]["asetupRelease"]}
        export ATHENA_CORE_NUMBER={{threads}}
        Reco_tf.py {{params.mt}} --inputRDOFile={{params.inp}} --outputAODFile=AOD.pool.root
EOF
        {alrb_container_run("{params.dir}/.alrb_payload.sh")}
        """

# Fan-in: one DAOD_PHYS per polarization from the AODs of all split jobs.
rule derivationPHYS:
    input:
        lambda w: expand(f"{RECO_DIR}/{w.p}_ttbar/job{{j}}/AOD.pool.root", j=JOBS)
    output:
        f"{DER_DIR}/{{p}}_ttbar_PHYS/DAOD_PHYS.mcval.pool.root"
    params:
        dir=lambda w: f"{DER_DIR}/{w.p}_ttbar_PHYS",
        inp=lambda w, input: rel_to(input, f"{DER_DIR}/{w.p}_ttbar_PHYS"),
        mt=lambda w, threads: mt_flags(threads)
    threads: res("derivationPHYS")["threads"]
    resources:
        mem_mb=res("derivationPHYS")["mem_mb"],
        runtime=res("derivationPHYS")["runtime"]
    shell:
        f"""
        set +eu
        rm -rf {{params.dir}}
        mkdir -p {{params.dir}}
        cat > {{params.dir}}/.alrb_payload.sh << 'EOF'
        cd {{params.dir}}
        asetup {config["derivationPHYS"]["asetupRelease"]}
        export ATHENA_CORE_NUMBER={{threads}}
        Derivation_tf.py {{params.mt}} --inputAODFile={{params.inp}} --outputDAODFile=mcval.pool.root --formats PHYS
EOF
        {alrb_container_run("{params.dir}/.alrb_payload.sh")}
        """

# Built once and shared by every validate job (rebuilt when sources change).
rule build_validation:
    input:
        [f for f in glob.glob(f"{VAL_DIR}/source/**", recursive=True) if os.path.isfile(f)]
    output:
        touch(f"{VAL_DIR}/build/.built")
    threads: res("build_validation")["threads"]
    resources:
        mem_mb=res("build_validation")["mem_mb"],
        runtime=res("build_validation")["runtime"]
    shell:
        f"""
        set +eu
        mkdir -p {VAL_DIR}/build
        cat > {VAL_DIR}/build/.alrb_payload.sh << 'EOF'
        cd {VAL_DIR}/build
        asetup {config["validation"]["asetupRelease"]}
        cmake ../source && make -j{{threads}}
EOF
        {alrb_container_run(f"{VAL_DIR}/build/.alrb_payload.sh")}
        """

# Fan-in: MCVal_eljob.py scans the polarization's derivation directory
# recursively, so all job*/DAOD_TRUTH1 files end up in one sample.
rule validate:
    input:
        built=f"{VAL_DIR}/build/.built",
        daods=lambda w: expand(f"{DER_DIR}/{w.p}_ttbar/job{{j}}/DAOD_TRUTH1.mcval.pool.root", j=JOBS)
    output:
        f"{VAL_DIR}/run/{{p}}_ttbar/hist-{{p}}_ttbar.root"
    params:
        inp=lambda w: rel_to([f"{DER_DIR}/{w.p}_ttbar"], f"{VAL_DIR}/run")
    threads: res("validate")["threads"]
    resources:
        mem_mb=res("validate")["mem_mb"],
        runtime=res("validate")["runtime"]
    shell:
        f"""
        set +eu
        mkdir -p {VAL_DIR}/run
        rm -rf {VAL_DIR}/run/{{wildcards.p}}_ttbar
        cat > {VAL_DIR}/run/.alrb_payload_{{wildcards.p}}.sh << 'EOF'
        cd {VAL_DIR}/build
        asetup {config["validation"]["asetupRelease"]}
        source x86_64-*/setup.sh
        cd ../run
        MCVal_eljob.py --input-file {{params.inp}}/ --submission-dir {{wildcards.p}}_ttbar
EOF
        {alrb_container_run(f"{VAL_DIR}/run/.alrb_payload_{{wildcards.p}}.sh")}
        """
