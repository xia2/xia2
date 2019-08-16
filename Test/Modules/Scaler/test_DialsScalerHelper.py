from __future__ import absolute_import, division, print_function

import pytest
import random

from cctbx import sgtbx
from dials.algorithms.symmetry.cosym._generate_test_data import generate_intensities
from dials.array_family import flex
from dxtbx.model.experiment_list import ExperimentList
from dxtbx.model import Crystal, Scan, Beam, Experiment
from dxtbx.serialize import load


flex.set_random_seed(42)
random.seed(42)


@pytest.fixture
def helper(ccp4, run_in_tmpdir):
    """Initialise a DialsScalerHelper, ensure CCP4 is available for test"""
    from xia2.Modules.Scaler.DialsScaler import DialsScalerHelper

    helper = DialsScalerHelper()
    helper.set_pname_xname("AUTOMATIC", "DEFAULT")
    helper.set_working_directory(run_in_tmpdir.strpath)
    return helper


def generated_exp(n=1, space_group="P 2", assign_ids=False, id_=None):
    """Generate an experiment list with two experiments."""
    experiments = ExperimentList()
    exp_dict = {
        "__id__": "crystal",
        "real_space_a": [15.0, 0.0, 0.0],
        "real_space_b": [0.0, 10.0, 0.0],
        "real_space_c": [0.0, 0.0, 20.0],
        "space_group_hall_symbol": space_group,
    }
    crystal = Crystal.from_dict(exp_dict)
    scan = Scan(image_range=[0, 90], oscillation=[0.0, 1.0])
    beam = Beam(s0=(0.0, 0.0, 1.01))
    if assign_ids:
        experiments.append(
            Experiment(identifier="0", beam=beam, scan=scan, crystal=crystal)
        )
    elif id_:
        experiments.append(
            Experiment(identifier=str(id_), beam=beam, scan=scan, crystal=crystal)
        )
    else:
        experiments.append(Experiment(beam=beam, scan=scan, crystal=crystal))
    if n > 1:
        for i in range(1, n):
            if assign_ids:
                experiments.append(
                    Experiment(identifier=str(i), beam=beam, scan=scan, crystal=crystal)
                )
            else:
                experiments.append(Experiment(beam=beam, scan=scan, crystal=crystal))
    return experiments


def generate_reflections_in_sg(space_group, id_=0, assign_id=False):
    """Generate reflections with intensities consistent with space group"""
    sgi = sgtbx.space_group_info(symbol=space_group)
    cs = sgi.any_compatible_crystal_symmetry(volume=3000)
    cs = cs.best_cell()
    cs = cs.minimum_cell()
    intensities = (
        generate_intensities(cs, d_min=2.0)
        .generate_bijvoet_mates()
        .set_observation_type_xray_intensity()
    )
    intensities = intensities.expand_to_p1()
    # needed to give vaguely sensible E_cc_true values
    reflections = flex.reflection_table()
    reflections["intensity.sum.value"] = intensities.data()
    reflections["intensity.sum.variance"] = flex.pow2(intensities.sigmas())
    reflections["miller_index"] = intensities.indices()
    reflections["id"] = flex.int(reflections.size(), id_)
    if assign_id:
        reflections.experiment_identifiers()[id_] = str(id_)
    reflections.set_flags(
        flex.bool(reflections.size(), True), reflections.flags.integrated
    )
    return reflections


