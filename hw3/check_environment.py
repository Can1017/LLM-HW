"""Record the actual Conda/PyTorch runtime and execute a CUDA operation."""
import importlib.metadata
import platform
import site
import sys

import torch
from prepare_data import ROOT, write_json

assert not site.ENABLE_USER_SITE, 'Activate hw3-bert with PYTHONNOUSERSITE=1'
assert torch.cuda.is_available(), 'Install the CUDA PyTorch wheel in hw3-bert'
matrix = torch.rand(256, 256, device='cuda')
product = matrix @ matrix
assert torch.isfinite(product).all()
record = {
    'python_executable': sys.executable, 'python': sys.version, 'platform': platform.platform(),
    'user_site_enabled': site.ENABLE_USER_SITE, 'torch_location': torch.__file__,
    'torch': torch.__version__, 'cuda_runtime': torch.version.cuda,
    'gpu': torch.cuda.get_device_name(0),
    'gpu_memory_mib': torch.cuda.get_device_properties(0).total_memory / 2**20,
    'cuda_matrix_multiplication': 'passed',
    'packages': {name: importlib.metadata.version(name) for name in
                 ['torch', 'transformers', 'numpy', 'requests', 'matplotlib', 'pytest', 'tokenizers']}}
write_json(ROOT / 'results/environment.json', record)
print(record, flush=True)
