from hyperadmin.hyperobjects import State, Namespace

class DotpathState(State):
    def set_dotpath(self, val):
        self.params['_dopath'] = val
    
    def get_dotpath(self):
        return self.params.get('_dotpath', '')
    
    dotpath = property(get_dotpath, set_dotpath)

class DotpathNamespace(Namespace):
    pass
