try:
    from importlib import metadata
except ImportError:
    # Running on pre-3.8 Python; use importlib-metadata package
    import importlib_metadata as metadata

VersionNumber = metadata.version("xia2")
Version = "XIA2 %s" % VersionNumber
Directory = "xia2-%s" % VersionNumber
