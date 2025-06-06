from __future__ import annotations

import logging
import traceback

import iotbx.phil
import libtbx.phil

xia2_logger = logging.getLogger(__name__)


def handle_fail(fn):
    def wrap_fn(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception:
            xia2_logger.debug(traceback.format_exc())
            xia2_logger.debug("A program terminated abruptly")
            return None

    return wrap_fn


def diff_phil_from_params_and_scope(
    params: libtbx.phil.scope_extract, phil_scope: libtbx.phil.scope
) -> str:
    """
    This function determines which parameters in a params scope extract
    object are different to the default parameters in the original phil_scope.
    It returns the difference in the style of the string representation of a
    phil scope difference.
    """
    original = phil_scope.extract()
    diff_phil = ""

    def compare_params(
        new: libtbx.phil.scope_extract,
        original: libtbx.phil.scope_extract,
        diff_phil: str,
        parent: str = "",
    ):
        for k in [k for k in vars(original).keys() if k[0] != "_"]:
            v2 = getattr(original, k, None)
            v1 = getattr(new, k, None)
            if isinstance(v1, libtbx.phil.scope_extract):
                if parent:
                    diff_phil = compare_params(v1, v2, diff_phil, parent + "." + k)
                else:
                    diff_phil = compare_params(v1, v2, diff_phil, k)
            else:
                if (v1 or v2) and v1 != v2:
                    diff_phil += f"{parent}.{k} = {v1}\n"
        return diff_phil

    diff_phil = compare_params(params, original, diff_phil)
    pretty = phil_scope.fetch_diff(
        source=phil_scope.fetch(sources=[iotbx.phil.parse(diff_phil)])
    ).as_str()
    pretty = "The following parameters have been modified:\n\n" + pretty
    return pretty
