# -*- coding: utf-8 -*-

"""\
Job Scheduler Interface
-----------------------

This module provides a unified interface to submitting serial, local-MPI
parallel, and parallel jobs on high-performance computing (HPC) queues.
"""

import sys
import os
import abc
import re
import shlex
import subprocess
import logging
import textwrap
from collections import Mapping, OrderedDict
import six

from ..config import cmlenv
from ..config import config
from ..config.jinja2wrappers import CaelusTemplates
from ..utils import osutils

_lgr = logging.getLogger(__name__)

def caelus_execute(cmd, env=None, stdout=sys.stdout, stderr=sys.stderr):
    """Execute a CML command with the right environment setup

    A wrapper around subprocess.Popen to set up the correct environment before
    invoing the CML executable.

    The command can either be a string or a list of arguments as appropriate
    for Caelus executables.

    Examples:
      caelus_execute("blockMesh -help")

    Args:
        cmd (str or list): The command to be executed
        env (CMLEnv): An instance representing the CML installation
                      (default: latest)
        stdout: A file handle where standard output is redirected
        stderr: A file handle where standard error is redirected

    Returns:
        subprocess.Popen : The task instance
    """
    renv = env or cmlenv.cml_get_latest_version()
    posix = not (osutils.ostype() == "windows")
    cmd_popen = cmd if isinstance(cmd, list) else shlex.split(cmd, posix=posix)
    _lgr.debug("Executing shell command: %s", ' '.join(cmd_popen))
    task = subprocess.Popen(
        cmd_popen, stdout=stdout, stderr=stderr, env=renv.environ)
    return task

def python_execute(pyscript, script_args="", env=None,
                   log_file=None, log_to_file=True):
    """Execute a python script with the right environment

    This function will setup the correct CPL and CML environment and execute
    the python script within this environment. The user should only provide the
    name of the script and not ``python script`` as this it is this functions
    job to detect the correct python executable and execute within that
    environment.

    If ``log_file`` isn't provided it automatically creates a "py_*.log" file
    to redirect output messages from the script where ``*`` is replaced with
    the basename of the python script.

    Args:
        pyscript (path): Filename of the python script
        script_args (str): Extra arguments to be passed to the python script
        env (CMLEnv): CML environment used for execution
        log_file (filename): Filename to redirect output to
        log_to_file (bool): Should outputs be redirected to log file

    Returns:
        status (int): The status of the execution

    """
    spath = osutils.abspath(pyscript)
    if not log_file and log_to_file:
        _, sbase, _ = osutils.split_path(spath)
        log_file = "py_%s.log"%sbase
    pycmd = "%s %s %s"%(sys.executable, spath, script_args)
    fh = open(log_file, 'w') if log_file else sys.stdout
    task = caelus_execute(pycmd, env, fh, stderr=subprocess.STDOUT)
    status = task.wait()
    if status != 0:
        _lgr.error("Python script %s failed; status = %d",
                    spath, status)
    if log_file is not None:
        fh.close()
    return status

