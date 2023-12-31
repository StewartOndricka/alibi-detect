import numpy as np
import pytest
import tensorflow as tf
from tensorflow.keras.layers import Dense
import torch
import torch.nn as nn
from alibi_detect.cd import LearnedKernelDrift
from alibi_detect.cd.pytorch.learned_kernel import LearnedKernelDriftTorch
from alibi_detect.cd.tensorflow.learned_kernel import LearnedKernelDriftTF
from alibi_detect.utils.frameworks import has_keops
if has_keops:
    from alibi_detect.cd.keops.learned_kernel import LearnedKernelDriftKeops
    from pykeops.torch import LazyTensor

n, n_features = 100, 5


class MyKernelTF(tf.keras.Model):  # TODO: Support then test models using keras functional API
    def __init__(self, n_features: int):
        super().__init__()
        self.config = {'n_features': n_features}
        self.dense = Dense(20)

    def call(self, x: tf.Tensor, y: tf.Tensor) -> tf.Tensor:
        return tf.einsum('ji,ki->jk', self.dense(x), self.dense(y))

    def get_config(self) -> dict:
        return self.config

    @classmethod
    def from_config(cls, config):
        return cls(**config)


class MyKernelTorch(nn.Module):
    def __init__(self, n_features: int):
        super().__init__()
        self.dense = nn.Linear(n_features, 20)

    def forward(self, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        return torch.einsum('ji,ki->jk', self.dense(x), self.dense(y))


if has_keops:
    class MyKernelKeops(nn.Module):
        def __init__(self):
            super().__init__()

        def forward(self, x: LazyTensor, y: LazyTensor) -> LazyTensor:
            return (- ((x - y) ** 2).sum(-1)).exp()


tests_lkdrift = ['tensorflow', 'pytorch', 'keops', 'PyToRcH', 'mxnet']
n_tests = len(tests_lkdrift)


@pytest.fixture
def lkdrift_params(request):
    return tests_lkdrift[request.param]


@pytest.mark.parametrize('lkdrift_params', list(range(n_tests)), indirect=True)
def test_lkdrift(lkdrift_params):
    backend = lkdrift_params
    if backend.lower() == 'pytorch':
        kernel = MyKernelTorch(n_features)
    elif backend.lower() == 'tensorflow':
        kernel = MyKernelTF(n_features)
    elif has_keops and backend.lower() == 'keops':
        kernel = MyKernelKeops()
    else:
        kernel = None
    x_ref = np.random.randn(*(n, n_features))

    try:
        cd = LearnedKernelDrift(x_ref=x_ref, kernel=kernel, backend=backend)
    except NotImplementedError:
        cd = None
    except ImportError:
        assert not has_keops
        cd = None

    if backend.lower() == 'pytorch':
        assert isinstance(cd._detector, LearnedKernelDriftTorch)
    elif backend.lower() == 'tensorflow':
        assert isinstance(cd._detector, LearnedKernelDriftTF)
    elif has_keops and backend.lower() == 'keops':
        assert isinstance(cd._detector, LearnedKernelDriftKeops)
    else:
        assert cd is None
