from __future__ import absolute_import, division, unicode_literals

import sys

import param as _param
from bokeh.document import Document as _Document
from pyviz_comms import (
    CommManager as _CommManager, JupyterCommManager as _JupyterCommManager,
    extension as _pyviz_extension)

from . import layout # noqa
from . import links # noqa
from . import pane # noqa
from . import param # noqa
from . import pipeline # noqa
from . import widgets # noqa

from .interact import interact # noqa
from .layout import Row, Column, Tabs, Spacer # noqa
from .pane import panel, Pane # noqa
from .param import Param # noqa
from .util import load_notebook as _load_nb
from .viewable import Viewable


__version__ = str(_param.version.Version(
    fpath=__file__, archive_commit="$Format:%h$", reponame="panel"))


class state(_param.Parameterized):
    """
    Holds global state associated with running apps, allowing running
    apps to indicate their state to a user.
    """

    curdoc = _param.ClassSelector(class_=_Document, doc="""
        The bokeh Document for which a server event is currently being
        processed.""")

    _comm_manager = _CommManager

    # An index of all currently active views
    _views = {}

    # An index of all curently active servers
    _servers = {}


class extension(_pyviz_extension):
    """
    Initializes the pyviz notebook extension to allow plotting with
    bokeh and enable comms.
    """

    inline = _param.Boolean(default=True, doc="""
        Whether to inline JS and CSS resources.
        If disabled, resources are loaded from CDN if one is available.""")

    _loaded = False

    def __call__(self, *args, **params):
        # Abort if IPython not found
        try:
            ip = params.pop('ip', None) or get_ipython() # noqa (get_ipython)
        except:
            return

        p = _param.ParamOverrides(self, params)
        if hasattr(ip, 'kernel') and not self._loaded:
            # TODO: JLab extension and pyviz_comms should be changed
            #       to allow multiple cleanup comms to be registered
            _JupyterCommManager.get_client_comm(self._process_comm_msg,
                                                "hv-extension-comm")
        _load_nb(p.inline)
        self._loaded = True

        Viewable._comm_manager = _JupyterCommManager

        if 'holoviews' in sys.modules:
            import holoviews as hv
            if hv.extension._loaded:
                return
            import holoviews.plotting.bokeh # noqa
            if hasattr(hv.Store, 'set_current_backend'):
                hv.Store.set_current_backend('bokeh')
            else:
                hv.Store.current_backend = 'bokeh'


def _cleanup_panel(msg_id):
    """
    A cleanup action which is called when a plot is deleted in the notebook
    """
    if msg_id not in state._views:
        return
    viewable, model = state._views.pop(msg_id)
    viewable._cleanup(model)


def _cleanup_server(server_id):
    """
    A cleanup action which is called when a server is deleted in the notebook
    """
    if server_id not in state._servers:
        return
    server, viewable, docs = state._servers.pop(server_id)
    server.stop()
    for doc in docs:
        for root in doc.roots:
            if root.ref['id'] in viewable._models:
                viewable._cleanup(root)

extension.add_delete_action(_cleanup_panel)
if hasattr(extension, 'add_server_delete_action'):
    extension.add_server_delete_action(_cleanup_server)
