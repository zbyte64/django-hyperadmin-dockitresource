from hyperadmin.hyperobjects import State, Namespace

class DotpathState(State):
    def set_dotpath(self, val):
        self['dopath'] = val
    
    def get_dotpath(self):
        return self.get('dotpath', '')
    
    dotpath = property(get_dotpath, set_dotpath)

class DotpathNamespace(Namespace):
    pass
