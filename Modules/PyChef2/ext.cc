/*
 * ext.cc
 *
 *  Copyright (C) 2015 Diamond Light Source
 *
 *  Author: Richard Gildea
 *
 *  This code is distributed under the BSD license, a copy of which is
 *  included in the root directory of this package.
 */
#include <boost/python.hpp>
#include <boost/python/def.hpp>
#include <boost/python/suite/indexing/map_indexing_suite.hpp>
#include <xia2/Modules/Pychef2/pychef.h>

namespace xia2 { namespace pychef {
  namespace boost_python {

  using namespace boost::python;

  void export_observations() {

    class_<Observations::map_type>("ObservationGroupMap")
      .def(map_indexing_suite<Observations::map_type>())
      ;

    class_<Observations>("Observations", no_init)
      .def(init<scitbx::af::const_ref<cctbx::miller::index<> > const&,
                sgtbx::space_group, bool>((
           arg("miller_index"),
           arg("space_group"),
           arg("anomalous_flag"))))
      .def("observation_groups", &Observations::observation_groups)
      ;
  }

  void export_observation_group() {
    class_<ObservationGroup>("ObservationGroup", no_init)
      .def(init<cctbx::miller::index<>, bool>((
           arg("miller_index"),
           arg("flag"))))
      .def("add_iplus", &ObservationGroup::add_iplus)
      .def("add_iminus", &ObservationGroup::add_iminus)
      .def("miller_index", &ObservationGroup::miller_index)
      .def("iplus", &ObservationGroup::iplus)
      .def("iminus", &ObservationGroup::iminus)
      .def("is_centric", &ObservationGroup::is_centric)
      ;
  }


  void export_accumulators() {
    using namespace accumulator;


    typedef CompletenessAccumulator<> completeness_accumulator_t;
    class_<completeness_accumulator_t>("CompletenessAccumulator", no_init)
      .def(init<af::const_ref<std::size_t> const &,
                af::const_ref<double> const &,
                cctbx::miller::binner const &,
                int>((
           arg("dose"),
           arg("d_star_sq"),
           arg("binner"),
           arg("n_steps"))))
      .def("__call__", &completeness_accumulator_t::operator())
      .def("finalise", &completeness_accumulator_t::finalise)
      .def("iplus_completeness",
           &completeness_accumulator_t::iplus_completeness)
      .def("iminus_completeness",
           &completeness_accumulator_t::iminus_completeness)
      .def("ieither_completeness",
           &completeness_accumulator_t::ieither_completeness)
      .def("iboth_completeness",
           &completeness_accumulator_t::iboth_completeness)
      .def("iplus_completeness_bins",
           &completeness_accumulator_t::iplus_completeness_bins)
      .def("iminus_completeness_bins",
           &completeness_accumulator_t::iminus_completeness_bins)
      .def("ieither_completeness_bins",
           &completeness_accumulator_t::ieither_completeness_bins)
      .def("iboth_completeness_bins",
           &completeness_accumulator_t::iboth_completeness_bins)
      ;


    typedef RcpScpAccumulator<> rcp_scp_accumulator_t;
    class_<rcp_scp_accumulator_t>("RcpScpAccumulator", no_init)
      .def(init<af::const_ref<double> const &,
                af::const_ref<double> const &,
                af::const_ref<std::size_t> const &,
                af::const_ref<double> const &,
                cctbx::miller::binner const &,
                int>((
           arg("dose"),
           arg("d_star_sq"),
           arg("binner"),
           arg("n_steps"))))
      .def("__call__", &rcp_scp_accumulator_t::operator())
      .def("finalise", &rcp_scp_accumulator_t::finalise)
      .def("rcp_bins",
           &rcp_scp_accumulator_t::rcp_bins)
      .def("scp_bins",
           &rcp_scp_accumulator_t::scp_bins)
      .def("rcp",
           &rcp_scp_accumulator_t::rcp)
      .def("scp",
           &rcp_scp_accumulator_t::scp)
      ;


    typedef RdAccumulator<> rd_accumulator_t;
    class_<rd_accumulator_t>("RdAccumulator", no_init)
      .def(init<af::const_ref<double> const &,
                af::const_ref<std::size_t> const &,
                int>((
           arg("dose"),
           arg("n_steps"))))
      .def("__call__", &rd_accumulator_t::operator())
      .def("finalise", &rd_accumulator_t::finalise)
      .def("rd",
           &rd_accumulator_t::rd)
      ;

  }

  BOOST_PYTHON_MODULE(xia2_pychef_ext)
  {
    export_observations();
    export_observation_group();
    export_accumulators();
  }

}}} // namespace = xia2::pychef::boost_python
