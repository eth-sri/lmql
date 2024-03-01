"""
Launcher script to run multiple 'serve-model' processes with a
provided GPU-to-process layout.

Only supports NVIDIA GPUs for now.
"""
import os
import sys
import shlex
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
    
    processes = []
    
    num_groups = int(layout.split("x")[0])
    num_devices_per_group = int(layout.split("x")[1])
    num_devices = num_groups * num_devices_per_group # the total number of devices needed

    # Query the hardware to see how many GPUs there are in total.
    # Note: we might not be able to _uses_ all of these in a shared compute environment...
    cmd = ["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"]
    all_gpu_ids = subprocess.check_output(cmd).decode("utf-8").strip().split("\n")
    all_gpu_ids = [int(gpu_id) for gpu_id in all_gpu_ids]

    # at this point, all_gpu_ids has a list of all GPUs on the system; however, we might not actually have access
    # to all of them. Let's check CUDA_VISIBLE_DEVICES and see:
    if os.getenv("CUDA_VISIBLE_DEVICES"):
        avail_gpus = [int(g) for g in os.getenv("CUDA_VISIBLE_DEVICES").split(",")]
        # quick sanity checks:
        if len(avail_gpus) == 0:
            print(f"CUDA_VISIBLE_DEVICES is set but includes no GPUSs?")
            sys.exit(1)

        if len(avail_gpus) != len(set(avail_gpus) & set(all_gpu_ids)):
            print(f"CUDA_VISIBLE_DEVICES specifies GPUs that nvidia-smi doesn't know about...")
            sys.exit(1)

        if num_devices > len(avail_gpus):
            print(f"Layout specified more devices ({num_devices}) than available: {len(avail_gpus)}")

        gpu_ids = avail_gpus[:num_devices]
    else:
        gpu_ids = all_gpu_ids[:num_devices]  # take however many of the total we need to make up our list


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

        cmd = [sys.executable, "-m", "lmql.cli", "serve-model"] + serve_args + ["--port", str(port)]
        print(f"[localhost:{port}]", " ".join(shlex.quote(word) for word in cmd))
        workers.append(f"localhost:{port}")
        processes.append(subprocess.Popen(cmd, env=dict(os.environ, CUDA_VISIBLE_DEVICES=group_gpu_ids)))
        
        port += 1

    # run balancer
    cmd = [sys.executable, "-m", "lmql.cli", "serve-model", "balance", "--port", str(balancer_port)] + workers
    print(f"[localhost:{port}]", " ".join(shlex.quote(word) for word in cmd))
    processes.append(subprocess.Popen(cmd))

    # wait for processes to finish or Ctrl+C
    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        print("Ctrl+C pressed, exiting all processes...")
        for process in processes:
            process.terminate()