from __future__ import division

import iotbx.phil
from scitbx import matrix
from cctbx.crystal import symmetry
from libtbx.utils import Usage, multi_out
import sys
from xfel.cxi.util import is_odd_numbered # implicit import
from xfel.command_line.cxi_merge import master_phil
from xfel.command_line.cxi_xmerge import xscaling_manager

def run(args):
  phil = iotbx.phil.process_command_line(
    args = args, master_string = master_phil).show()
  work_params = phil.work.extract()
  if ("--help" in args) :
    libtbx.phil.parse(master_phil.show())
    return

  if ((work_params.d_min is None) or
      (work_params.data is None) or
      ((work_params.model is None) and
       work_params.scaling.algorithm != "mark1")):
    raise Usage("cxi.merge "
                "d_min=4.0 "
                "data=~/scratch/r0220/006/strong/ "
                "model=3bz1_3bz2_core.pdb")
  
  if ((work_params.rescale_with_average_cell) and
      (not work_params.set_average_unit_cell)) :
    raise Usage("If rescale_with_average_cell=True, you must also specify "+
      "set_average_unit_cell=True.")
  
  # Read Nat's reference model from an MTZ file.  XXX The observation
  # type is given as F, not I--should they be squared?  Check with Nat!
  
  log = open("%s_%s_reconcile.log" %
             (work_params.output.prefix,work_params.scaling.algorithm), "w")
  out = multi_out()
  out.register("log", log, atexit_send_to=None)
  out.register("stdout", sys.stdout)

  print >> out, "Target unit cell and space group:"
  print >> out, "  ", work_params.target_unit_cell
  print >> out, "  ", work_params.target_space_group

  miller_set = symmetry(
      unit_cell = work_params.target_unit_cell,
      space_group_info = work_params.target_space_group
    ).build_miller_set(
      anomalous_flag = not work_params.merge_anomalous,
      d_min = work_params.d_min)
  from xfel.cxi.merging.general_fcalc import random_structure
  i_model = random_structure(work_params)

# ---- Augment this code with any special procedures for x scaling
  scaler = xscaling_manager(
    miller_set = miller_set,
    i_model = i_model,
    params = work_params,
    log = out)
  
  scaler.read_all()
  print "finished reading, now look at master list of ASU miller indices"
  sg = miller_set.space_group()
  for ihkl,HKL in enumerate(scaler.millers["merged_asu_hkl"]):
    print ihkl,HKL

  pg = sg.build_derived_laue_group()
  rational_ops = []
  for symop in pg:
    print symop.r().as_hkl()
    rational_ops.append((matrix.sqr(symop.r().transpose().as_rational()),
                         symop.r().as_hkl()))

  print len(scaler.millers["merged_asu_hkl"])
  print len(miller_set.indices())
  miller_set.show_summary()

  hkl_asu = scaler.observations["hkl_id"]
  imageno = scaler.observations["frame_id"]
  intensi = scaler.observations["i"]
  sigma_i = scaler.observations["sigi"]
  lookup = scaler.millers["merged_asu_hkl"]
  origH = scaler.observations["H"]
  origK = scaler.observations["K"]
  origL = scaler.observations["L"]

  from cctbx.miller import map_to_asu
  sgtype = miller_set.space_group_info().type()
  aflag = miller_set.anomalous_flag()
  from cctbx.array_family import flex

  polarity_transform_I23 = matrix.sqr((0, 1, 0, -1, 0, 0, 0, 0, 1))
  for x in xrange(len(scaler.observations["hkl_id"])):
    hkl = lookup[hkl_asu[x]]
    hklrev = polarity_transform_I23 * hkl
    testmiller = flex.miller_index([hklrev])
    map_to_asu(sgtype, aflag, testmiller)
    hklrev_asu = testmiller[0]
    if (origH[x] + origK[x] + origL[x]) % 2 != 0 :
      relation = "BADSYS" 
    else:
      original = origH[x], origK[x], origL[x]
      relation = "XXXXXX"
      for op in rational_ops:
        if (op[0] * original).elems == hkl:
          relation = op[1]
          break

    print "%6d" % hkl_asu[x], "%9s" % relation, \
          "%7d frame %5d HKL:%4d%4d%4d ASU:%4d%4d%4d ALT:%4d%4d%4d" % (
      x, imageno[x], origH[x], origK[x], origL[x], hkl[0], hkl[1], hkl[2],
      hklrev_asu[0], hklrev_asu[1], hklrev_asu[2]), \
      "I %8.2f S %8.2f" % (intensi[x], sigma_i[x])

if (__name__ == "__main__"):
  sargs = ["d_min=3.0",
           "output.n_bins=25",
           "target_unit_cell=106.18,106.18,106.18,90,90,90",
           "target_space_group=I23",
           "nproc=1",
           "merge_anomalous=True",
           "plot_single_index_histograms=False",
           "scaling.algorithm=mark1",
           "raw_data.sdfac_auto=True",
           "scaling.mtz_file=fake_filename.mtz",
           "scaling.show_plots=True",
           "scaling.log_cutoff=-3.",
           "set_average_unit_cell=True",
           "rescale_with_average_cell=False",
           "significance_filter.sigma=0.5",
           "output.prefix=poly_124_unpolarized_control"
           ]
  result = run(args=sargs)