@six.add_metaclass(abc.ABCMeta)
class HPCQueue():
    """Abstract base class for job submission interface

    Attributes:
        name (str): Job name
        queue (str): Queue/partition where job is submitted
        account (str): Account the job is charged to
        num_nodes (int): Number of nodes requested
        num_ranks (int): Number of MPI ranks
        stdout (path): Filename where standard out is redirected
        stderr (path): Filename where standard error is redirected
        join_outputs (bool): Merge stdout/stderr to same file
        mail_opts (str): Mail options (see specific queue implementation)
        email_address (str): Email address for notifications
        qos (str): Quality of service
        time_limit (str): Wall clock time limit
        shell (str): shell to use for scripts
        mpi_extra_args (str): additional arguments for MPI
    """

    #: Variables to parse from configuration file
    _cpl_config_vars = ['name', 'queue', 'account', 'num_nodes',
                        'num_ranks', 'stdout', 'stderr', 'join_outputs',
                        'mail_opts', 'email_address', 'qos',
                        'time_limit', 'shell']

    #: Identifier used for queue
    queue_name = "_ERROR_"

    #: Attribute to job scheduler option mapping
    _queue_var_map = {}

    #: Default values for attributes
    _queue_default_values = {}

    @classmethod
    @abc.abstractmethod
    def submit(cls, script_file, job_dependencies=None, extra_args=None,
               dep_type=None):
        """Submit the job to the queue"""

    @staticmethod
    @abc.abstractmethod
    def delete(job_id):
        """Delete a job from the queue"""

    @staticmethod
    def is_parallel():
        """Flag indicating whether the queue type can support parallel runs"""
        return True

    @staticmethod
    def is_job_scheduler():
        """Is this a job scheduler"""
        return True

    def __init__(self, name, cml_env=None, **kwargs):
        """
        Args:
            name (str): Name of the job
            cml_env (CMLEnv): Environment used for execution
        """
        self.name = name
        self.cml_env = cml_env
        self.shell = "/bin/bash"
        self.num_ranks = 1
        self.env_config = ""
        self._has_script_body = False
        self._script_body = None
        cfg = config.get_config()
        opts = cfg.caelus.system.scheduler_defaults
        for key, val in self._queue_default_values.items():
            setattr(self, key, val)
        for key, val in opts.items():
            setattr(self, key, val)
        for key, val in kwargs.items():
            setattr(self, key, val)

    def __repr__(self):
        return """<%s (%s)>"""%(self.__class__.__name__, self.name)

    def write_script(self, script_name=None):
        """Write a submission script using the arguments provided

        Args:
            script_name (path): Name of the script file
        """
        if not self._has_script_body:
            raise RuntimeError("Contents of script have not been initialized")
        fname = script_name or "%s_%s.job"%(
            self.name, self.queue_name)
        qconf = self.get_queue_settings()
        tmpl = CaelusTemplates()
        tmpl.write_template(fname, "run/hpc_queue/hpc_queue.job.tmpl",
                            job=self, queue_config=qconf)
        return fname

    def update(self, settings):
        """Update queue settings from the given dictionary"""
        for key in self._cpl_config_vars:
            if key in settings:
                setattr(self, key, settings[key])

    def process_cml_run_env(self):
        """Populate the run variables for script"""
        env_cfg = """
        # CAELUS environment updates
        export PROJECT_DIR=%s
        export CAELUS_PROJECT_DIR=${PROJECT_DIR}
        export PATH=%s:${PATH}
        export LD_LIBRARY_PATH=%s:${LD_LIBRARY_PATH}
        export MPI_BUFFER_SIZE=20000000

        """
        renv = self.cml_env or cmlenv.cml_get_latest_version()
        path_var = (renv.bin_dir + os.pathsep + renv.user_bindir +
                    os.pathsep + renv.mpi_bindir)
        lib_var = (renv.lib_dir + os.pathsep + renv.user_libdir +
                   os.pathsep + renv.mpi_libdir)
        self.env_config = textwrap.dedent(env_cfg)%(
            renv.project_dir, path_var, lib_var)

    def process_foam_run_env(self):
        """Populate the run variables for OpenFOAM execution"""
        env_cfg = """
        # OpenFOAM configuration
        source %s
        export LD_LIBRARY_PATH=%s:${LD_LIBRARY_PATH}

        """
        renv = self.cml_env
        bashrc_path = self.cml_env.foam_bashrc
        libs = "lib_dir user_libdir site_libdir mpi_libdir".split()
        libvar = os.pathsep.join(getattr(renv, vv)
                                 for vv in libs
                                 if getattr(renv, vv))
        self.env_config = textwrap.dedent(env_cfg)%(
            bashrc_path, libvar)

    def process_run_env(self):
        """Process runtime environment for scripts"""
        if self.cml_env and isinstance(self.cml_env, cmlenv.FOAMEnv):
            self.process_foam_run_env()
        else:
            self.process_cml_run_env()

    @abc.abstractmethod
    def get_queue_settings(self):
        """Return a string with all the necessary queue options"""

    def prepare_mpi_cmd(self):
        """Prepare the MPI invocation"""
        num_mpi_ranks = getattr(self, "num_ranks", 1)
        cmd_tmpl = ("mpiexec -localonly %d "
                    if osutils.ostype() == "windows"
                    else "mpiexec -np %d ")
        mpi_cmd = cmd_tmpl%num_mpi_ranks
        return mpi_cmd + getattr(self, "mpi_extra_args", "")

    @abc.abstractmethod
    def __call__(self, **kwargs):
        """Submit job to scheduler"""

    @property
    def script_body(self):
        """The contents of the script submitted to scheduler"""
        return self._script_body

    @script_body.setter
    def script_body(self, value):
        self._script_body = value
        self._has_script_body = True

