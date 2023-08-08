"""
Launcher script to run multiple 'serve-model' processes with a
provided GPU-to-process layout.

Only supports NVIDIA GPUs for now.
"""
import sys
import subprocess

def layout_main(args):
    # extract and remove --layout <STR> from args
    serve_args = []
    layout = None
    balancer_port = 8080
    i = 0
    while i < len(args):
        arg = args[i]

        if arg == "--layout":
            layout = args[i+1]
            i += 2
        elif arg == "--port":
            balancer_port = int(args[i+1])
            i += 2
        else:
            serve_args.append(arg)
            i += 1
    
    serve_args = " ".join(serve_args)

    processes = []
    
    num_groups = int(layout.split("x")[0])
    num_devices_per_group = int(layout.split("x")[1])
    num_devices = num_groups * num_devices_per_group

    cmd = f"nvidia-smi --query-gpu=index --format=csv,noheader | head -n {num_devices}"
    gpu_ids = subprocess.check_output(cmd, shell=True).decode("utf-8").strip().split("\n")
    gpu_ids = [int(gpu_id) for gpu_id in gpu_ids]

    # validate layout
    if len(gpu_ids) < num_groups * num_devices_per_group:
        print(f"Invalid layout '{layout}', {len(gpu_ids)} GPUs found, but {num_devices}*{num_devices_per_group} GPUs expected")
        sys.exit(1)
    
    # warn about incomplete groups
    if len(gpu_ids) > num_groups * num_devices_per_group:
        print(f"Warning: {len(gpu_ids)} GPUs found, but {num_devices}*{num_devices_per_group} GPUs expected. Some GPUs will not be used.")
    
    port = balancer_port + 1
    workers = []

    # start processes
    for i in range(num_groups):
        group_gpu_ids = gpu_ids[i*num_devices_per_group:(i+1)*num_devices_per_group]
        group_gpu_ids = ",".join([str(gpu_id) for gpu_id in group_gpu_ids])
        cmd = f"CUDA_VISIBLE_DEVICES={group_gpu_ids} python -m lmql.cli serve-model {serve_args} --port {port}"
        print(f"[localhost:{port}]", cmd)
        workers.append(f"localhost:{port}")
        processes.append(subprocess.Popen(cmd, shell=True))
        
        port += 1

    # run balancer
    workers = " ".join(workers)
    cmd = f"python -m lmql.cli serve-model balance --port {balancer_port} {workers}"
    print(f"[localhost:{port}]", cmd)
    processes.append(subprocess.Popen(cmd, shell=True))

    # wait for processes to finish or Ctrl+C
    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        print("Ctrl+C pressed, exiting all processes...")
        for process in processes:
            process.terminate()