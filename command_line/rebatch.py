import sys
import xia2.Handlers.Streams

master_phil = """\
hklin = None
  .type = path
hklout = hklout.mtz
  .type = path
first_batch = None
  .type = int(value_min=0)
add_batch = None
  .type = int(value_min=0)
include_range = None
  .type = ints(size=2)
  .multiple=True
exclude_range = None
  .type = ints(size=2)
  .multiple=True
project_name = None
  .type = str
crystal_name = None
  .type = str
dataset_name = None
  .type = str

"""


def run(args):
    import iotbx.phil
    from xia2.Modules.Scaler.rebatch import rebatch

    processed = iotbx.phil.process_command_line(args, master_phil)
    params = processed.work.extract()
    args = processed.remaining_args
    if params.hklin is None and len(args):
        params.hklin = args[0]
    assert params.hklin is not None

    rebatch(
        params.hklin,
        params.hklout,
        first_batch=params.first_batch,
        add_batch=params.add_batch,
        include_range=params.include_range,
        exclude_range=params.exclude_range,
    )


if __name__ == "__main__":
    xia2.Handlers.Streams.setup_logging(
        logfile="xia2.rebatch.txt", debugfile="xia2.rebatch-debug.txt"
    )
    run(sys.argv[1:])