class SerialJob(HPCQueue):
    """Interface to a serial job"""

    queue_name = "serial_job"

    @classmethod
    def submit(cls, script_file, job_dependencies=None,
               extra_args=None):
        """Submit the job to the queue"""
        task = subprocess.Popen(script_file)
        status = task.wait()
        if status != 0:
            _lgr.error("Error executing script %s", script_file)
        return status

    @staticmethod
    def delete(job_id):
        """Delete a job from the queue"""
        pass

    @staticmethod
    def is_parallel():
        """Flag indicating whether the queue type can support parallel runs"""
        return False

    @staticmethod
    def is_job_scheduler():
        """Flag indicating whether this is a job scheduler"""
        return False

    def get_queue_settings(self):
        """Return queue settings"""
        return ""

    def prepare_mpi_cmd(self):
        """Prepare the MPI invocation"""
        return ""

    def __call__(self, **kwargs):
        wait = kwargs.get("wait", True)
        if not self._has_script_body:
            raise RuntimeError("Invalid command for execution")
        cmdline = self.script_body
        outfile = getattr(self, "stdout", "%s.log"%self.name)
        with open(outfile, 'w') as fh:
            task = caelus_execute(
                cmdline, env=self.cml_env,
                stdout=fh, stderr=subprocess.STDOUT)
            self.task = task # pylint: disable=attribute-defined-outside-init
            if wait:
                status = task.wait()
                if status != 0:
                    _lgr.error("Error running command: %s", cmdline)
                return status

class ParallelJob(SerialJob):
    """Interface to a parallel job"""

    queue_name = "parallel_job"

    @staticmethod
    def is_parallel():
        """Flag indicating whether the queue type can support parallel runs"""
        return True

    def prepare_mpi_cmd(self):
        """Prepare the MPI invocation"""
        num_mpi_ranks = getattr(self, "num_ranks", 1)
        machinefile = getattr(self, "machinefile", None)
        cmd_tmpl = ("mpiexec -localonly %d "
                    if osutils.ostype() == "windows"
                    else "mpiexec -np %d ")
        mpi_cmd = cmd_tmpl%num_mpi_ranks
        if machinefile:
            mpi_cmd += mpi_cmd + " -machinefile %s "%machinefile
        return mpi_cmd + getattr(self, "mpi_extra_args", "")

