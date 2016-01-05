import numpy as np
import pytest
from scipy.optimize import check_grad

from elo_core import *

# Only need to gradient check for the naive version,
# since we test that the others agree with the gradient computation.
def test_grad():
    rs = np.random.randn(10)

    print 'Test input:  %s' % rs

    err = check_grad(
        lambda x: f_naive(x)[0],
        lambda x: f_naive(x)[1],
        rs)
    print 'Error:  %.5g' % err

    assert err < 1e-4

def test_f_compare():
    rs = np.random.randn(10)

    print 'Test input:  %s' % rs

    val_naive, grad_naive = f_naive(rs)
    print
    print 'Naive value:  %s' % val_naive
    print 'Naive gradient:  %s' % grad_naive

    val_py, grad_py = f_py(rs)
    print
    print 'Python value:  %s' % val_py
    print 'Python gradient:  %s' % grad_py

    val_np, grad_np = f_np(rs)
    print
    print 'Numpy value:  %s' % val_np
    print 'Numpy gradient:  %s' % grad_np

    np.testing.assert_almost_equal(val_naive, val_py)
    np.testing.assert_almost_equal(grad_naive, grad_py)

    np.testing.assert_almost_equal(val_naive, val_np)
    np.testing.assert_almost_equal(grad_naive, grad_np)

def test_overflow():
    rs = np.random.randn(10)

    # Translating the input shouldn't change the result, but it will cause the naive
    # computation to overflow.
    rs += 1000

    print 'Test input:  %s' % rs

    with pytest.raises(OverflowError):
        f_naive(rs)

    val_py, grad_py = f_py(rs)
    print
    print 'Python value:  %s' % val_py
    print 'Python gradient:  %s' % grad_py

    val_np, grad_np = f_np(rs)
    print
    print 'Numpy value:  %s' % val_np
    print 'Numpy gradient:  %s' % grad_np

    np.testing.assert_almost_equal(val_py, val_np)
    np.testing.assert_almost_equal(grad_py, grad_np)
