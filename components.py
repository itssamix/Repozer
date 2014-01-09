# -*- coding: utf-8 -*-
##
## $id$
##
## This file is part of Indico.
## Copyright (C) 2002 - 2013 European Organization for Nuclear Research (CERN).
##
## Indico is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 3 of the
## License, or (at your option) any later version.
##
## Indico is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Indico;if not, see <http://www.gnu.org/licenses/>.

# stdlib imports
import zope.interface
import os

# legacy imports
from MaKaC.plugins.base import Observable

# indico imports
from indico.core.extpoint import Component
from indico.core.extpoint.events import IObjectLifeCycleListener, IMetadataChangeListener
from indico.core.extpoint.plugins import IPluginImplementationContributor
from indico.ext.search.repozer.implementation import RepozerSEA
from indico.ext.search.repozer.repozeIndexer import RepozeCatalog
import indico.ext.search.repozer
from MaKaC.plugins.base import PluginsHolder
from indico.web.handlers import RHHtdocs
import inspect
from repozeIndexer import RepozeCatalog
from indico.ext.search.register import SearchRegister
from zope.interface import implements

import MaKaC.services.implementation.conference as conference

# TODO: move to options
typesToIndicize = ['Conference']


# This is just until ROLES will be integrated in Indico with hook on event listener
defclasses = []
for name, obj in inspect.getmembers(conference, inspect.isclass):
    defclasses.append(name)
if 'ConferenceRolesModification' in defclasses:
    class ConferenceRolesModificationRepozer(conference.ConferenceRolesModification):
        """
        Conference roles modification
        """
        def _handleSet(self):
            conference.ConferenceRolesModification._handleSet(self)
            rc = RepozeCatalog()
            rc.reindex(self._target)
    conference.methodMap["main.changeRoles"] = ConferenceRolesModificationRepozer



# This should be removed...
# Class override from /MaKaC/services/implementation/conference.py
class ConferenceKeywordsModificationRepozer( conference.ConferenceKeywordsModification ):
    """
    Conference keywords modification
    """
    def _handleSet(self):
        conference.ConferenceKeywordsModification._handleSet(self)
        rc = RepozeCatalog()
        rc.reindex(self._target)
conference.methodMap["main.changeKeywords"] = ConferenceKeywordsModificationRepozer        




class ObjectChangeListener(Component):
    """
    This component listens for events and directs them to the MPT.
    Implements ``IObjectLifeCycleListener``,``IMetadataChangeListener``
    """

    implements(IMetadataChangeListener, IObjectLifeCycleListener)

    def toIndicize(self,obj):
        return type(obj).__name__ in typesToIndicize

    def created(self, obj, owner):
        if self.toIndicize(obj):
            RepozeCatalog().index(obj)

    def moved(self, obj, fromOwner, toOwner):
        if self.toIndicize(obj):
            RepozeCatalog().reindex(obj)

    def deleted(self, obj, oldOwner):
        if self.toIndicize(obj):
            RepozeCatalog().unindex(obj)
        
    def eventTitleChanged(self, obj, oldTitle, newTitle):
        if self.toIndicize(obj):
            RepozeCatalog().reindex(obj)    

    def infoChanged(self, obj):
        if self.toIndicize(obj):
            RepozeCatalog().reindex(obj)
                
    def eventDatesChanged(cls, obj, oldStartDate, oldEndDate, newStartDate, newEndDate):
        if self.toIndicize(obj):
            RepozeCatalog().reindex(obj)
                          

class PluginImplementationContributor(Component, Observable):
    """
    Adds interface extension to plugins's implementation.
    """

    zope.interface.implements(IPluginImplementationContributor)
        
    def getPluginImplementation(self, obj):
        plugin = PluginsHolder().getPluginType('search').getPlugin("repozer")
        #typeSearch = plugin.getOptions()["type"].getValue()
        return ("repozer", RepozerSEA)


class RHSearchHtdocsRepozer(RHHtdocs):

    _local_path = os.path.join(os.path.dirname(indico.ext.search.repozer.__file__), "htdocs")
    _min_dir = 'repozer'