def generate_test_refl(id_=0, assign_id=False):
    """Generate a small reflection table"""
    reflections = flex.reflection_table()
    reflections["intensity.sum.value"] = flex.double([1.0, 1.0, 2.0, 2.0, 3.0, 3.0])
    reflections["variance.sum.variance"] = flex.double([1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    reflections["miller_index"] = flex.miller_index(
        [(1, 0, 0), (0, 0, 1), (2, 0, 0), (0, 0, 2), (0, 1, 0), (0, -1, 0)]
    )
    reflections["id"] = flex.int(6, id_)
    if assign_id:
        reflections.experiment_identifiers()[id_] = str(id_)
    return reflections


symmetry_test_data = [
    (
        "P 2 ",
        "P 2 ",
        ["mP", "aP", "oP"],
        ["P 1 2 1", "P 1"],
        ["P 1 2 1", "P 1 2 1", "P 2 2 2"],
    ),
    (
        "P 1 ",
        "P 2 ",
        ["aP", "mP", "oP"],
        ["P 1", "P 1 2 1"],
        ["P 1 2 1", "P 1 2 1", "P 2 2 2"],
    ),
]


@pytest.mark.parametrize(
    """reflection_spacegroup, experiments_spacegroup,
  expected_lattices, required_spacegroup_order, other_spacegroups""",
    symmetry_test_data,
)
def test_dials_symmetry_decide_pointgroup(
    reflection_spacegroup,
    experiments_spacegroup,
    expected_lattices,
    required_spacegroup_order,
    other_spacegroups,
    helper,
):
    """Test for the dials_symmetry_decide_pointgroup helper function """

    generated_exp(space_group=experiments_spacegroup).as_file("test.expt")
    generate_reflections_in_sg(reflection_spacegroup).as_pickle("test.refl")

    symmetry_analyser = helper.dials_symmetry_decide_pointgroup(
        ["test.expt"], ["test.refl"]
    )

    # Note : instabilities have been observed in the order of the end of the
    # spacegroup list - this is likely due to the use of unseeded random number
    # generation in dials.symmetry symmetry element scoring, but this only seems
    # to affect the order of groups with a score near zero. Hence only assert the
    # order of the spacegroups that must be in order, near the start of the list.
    assert symmetry_analyser.get_possible_lattices() == expected_lattices
    spacegroups = symmetry_analyser.get_likely_spacegroups()
    assert spacegroups[: len(required_spacegroup_order)] == required_spacegroup_order
    assert set(spacegroups[len(required_spacegroup_order) :]) == set(other_spacegroups)


def test_assign_identifiers(helper):
    """Test the call to the assign identifiers wrapper"""
    experiments = []
    reflections = []
    for i in range(0, 3):
        refl_path, exp_path = ("test_%s.refl" % i, "test_%s.expt" % i)
        generate_test_refl().as_pickle(refl_path)
        generated_exp().as_file(exp_path)
        experiments.append(exp_path)
        reflections.append(refl_path)
    assigner = helper.assign_dataset_identifiers(experiments, reflections)
    assigned_exp = load.experiment_list(assigner.get_output_experiments_filename())
    assert assigned_exp[0].identifier == "0"
    assert assigned_exp[1].identifier == "1"
    assert assigned_exp[2].identifier == "2"
    assigned_refl = flex.reflection_table.from_file(
        assigner.get_output_reflections_filename()
    )
    assert assigned_refl.experiment_identifiers()[0] == "0"
    assert assigned_refl.experiment_identifiers()[1] == "1"
    assert assigned_refl.experiment_identifiers()[2] == "2"


class simple_sweep_info(object):
    """Simple sweep info class for testing"""

    def __init__(self):
        self.reflections = ""
        self.experiments = ""

    def get_integrater(self):
        return self

    def get_integrated_experiments(self):
        return self.experiments

    def get_integrated_reflections(self):
        return self.reflections

    def set_reflections(self, refl):
        self.reflections = refl

    def get_reflections(self):
        return self.reflections

    def set_experiments(self, exp):
        self.experiments = exp

    def get_experiments(self):
        return self.experiments


class simple_sweep_handler(object):
    """Simple sweep handler class for testing"""

    def __init__(self, number_of_experiments):
        self.number_of_experiments = number_of_experiments
        self.sis = [simple_sweep_info() for _ in range(number_of_experiments)]

    def get_epochs(self):
        """Return a list of 0...n-1"""
        return list(range(self.number_of_experiments))

    def get_sweep_information(self, epoch):
        """Return the simple sweep info class for a given epoch"""
        return self.sis[epoch]


@pytest.mark.parametrize("number_of_experiments", [2, 10])
def test_split_experiments(number_of_experiments, helper):
    """Test the call to split experiments: should split the dataset on experiment
    id, giving single datasets with unique ids from 0..n-1"""
    sweephandler = simple_sweep_handler(number_of_experiments)
    exp_path = "test.expt"
    refl_path = "test.refl"
    generated_exp(number_of_experiments, assign_ids=True).as_file(exp_path)
    reflections = flex.reflection_table()
    for i in range(number_of_experiments):
        reflections.extend(generate_test_refl(id_=i, assign_id=True))
    reflections.as_pickle(refl_path)
    # Now call split_experiments and inspect handler to check result
    sweephandler = helper.split_experiments(exp_path, refl_path, sweephandler)
    check_data_in_sweep_handler(sweephandler)


def check_data_in_sweep_handler(sweephandler):
    """Check that data in sweep handler has ids set correctly"""
    for i, epoch in enumerate(sweephandler.get_epochs()):
        si = sweephandler.get_sweep_information(epoch)
        r = flex.reflection_table.from_file(si.get_reflections())
        assert list(set(r["id"])) == [0]
        assert list(r.experiment_identifiers().keys()) == [0]
        assert list(r.experiment_identifiers().values()) == [str(i)]
        experiment = load.experiment_list(si.get_experiments())
        assert len(experiment) == 1
        assert experiment[0].identifier == str(i)


def test_assign_and_return_datasets(helper):
    """Test the combined method of assigning ids and setting in the sweep handler"""
    n = 3
    sweephandler = simple_sweep_handler(n)
    for i in range(0, n):
        si = sweephandler.get_sweep_information(i)
        refl_path, exp_path = ("test_%s.refl" % i, "test_%s.expt" % i)
        generate_test_refl().as_pickle(refl_path)
        generated_exp().as_file(exp_path)
        si.set_experiments(exp_path)
        si.set_reflections(refl_path)
    sweephandler = helper.assign_and_return_datasets(sweephandler)
    check_data_in_sweep_handler(sweephandler)


class simple_refiner(object):

    LATTICE_POSSIBLE = "LATTICE_POSSIBLE"
    LATTICE_IMPOSSIBLE = "LATTICE_IMPOSSIBLE"
    LATTICE_CORRECT = "LATTICE_CORRECT"

    def __init__(self, refiner_lattices):
        self.refiner_lattices = (
            refiner_lattices
        )  # first one should be 'best' one used in refinement
        self.indexer_done = True
        self._refiner_reset = False

    def get(self):
        return self.refiner_lattices

    def set_refiner_asserted_lattice(self, lattice):
        """Replicate asserted_lattice methods of refiner and indexer"""
        # calls indexer, if not in list of lattices - returns LATTICE_IMPOSSIBLE
        if lattice not in self.refiner_lattices:
            return self.LATTICE_IMPOSSIBLE

        if lattice == self.refiner_lattices[0]:
            """if (PhilIndex.params.xia2.settings.integrate_p1 and
              asserted_lattice != self.get_indexer_lattice() and
              asserted_lattice != 'aP'):
            if PhilIndex.params.xia2.settings.reintegrate_correct_lattice:
              self.set_indexer_done(False)
              return self.LATTICE_POSSIBLE"""
            return self.LATTICE_CORRECT

        # else, - calls eliminate, set indexer done false
        while self.get()[0] != lattice:
            del self.refiner_lattices[0]  # i.e. eliminate
            # if (not integrate_p1) or reintegrate_correct_lattice
            self.indexer_done = False
            self.refiner_reset()
        return self.LATTICE_POSSIBLE

    def get_refiner_lattice(self):
        """Return first lattice"""
        return self.refiner_lattices[0]

    def refiner_reset(self):
        """Set refiner reset as True"""
        self._refiner_reset = True

    def get_refiner_reset(self):
        """Get refiner reset status"""
        return self._refiner_reset


# get ntr if symmetry lower than refiner - resets reindex op in integrater and
# sets need_to_return = True, which then sets scaler prepare done as False
# get rerun if symmetry finds higher than refiner or no possible - then in symmetry jiffy sets the
# correct lattice in symmetry and makes it run with that.
# test_data = (refiner lattice, possible lattices, (correct, rerun, ntr))
test_data = [
    (["mP", "aP", "oP"], ["mP"], ("mP", False, False)),  # symmetry same as from refiner
    (
        ["mP", "aP", "oP"],
        ["aP"],
        ("aP", False, True),
    ),  # symmetry is lower than from refiner
    (
        ["mP", "aP", "oP"],
        ["tP", "mP"],
        ("mP", True, False),
    ),  # symmetry finds higher than refiner
    (["mP", "aP", "oP"], ["tP", "aP"], ("aP", True, True)),
]  # symmetry finds higher than refiner,
# but next best is lower than refiner


@pytest.mark.parametrize(
    "refiner_lattices, possible_lattices, expected_output", test_data
)
def test_decide_correct_lattice_using_refiner(
    ccp4, refiner_lattices, possible_lattices, expected_output
):

    refiner = simple_refiner(refiner_lattices)
    from xia2.Modules.Scaler.DialsScaler import decide_correct_lattice_using_refiner

    result = decide_correct_lattice_using_refiner(possible_lattices, refiner)
    assert result == expected_output


# refienr lattices, (pg, ntr, pt, refiner_reset, reindex_init)
test_lattices = [
    (["mP", "aP", "oP"], ("P 1 2 1", False, False, False, False)),
    # symmetry finds consistent lattice, all good
    (["tP", "mP", "aP", "oP"], ("P 1 2 1", True, False, True, False)),
    # symmetry finds lower than refiner lattice, so need to return to rerefine
    (["aP"], ("P 1", False, False, False, True)),
]  # symmetry finds higher than refiner - can occur
# is pseudosymmetry, so just drop to lower symmetry of lattice and don't need to rerefine
# as already done in this space group.


@pytest.mark.parametrize("refiner_lattices, expected_output", test_lattices)
def test_dials_symmetry_indexer_jiffy(helper, refiner_lattices, expected_output):
    """Test the jiffy"""
    n = 2
    if n > 1:
        multisweep = True
    # Create list of experiments, reflections and refiners
    experiments = []
    reflections = []
    refiners = []
    for i in range(0, n):
        refl_path, exp_path = ("test_%s.refl" % i, "test_%s.expt" % i)
        generate_reflections_in_sg("P 2", id_=i, assign_id=True).as_pickle(refl_path)
        generated_exp(space_group="P 2", id_=i).as_file(exp_path)
        experiments.append(exp_path)
        reflections.append(refl_path)
        refiners.append(simple_refiner(refiner_lattices))

    result = helper.dials_symmetry_indexer_jiffy(
        experiments, reflections, refiners, multisweep=multisweep
    )
    pg, reind_op, ntr, pt, reind_refl, reind_exp, reind_init = result
    refiner_reset = refiners[0].get_refiner_reset()
    assert (pg, ntr, pt, refiner_reset, reind_init) == expected_output
    if expected_output[3]:
        for refiner in refiners[1:]:
            assert refiner.get_refiner_reset()