class SlurmQueue(HPCQueue):
    """Interface to SLURM queue manager"""

    queue_name = "slurm"

    _queue_var_map = OrderedDict(
        name="job-name",
        queue="partition",
        account="account",
        num_nodes="nodes",
        num_ranks="ntasks",
        stdout="output",
        stderr="error",
        mail_opts="mail-type",
        email_address="mail-user",
        qos="qos",
        time_limit="time",
        dependencies="depend",
        licenses="licenses",
        features="constraint"
    )

    _queue_default_values = dict(
        stdout="job-%x-%J.out",
        mail_opts="NONE",
        shell="/bin/bash"
    )

    _batch_job_regex = re.compile(r"Submitted batch job (\d+)")

    @classmethod
    def submit(cls, script_file,
               job_dependencies=None,
               extra_args=None,
               dep_type="afterok"):
        """Submit to SLURM using sbatch command

        ``job_dependencies`` is a list of SLURM job IDs. The submitted job will
        not run until after all the jobs provided in this list have been
        completed successfully.

        ``extra_args`` is a dictionary of extra arguments to be passed to
        ``sbatch`` command. Note that this can override options provided in the
        script file as well as introduce additional options during submission.

        ``dep_type`` can be one of: after, afterok, afternotok afterany

        The job ID returned by this method can be used as an argument to delete
        method or as an entry in ``job_dependencies`` for a subsequent job
        submission.

        Args:
            script_file (path): Script provided to sbatch command
            job_dependencies (list): List of jobs to wait for
            extra_args (dict): Extra SLURM arguments
            dep_type (str): Dependency type

        Returns:
            str: Job ID as a string
        """
        depends_arg = ""
        if job_dependencies:
            depends_arg = (
                "--depend afterok:" +
                ":".join("%s"%i for i in job_dependencies))

        slurm_args = ""
        if isinstance(extra_args, Mapping):
            slurm_args = " ".join(
                "--%s %s"%(cls._queue_var_map.get(key, key), val)
                for key, val in extra_args.items())
        elif extra_args is not None:
            slurm_args = extra_args

        sbatch_cmd = "sbatch %s %s %s"%(
            depends_arg, slurm_args, script_file)
        cmd_line = shlex.split(sbatch_cmd)
        _lgr.debug("Executing SLURM sbatch command: %s", sbatch_cmd)
        pp = subprocess.Popen(
            cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = pp.communicate()
        job_id_match = cls._batch_job_regex.search(out.decode('utf-8'))
        if err or not job_id_match:
            raise RuntimeError("Error submitting job: '%s'"%sbatch_cmd)
        job_id = job_id_match.group(1)
        return job_id

    @staticmethod
    def delete(job_id):
        """Delete the SLURM batch job using job ID"""
        scancel_cmd = "scancel %s"%job_id
        cmd_line = shlex.split(scancel_cmd)
        _lgr.debug("Executing SLURM scancel command: %s", scancel_cmd)
        pp = subprocess.Popen(
            cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = pp.communicate()
        if out:
            _lgr.debug("scancel output: %s", out)
        if err:
            _lgr.debug("Error executing scancel: %s", err)

    def __init__(self, name, cml_env=None, **kwargs):
        """
        Args:
            name (str): Name of the job
            cml_env (CMLEnv): Environment used for execution
        """
        super(SlurmQueue, self).__init__(name, cml_env, **kwargs)
        cfg = config.get_config()
        opts = cfg.caelus.system
        use_mpiexec = opts.get("slurm_use_mpiexec", True)
        if not use_mpiexec:
            self.prepare_mpi_cmd = self.prepare_srun_cmd

    def get_queue_settings(self):
        """Return all SBATCH options suitable for embedding in script"""
        qopts = "\n".join(
            "#SBATCH --%s %s"%(val, getattr(self, key))
            for key, val in self._queue_var_map.items()
            if hasattr(self, key))
        header = "\n# SLURM options\n"
        return header + qopts + "\n"

    def prepare_srun_cmd(self):
        """Prepare the call to SLURM srun command"""
        return "srun --ntasks ${SLURM_NTASKS} " + getattr(
            self, "mpi_extra_args", "")

    def __call__(self, **kwargs):
        """Submit the job"""
        script_file = kwargs.get("script_file", None)
        job_deps = kwargs.get("job_dependencies", None)
        extra_args = kwargs.get("extra_args", None)
        if not self._has_script_body:
            raise RuntimeError(
                "Script contents have not been set before submit")
        self.process_run_env()
        script_file = self.write_script(script_file)
        return self.submit(script_file, job_deps, extra_args)

class PBSQueue(HPCQueue):
    """PBS Queue Interface"""

    queue_name = "pbs"

    _queue_var_map = OrderedDict(
        name="-N ",
        queue="-q ",
        account="-A ",
        num_nodes="-l nodes=",
        stdout="-o ",
        stderr="-e ",
        join_outputs="-j ",
        mail_opts="-m ",
        email_address="-M ",
        time_limit="-l walltime=",
    )

    _default_queue_vaues = dict(
        stdout="job-$PBS_JOBNAME-$PBS_JOBID.out",
        join_outputs="oe",
        shell="/bin/bash",
    )

    _batch_job_regex = re.compile(r"(\d+)")

    @classmethod
    def submit(cls, script_file,
               job_dependencies=None,
               extra_args=None,
               dep_type="afterok"):
        """Submit a PBS job using qsub command

        ``job_dependencies`` is a list of PBS job IDs. The submitted job will
        run depending the status of the dependencies.

        ``extra_args`` is a dictionary of arguments passed to ``qsub`` command.


        The job ID returned by this method can be used as an argument to delete
        method or as an entry in ``job_dependencies`` for a subsequent job
        submission.

        Args:
            script_file (path): Script provided to sbatch command
            job_dependencies (list): List of jobs to wait for
            extra_args (dict): Extra SLURM arguments

        Returns:
            str: Job ID as a string
        """
        depends_arg = ""
        if job_dependencies:
            depends_arg = (
                "-W depend=%s:"%dep_type +
                ":".join("%s"%i for i in job_dependencies))
        qsub_args = extra_args or ""

        qsub_cmd = "qsub %s %s %s"%(
            depends_arg, qsub_args, script_file)
        cmd_line = shlex.split(qsub_cmd)
        _lgr.debug("Executing PBS qsub command: %s", qsub_cmd)
        pp = subprocess.Popen(
            cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = pp.communicate()
        job_id_match = cls._batch_job_regex.search(out.decode('utf-8'))
        if err or not job_id_match:
            raise RuntimeError("Error submitting job: '%s'"%qsub_cmd)
        job_id = job_id_match.group(1)
        return job_id

    @staticmethod
    def delete(job_id):
        """Delete the PBS batch job using job ID"""
        qdel_cmd = "qdel %s"%job_id
        cmd_line = shlex.split(qdel_cmd)
        _lgr.debug("Executing PBS qdel command: %s", qdel_cmd)
        pp = subprocess.Popen(
            cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = pp.communicate()
        if out:
            _lgr.debug("qdel output: %s", out)
        if err:
            _lgr.debug("Error executing qdel: %s", err)

    def get_queue_settings(self):
        """Return all PBS options suitable for embedding in script"""
        qopts = "\n".join(
            "#PBS %s%s"%(val, getattr(self, key))
            for key, val in self._queue_var_map.items()
            if hasattr(self, key))
        header = "\n# PBS Queue options\n"
        return header + qopts + "\n"

    def __call__(self, **kwargs):
        """Submit the job"""
        script_file = kwargs.get("script_file", None)
        job_deps = kwargs.get("job_dependencies", None)
        extra_args = kwargs.get("extra_args", None)
        if not self._has_script_body:
            raise RuntimeError(
                "Script contents have not been set before submit")
        self.process_run_env()
        script_file = self.write_script(script_file)
        return self.submit(script_file, job_deps, extra_args)

_hpc_queue_map = dict(
    no_mpi=SerialJob,
    local_mpi=ParallelJob,
    slurm=SlurmQueue,
    pbs=PBSQueue,
)

def get_job_scheduler(queue_type=None):
    """Return an instance of the job scheduler"""
    cfg = config.get_config()
    cfg_queue_type = cfg.caelus.system.get("job_scheduler", 'local_mpi')
    qtype = queue_type or cfg_queue_type
    return _hpc_queue_map.get(qtype.lower(), ParallelJob)
