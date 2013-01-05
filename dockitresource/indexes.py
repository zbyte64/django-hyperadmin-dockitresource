from hyperadmin.indexes import Index
from hyperadmin.resources.storages.endpoints import BoundFile

from django.core.paginator import Page
from django.core.exceptions import ObjectDoesNotExist


class DotpathIndex(Index):
    def get_url_params(self, param_map={}):
        """
        returns url parts for use in the url regexp for conducting item lookups
        """
        param_map.setdefault('dotpath', 'dotpath')
        return [r'(?P<{dotpath}>[\w\.]+)'.format(**param_map)]
    
    def get_url_params_from_item(self, item, param_map={}):
        param_map.setdefault('dotpath', 'dotpath')
        return {param_map['dotpath']: item.dotpath}
    
    def get(self, dotpath):
        val = self.state.parent.instance
        return val.dot_notation_to_value(dotpath)
    
    def get_resource_item(self, dotpath):
        return self.resource.get_resource_item(self.state.item, dotpath=dotpath)

