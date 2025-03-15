import subprocess
def run_command(command):
    """
    Executes a shell command, returning (stdout, stderr, returncode).
    """
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print("stdout", result.stdout)
    print("stderr", result.stderr)
    print("returncode", result.returncode)
    return result.stdout, result.stderr, result.returncode