"""Keeps the NVIDIA GPU busy for N seconds (default 20). Needs PyTorch with CUDA."""
import sys
import time

import torch

a = torch.randn(8192, 8192, device="cuda", dtype=torch.float16)
b = torch.randn(8192, 8192, device="cuda", dtype=torch.float16)
end = time.time() + (float(sys.argv[1]) if len(sys.argv) > 1 else 20)
while time.time() < end:
    for _ in range(20):
        a @ b
    torch.cuda.synchronize()
