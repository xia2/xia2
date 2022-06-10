from __future__ import annotations

from typing import Type

from xia2.Modules.SSX.data_reduction_base import BaseDataReduction, ReductionParams
from xia2.Modules.SSX.data_reduction_simple import SimpleDataReduction
from xia2.Modules.SSX.data_reduction_with_pdb_model import DataReductionWithPDBModel


def get_reducer(reduction_params: ReductionParams) -> Type[BaseDataReduction]:
    if reduction_params.model:
        return DataReductionWithPDBModel
    else:
        return SimpleDataReduction
