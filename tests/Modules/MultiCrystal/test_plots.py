import scitbx.random

from xia2.Modules.MultiCrystal import plots


def test_plot_uc_histograms():
    params = (50, 60, 70, 90, 90, 90)
    rand_norm = scitbx.random.normal_distribution(mean=0, sigma=0.5)
    g = scitbx.random.variate(rand_norm)
    n = 20
    uc_params = [p + g(n) for p in params]
    d = plots.plot_uc_histograms(uc_params)
    # ensure the following dictionary keys are present
    assert set(d) >= {"uc_scatter", "uc_hist"}
    for v in d.values():
        assert set(v) >= {"layout", "data", "help"}
