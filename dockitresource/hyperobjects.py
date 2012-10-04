from hyperadmin.hyperobjects import State, Namespace, ResourceItem

class DotpathState(State):
    def set_dotpath(self, val):
        self['dopath'] = val
    
    def get_dotpath(self):
        return self.get('dotpath', '')
    
    dotpath = property(get_dotpath, set_dotpath)
    
    def get_resource_items(self):
        if self.dotpath:
            return self.resource.get_resource_items()
        return super(DotpathState, self).get_resource_items()

class DotpathNamespace(Namespace):
    pass

class DotpathResourceItem(ResourceItem):
    def __init__(self, dotpath=None, **kwargs):
        super(DotpathResourceItem, self).__init__(**kwargs)
        self.dotpath = dotpath or self.resource.state.dotpath
