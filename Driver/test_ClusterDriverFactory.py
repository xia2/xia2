from __future__ import absolute_import, division, print_function

import pytest

import xia2.Driver.ClusterDriverFactory as CDF


def test_instantiate_cluster_driver():
    assert CDF.ClusterDriverFactory.Driver()


def test_instantiate_nonexistant_clusterdriver_fails():
    with pytest.raises(RuntimeError):
        CDF.ClusterDriverFactory.Driver("nosuchtype")
