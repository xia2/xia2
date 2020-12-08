# An expert who knows about how file names are structured on a number of
# platforms... this handles them mostly as strings, which of course they
# are...


import os


def windows_environment_vars_to_unix(token):
    """Transmogrify windows environment tokens (e.g. %WINDIR%) to
    the UNIX form ($WINDIR) for python environment token replacement."""

    if token.count("%") % 2:
        raise RuntimeError("must have even number of % tokens")

    in_env_variable = False

    token_list = token.split("%")
    result = ""
    for l in token_list:
        if not in_env_variable:
            result += l
            in_env_variable = True
        else:
            result += "$%s" % l
            in_env_variable = False

    return result


def expand_path(path):
    """Expand the input to give a full path."""

    if path is None:
        return None

    if os.name == "nt":
        return os.path.expandvars(
            os.path.expanduser(windows_environment_vars_to_unix(path))
        )
    else:
        return os.path.expandvars(os.path.expanduser(path))
