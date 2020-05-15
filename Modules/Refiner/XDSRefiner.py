import copy
import logging
import os

import xia2.Wrappers.Dials.ExportXDS
from dxtbx.model import ExperimentList
from xia2.Handlers.Phil import PhilIndex
from xia2.lib.bits import auto_logfiler
from xia2.Schema.Interfaces.Refiner import Refiner

logger = logging.getLogger("xia2.Modules.Refiner.XDSRefiner")


class XDSRefiner(Refiner):
    # factory functions
    def ExportXDS(self):
        export_xds = xia2.Wrappers.Dials.ExportXDS.ExportXDS()
        export_xds.set_working_directory(self.get_working_directory())
        auto_logfiler(export_xds)
        return export_xds

    def _refine_prepare(self):
        for epoch, idxr in self._refinr_indexers.items():

            experiments = idxr.get_indexer_experiment_list()
            assert len(experiments) == 1  # currently only handle one lattice/sweep
            experiment = experiments[0]
            crystal_model = experiment.crystal

            # check if the lattice was user assigned...
            user_assigned = idxr.get_indexer_user_input_lattice()

            # hack to figure out if we did indexing with Dials - if so then need to
            # run XYCORR, INIT, and then dials.export_xds before we are ready to
            # integrate with XDS
            from xia2.Modules.Indexer.DialsIndexer import DialsIndexer

            if isinstance(idxr, DialsIndexer):
                sweep = idxr.get_indexer_sweep()
                imageset = idxr._indxr_imagesets[0]
                scan = imageset.get_scan()

                first, last = scan.get_image_range()
                phi_width = scan.get_oscillation()[1]
                last_background = int(round(5.0 / phi_width)) - 1 + first
                last_background = min(last, last_background)

                from xia2.Modules.Indexer.XDSIndexer import XDSIndexer

                xds_idxr = XDSIndexer()
                xds_idxr.set_working_directory(self.get_working_directory())
                xds_idxr.set_indexer_sweep(sweep)
                xds_idxr.add_indexer_imageset(imageset)

                # next start to process these - first xycorr
                # FIXME run these *afterwards* as then we have a refined detector geometry
                # so the parallax correction etc. should be slightly better.

                # self._indxr_images = [(first, last)]
                xycorr = xds_idxr.Xycorr()
                xycorr.set_data_range(first, last)
                xycorr.set_background_range(first, last_background)
                xycorr.set_working_directory(self.get_working_directory())
                xycorr.run()

                xds_data_files = {}
                for file in ("X-CORRECTIONS.cbf", "Y-CORRECTIONS.cbf"):
                    xds_data_files[file] = xycorr.get_output_data_file(file)

                # next start to process these - then init

                init = xds_idxr.Init()

                for file in ("X-CORRECTIONS.cbf", "Y-CORRECTIONS.cbf"):
                    init.set_input_data_file(file, xds_data_files[file])

                init.set_data_range(first, last)
                init.set_background_range(first, last_background)
                init.set_working_directory(self.get_working_directory())
                init.run()

                for file in ("BLANK.cbf", "BKGINIT.cbf", "GAIN.cbf"):
                    xds_data_files[file] = init.get_output_data_file(file)

                exporter = self.ExportXDS()
                exporter.set_experiments_filename(
                    idxr.get_solution()["experiments_file"]
                )
                exporter.run()

                for file in ["XPARM.XDS"]:
                    xds_data_files[file] = os.path.join(
                        self.get_working_directory(), "xds", file
                    )

                for k, v in xds_data_files.items():
                    idxr.set_indexer_payload(k, v)

            # check that the indexer is an XDS indexer - if not then
            # create one...

            elif not idxr.get_indexer_payload("XPARM.XDS"):
                logger.debug("Generating an XDS indexer")

                idxr_old = idxr

                from xia2.Modules.Indexer.XDSIndexer import XDSIndexer

                idxr = XDSIndexer()
                idxr.set_indexer_sweep(idxr_old.get_indexer_sweep())
                self._refinr_indexers[epoch] = idxr
                self.set_refiner_prepare_done(False)

                # note to self for the future - this set will reset the
                # integrater prepare done flag - this means that we will
                # go through this routine all over again. However this
                # is not a problem as all that will happen is that the
                # results will be re-got, no additional processing will
                # be performed...

                # set the indexer up as per the frameprocessor interface...
                # this would usually happen within the IndexerFactory.

                idxr.set_indexer_sweep_name(idxr_old.get_indexer_sweep_name())

                idxr.add_indexer_imageset(idxr_old.get_imageset())
                idxr.set_working_directory(idxr_old.get_working_directory())

                # now copy information from the old indexer to the new
                # one - lattice, cell, distance etc.

                # bug # 2434 - providing the correct target cell
                # may be screwing things up - perhaps it would
                # be best to allow XDS just to index with a free
                # cell but target lattice??
                cell = crystal_model.get_unit_cell().parameters()
                check = PhilIndex.params.xia2.settings.xds_check_cell_deviation

                # FIXME this was changed in #42 but not sure logic is right
                if not check:
                    logger.debug(
                        "Inputting target cell: %.2f %.2f %.2f %.2f %.2f %.2f" % cell
                    )
                    idxr.set_indexer_input_cell(cell)

                from cctbx.sgtbx import bravais_types

                lattice = str(
                    bravais_types.bravais_lattice(group=crystal_model.get_space_group())
                )
                idxr.set_indexer_input_lattice(lattice)

                if user_assigned:
                    logger.debug("Assigning the user given lattice: %s", lattice)
                    idxr.set_indexer_user_input_lattice(True)

                idxr.set_detector(experiment.detector)
                idxr.set_beam(experiment.beam)
                idxr.set_goniometer(experiment.goniometer)

                # re-get the unit cell &c. and check that the indexing
                # worked correctly

                logger.debug("Rerunning indexing with XDS")

                experiments = idxr.get_indexer_experiment_list()
                assert len(experiments) == 1  # currently only handle one lattice/sweep
                experiment = experiments[0]
                crystal_model = experiment.crystal

                # then in here check that the target unit cell corresponds
                # to the unit cell I wanted as input...? now for this I
                # should probably compute the unit cell volume rather
                # than comparing the cell axes as they may have been
                # switched around...

                # FIXME comparison needed

    def _refine(self):
        self._refinr_refined_experiment_list = ExperimentList()
        for epoch, idxr in self._refinr_indexers.items():
            self._refinr_payload[epoch] = copy.deepcopy(idxr._indxr_payload)
            self._refinr_refined_experiment_list.extend(
                idxr.get_indexer_experiment_list()
            )

    def _refine_finish(self):
        pass
